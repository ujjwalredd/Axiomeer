import json
import typer
import requests
from rich import print
from rich.panel import Panel

from marketplace.settings import API_BASE_URL, ANSWER_MODEL
from marketplace.core.cap_extractor import extract_capabilities
from marketplace.core.evidence_quality import assess_evidence
from marketplace.llm.ollama_client import ollama_generate, OllamaConnectionError

app = typer.Typer(add_completion=False)


def _post(path: str, payload: dict):
    r = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def build_grounded_answer(question: str, evidence: dict) -> str:
    """Force the LLM to answer ONLY using evidence we provide."""
    prompt = f"""You are answering a user question using ONLY the EVIDENCE below.
If the evidence is insufficient, say "I don't have enough evidence to answer."
Always include citations exactly as provided in the evidence.
Do not invent any facts or sources.

QUESTION:
{question}

EVIDENCE (JSON):
{json.dumps(evidence, indent=2)}

Return the final answer in 3-6 sentences.
"""
    return ollama_generate(ANSWER_MODEL, prompt)


@app.command()
def main(
    question: str,
    auto_caps: bool = typer.Option(True, "--auto-caps/--no-auto-caps"),
    execute: bool = typer.Option(True, "--execute/--no-execute"),
):
    """
    Simulate: external LLM -> marketplace shop -> choose -> execute -> answer grounded in evidence
    """
    # 1) infer capabilities from question
    try:
        caps = extract_capabilities(question, force_citations=True) if auto_caps else []
    except OllamaConnectionError as e:
        print(f"[yellow]Ollama unavailable, using heuristic caps: {e}[/yellow]")
        caps = []

    print(Panel(f"[bold]Question[/bold]\n{question}\n\n[bold]Inferred caps[/bold]\n{caps}", title="Client LLM"))

    # 2) shop
    shop_req = {
        "task": question,
        "required_capabilities": caps,
        "constraints": {
            "citations_required": True,
            "freshness": "realtime" if "realtime" in caps else None,
            "max_latency_ms": None,
            "max_cost_usd": None,
        },
    }
    shop_res = _post("/shop", shop_req)
    print(Panel(json.dumps(shop_res, indent=2), title="Marketplace /shop response"))

    if shop_res["status"] != "OK" or not shop_res["recommendations"]:
        print("[red]No recommendations available. Aborting.[/red]")
        raise typer.Exit(code=1)

    chosen = shop_res["recommendations"][0]
    print(Panel(json.dumps(chosen, indent=2), title="Chosen recommendation (top pick)"))

    # 3) execute chosen app to obtain evidence
    if not execute:
        print("[yellow]Execution disabled. Stopping after recommendation.[/yellow]")
        return

    ex_req = {
        "app_id": chosen["app_id"],
        "task": question,
        "inputs": {},
        "require_citations": True,
    }
    ex_res = _post("/execute", ex_req)
    print(Panel(json.dumps(ex_res, indent=2), title="Marketplace /execute response"))

    if not ex_res["ok"]:
        print("[red]Execution failed or validation failed. Aborting.[/red]")
        raise typer.Exit(code=1)

    # 4) final answer grounded in evidence output
    evidence = ex_res["output"]
    quality, q_reasons = assess_evidence(evidence)
    print(Panel(json.dumps({"quality": quality, "reasons": q_reasons}, indent=2), title="Evidence Quality"))

    if quality == "LOW":
        print(Panel(
            "I don't have reliable evidence to answer this accurately.\n"
            "Here is the evidence returned (may be mock/test) and its citation(s).",
            title="Final Answer (Abstain)"
        ))
        return

    try:
        final = build_grounded_answer(question, evidence)
    except OllamaConnectionError as e:
        print(f"[red]Cannot generate answer: {e}[/red]")
        raise typer.Exit(code=1)

    print(Panel(final, title="Final Answer (Grounded)"))


if __name__ == "__main__":
    app()
