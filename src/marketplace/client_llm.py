import json
import re
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
    if not r.ok:
        print(f"[red]HTTP {r.status_code} for {path}[/red]")
        try:
            print(r.json())
        except Exception:
            print(r.text)
        r.raise_for_status()
    return r.json()

def _get(path: str, params: dict | None = None):
    r = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def _extract_location(question: str) -> str | None:
    q = question.strip()
    m = re.search(r"\bin\s+([A-Za-z0-9 .,'-]+)", q, flags=re.IGNORECASE)
    if not m:
        return None
    loc = m.group(1).strip()
    # Remove trailing time/context phrases that can confuse geocoding
    loc = re.sub(
        r"\b(right now|currently|today|now|this morning|this afternoon|this evening)\b.*$",
        "",
        loc,
        flags=re.IGNORECASE,
    ).strip()
    # Trim trailing punctuation and common suffixes
    loc = re.sub(r"[?.!,;:]+$", "", loc)
    return loc if loc else None

def _extract_subject(question: str) -> str | None:
    """
    Extract a subject for search-style queries like:
    "What is Wakanda? Cite sources."
    """
    q = question.strip()
    # Prefer quoted terms
    m = re.search(r"\"([^\"]+)\"", q)
    if m:
        return m.group(1).strip()
    patterns = [
        r"\bwhat is\s+(.+)",
        r"\bwho is\s+(.+)",
        r"\bdefine\s+(.+)",
        r"\bdefinition of\s+(.+)",
        r"\bmeaning of\s+(.+)",
        r"\bgdp of\s+(.+)",
        r"\bwhat is the gdp of\s+(.+)",
    ]
    for p in patterns:
        m = re.search(p, q, flags=re.IGNORECASE)
        if m:
            subject = m.group(1).strip()
            subject = re.sub(r"\b(cite sources|with sources|sources)\b.*$", "", subject, flags=re.IGNORECASE).strip()
            subject = re.sub(r"[?.!,;:]+$", "", subject)
            return subject
    return None

def _extract_fx_pair(question: str) -> tuple[str | None, str | None]:
    """
    Extract FX base/target from queries like:
    "exchange rate usd to inr" or "USD/INR"
    """
    q = question.strip()
    m = re.search(r"\b([A-Za-z]{3})\s*/\s*([A-Za-z]{3})\b", q, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    m = re.search(r"\b([A-Za-z]{3})\s+to\s+([A-Za-z]{3})\b", q, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    return None, None

def _geocode_location(location: str) -> dict | None:
    """
    Geocode a location string using Open-Meteo's free geocoding API.
    Returns dict with lat, lon, timezone_name if available.
    """
    def _variants(loc: str) -> list[str]:
        variants = [loc.strip()]
        # Remove commas
        variants.append(loc.replace(",", " ").strip())
        # Use the part before the first comma
        if "," in loc:
            variants.append(loc.split(",", 1)[0].strip())
        # Drop trailing 2-letter region codes (e.g., "Bloomington IN")
        variants.append(re.sub(r"\s+[A-Za-z]{2}$", "", loc).strip())
        # Dedupe while preserving order
        out: list[str] = []
        seen = set()
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                out.append(v)
        return out

    try:
        for candidate in _variants(location):
            r = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": candidate, "count": 1, "language": "en", "format": "json"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or []
            if not results:
                continue
            top = results[0]
            tz = top.get("timezone")
            return {
                "lat": top.get("latitude"),
                "lon": top.get("longitude"),
                "timezone_name": tz,
            }
        return None
    except Exception:
        return None


def build_grounded_answer(question: str, evidence: dict, history: list[dict] | None = None) -> str:
    """Force the LLM to answer ONLY using evidence we provide."""
    answer_text = evidence.get("answer", "")
    citations = evidence.get("citations", [])
    cite_str = ", ".join(citations) if citations else "none"

    prompt = f"""Use the EVIDENCE to answer the QUESTION. Only use facts from the evidence. Do not make up anything.

QUESTION: {question}
RECENT_HISTORY: {json.dumps(history or [], ensure_ascii=True)}

EVIDENCE: {answer_text}
SOURCE: {cite_str}

If the evidence does not answer the question, say "The available evidence does not answer this question."

Write a 2-4 sentence answer:"""
    generated = ollama_generate(ANSWER_MODEL, prompt)
    # Always append citations so they are visible even if the model omits them.
    return f"{generated}\n\nSources: {cite_str}"

def build_quality_gate_answer(
    question: str,
    evidence: dict,
    quality: str,
    reasons: list[str],
    history: list[dict] | None = None,
) -> str:
    answer_text = evidence.get("answer", "")
    citations = evidence.get("citations", [])
    cite_str = ", ".join(citations) if citations else "none"
    prompt = f"""You are an assistant that must answer using evidence only.
If evidence quality is LOW, abstain and explain why using the QUALITY_REASONS.

QUESTION: {question}
RECENT_HISTORY: {json.dumps(history or [], ensure_ascii=True)}

EVIDENCE: {answer_text}
SOURCES: {cite_str}
QUALITY: {quality}
QUALITY_REASONS: {json.dumps(reasons, ensure_ascii=True)}

Write a short response. If quality is LOW, abstain clearly and suggest what evidence is needed."""
    generated = ollama_generate(ANSWER_MODEL, prompt)
    return f"{generated}\n\nSources: {cite_str}"

def choose_recommendation_llm(
    question: str,
    top3: list[dict],
    sales_agent: dict | None,
    constraints: dict,
    history: list[dict] | None = None,
) -> dict:
    prompt = f"""You are the client agent. Choose the best app_id from the Top-3 recommendations.
Return ONLY valid JSON in this schema:
{{"app_id": "string", "reason": "string"}}

QUESTION: {question}
CONSTRAINTS: {json.dumps(constraints, ensure_ascii=True)}
SALES_AGENT: {json.dumps(sales_agent or {}, ensure_ascii=True)}
TOP_3: {json.dumps(top3, ensure_ascii=True)}
RECENT_HISTORY: {json.dumps(history or [], ensure_ascii=True)}
"""
    raw = ollama_generate(ANSWER_MODEL, prompt, response_format="json")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # attempt to extract JSON object if the model added extra text
        raw = raw.strip()
        if "{" in raw and "}" in raw:
            raw = raw[raw.find("{") : raw.rfind("}") + 1]
        payload = json.loads(raw)
    app_id = payload.get("app_id")
    reason = payload.get("reason")
    if not isinstance(app_id, str) or not app_id.strip():
        raise ValueError("client_choice_invalid_app_id")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("client_choice_invalid_reason")
    return {"app_id": app_id.strip(), "reason": reason.strip()}

def build_no_match_answer(question: str, sales_message: str, caps: list[str], constraints: dict, history: list[dict] | None = None) -> str:
    prompt = f"""You are an expert marketplace agent. Explain to the client why no product was recommended.
Use the provided context. Do not invent products or data sources.

QUESTION: {question}
SALES_AGENT_MESSAGE: {sales_message}
REQUIRED_CAPABILITIES: {caps}
CONSTRAINTS: {json.dumps(constraints, ensure_ascii=True)}
RECENT_HISTORY: {json.dumps(history or [], ensure_ascii=True)}

Write a short response that:
- States that no suitable product was found given the constraints
- Suggests what could be relaxed or added
- Does not claim to have executed any data source
"""
    return ollama_generate(ANSWER_MODEL, prompt).strip()


@app.command()
def main(
    question: str,
    auto_caps: bool = typer.Option(True, "--auto-caps/--no-auto-caps"),
    execute: bool = typer.Option(True, "--execute/--no-execute"),
    client_id: str = typer.Option("", "--client-id"),
):
    """
    Simulate: external LLM -> marketplace shop -> choose -> execute -> answer grounded in evidence
    """
    # 1) infer capabilities from question (optional)
    # Use LLM caps for context, but do not hard-filter by caps in /shop.
    caps = []
    if auto_caps:
        try:
            caps = extract_capabilities(question, force_citations=True)
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
    if client_id:
        shop_req["client_id"] = client_id
    shop_res = _post("/shop", shop_req)
    print(Panel(json.dumps(shop_res, indent=2), title="Marketplace /shop response"))

    history = []
    if client_id:
        try:
            history = _get("/history", params={"client_id": client_id})
        except Exception:
            history = []

    if shop_res["status"] != "OK" or not shop_res["recommendations"]:
        explanation = ""
        if shop_res.get("explanation"):
            explanation = " ".join(shop_res["explanation"]).strip()
        if not explanation:
            try:
                explanation = build_no_match_answer(question, "", caps, shop_req["constraints"], history)
            except OllamaConnectionError as e:
                print(f"[red]Cannot generate answer: {e}[/red]")
                raise typer.Exit(code=1)
        try:
            final = build_no_match_answer(question, explanation, caps, shop_req["constraints"], history)
        except OllamaConnectionError as e:
            print(f"[red]Cannot generate answer: {e}[/red]")
            raise typer.Exit(code=1)
        print(Panel(final, title="Final Answer (Grounded)"))
        if client_id:
            _post("/messages", {"client_id": client_id, "role": "client_agent", "content": final})
        return

    top3 = shop_res["recommendations"][:3]
    print(Panel(json.dumps(top3, indent=2), title="Top 3 Recommendations"))

    try:
        choice = choose_recommendation_llm(
            question=question,
            top3=top3,
            sales_agent=shop_res.get("sales_agent"),
            constraints=shop_req["constraints"],
            history=history,
        )
    except Exception as e:
        print(f"[red]Client selection failed: {e}[/red]")
        raise typer.Exit(code=1)
    chosen = next((r for r in top3 if r["app_id"] == choice["app_id"]), None)
    if not chosen:
        print("[red]Client selection returned app_id not in Top-3.[/red]")
        raise typer.Exit(code=1)
    print(Panel(json.dumps({"choice": choice, "picked": chosen}, indent=2), title="Chosen recommendation (client agent)"))

    # 3) execute chosen app to obtain evidence
    if not execute:
        print("[yellow]Execution disabled. Stopping after recommendation.[/yellow]")
        return

    # Best-effort location extraction + geocoding for weather-like queries.
    location = _extract_location(question)
    geo = _geocode_location(location) if location else None
    if location and geo is None:
        evidence = {
            "answer": f"Location '{location}' could not be resolved to real coordinates.",
            "citations": [],
        }
        quality, q_reasons = assess_evidence(evidence)
        print(Panel(json.dumps({"quality": quality, "reasons": q_reasons}, indent=2), title="Evidence Quality"))
        try:
            final = build_grounded_answer(question, evidence, history)
        except OllamaConnectionError as e:
            print(f"[red]Cannot generate answer: {e}[/red]")
            raise typer.Exit(code=1)
        print(Panel(final, title="Final Answer (Grounded)"))
        if client_id:
            _post("/messages", {"client_id": client_id, "role": "client_agent", "content": final})
        return
    inputs: dict = {}
    if geo and geo.get("lat") is not None and geo.get("lon") is not None:
        inputs["lat"] = geo["lat"]
        inputs["lon"] = geo["lon"]
    if geo and geo.get("timezone_name"):
        inputs["timezone_name"] = geo["timezone_name"]

    # Best-effort subject extraction for search-like providers.
    subject = _extract_subject(question)
    if subject:
        if chosen["app_id"] in {"wikipedia_search", "rest_countries", "open_library"}:
            inputs.setdefault("q", subject)
        elif chosen["app_id"] in {"openalex_search", "wikidata_search"}:
            inputs.setdefault("q", subject)
        elif chosen["app_id"] == "dictionary":
            inputs.setdefault("word", subject)

    if chosen["app_id"] == "exchange_rates":
        base, target = _extract_fx_pair(question)
        if base:
            inputs.setdefault("base", base)
        if target:
            inputs.setdefault("target", target)

    ex_req = {
        "app_id": chosen["app_id"],
        "task": question,
        "inputs": inputs,
        "require_citations": True,
    }
    if client_id:
        ex_req["client_id"] = client_id
    ex_res = _post("/execute", ex_req)
    print(Panel(json.dumps(ex_res, indent=2), title="Marketplace /execute response"))

    if not ex_res["ok"]:
        # Use provider output + validation errors to inform the client response.
        evidence = ex_res.get("output") or {}
        evidence["validation_errors"] = ex_res.get("validation_errors", [])
        try:
            final = build_grounded_answer(question, evidence, history)
        except OllamaConnectionError as e:
            print(f"[red]Cannot generate answer: {e}[/red]")
            raise typer.Exit(code=1)
        print(Panel(final, title="Final Answer (Grounded)"))
        if client_id:
            _post("/messages", {"client_id": client_id, "role": "client_agent", "content": final})
        return

    # 4) final answer grounded in evidence output
    evidence = ex_res["output"]
    quality, q_reasons = assess_evidence(evidence)
    print(Panel(json.dumps({"quality": quality, "reasons": q_reasons}, indent=2), title="Evidence Quality"))

    if quality == "LOW":
        try:
            final = build_quality_gate_answer(question, evidence, quality, q_reasons, history)
        except OllamaConnectionError as e:
            print(f"[red]Cannot generate answer: {e}[/red]")
            raise typer.Exit(code=1)
        print(Panel(final, title="Final Answer (Abstain)"))
        if client_id:
            _post("/messages", {"client_id": client_id, "role": "client_agent", "content": final})
        return

    try:
        final = build_grounded_answer(question, evidence, history)
    except OllamaConnectionError as e:
        print(f"[red]Cannot generate answer: {e}[/red]")
        raise typer.Exit(code=1)

    print(Panel(final, title="Final Answer (Grounded)"))
    if client_id:
        _post("/messages", {"client_id": client_id, "role": "client_agent", "content": final})


if __name__ == "__main__":
    app()
