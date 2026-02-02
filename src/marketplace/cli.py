import typer
import requests
from rich import print
from rich.table import Table
import json
from pathlib import Path
from marketplace.core.cap_extractor import extract_capabilities
from marketplace.settings import API_BASE_URL


app = typer.Typer(add_completion=False)


def _post(path: str, payload: dict):
    r = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def _get(path: str):
    r = requests.get(f"{API_BASE_URL}{path}", timeout=20)
    r.raise_for_status()
    return r.json()


@app.command()
def apps():
    """List apps in the marketplace."""
    rows = _get("/apps")
    t = Table(title="Marketplace Apps")
    t.add_column("id")
    t.add_column("name")
    t.add_column("freshness")
    t.add_column("citations")
    t.add_column("caps")
    for a in rows:
        t.add_row(
            a["id"],
            a["name"],
            a["freshness"],
            "yes" if a["citations_supported"] else "no",
            ",".join(a["capabilities"]),
        )
    print(t)


@app.command()
def shop(
    task: str,
    caps: str = "",
    auto_caps: bool = False,
    freshness: str = "",
    citations: bool = True,
    max_latency_ms: int = 0,
    max_cost_usd: float = 0.0,
    execute_top: bool = False,
):
    """
    Shop for top recommendations. Optionally execute top pick.

    - task is positional: `python -m marketplace.cli shop "..." ...`
    - caps is optional: `--caps "weather,realtime"`
    - auto_caps uses Ollama to infer tags: `--auto-caps`
    """
    # ---- Parse manual caps ----
    caps_list = [x.strip().lower() for x in caps.split(",") if x.strip()]

    # ---- Infer caps via LLM (optional) ----
    if auto_caps:
        inferred = extract_capabilities(task, force_citations=citations)
        # Merge inferred + manual, dedupe while preserving order
        merged = []
        seen = set()
        for c in inferred + caps_list:
            c = c.strip().lower()
            if c and c not in seen:
                seen.add(c)
                merged.append(c)
        caps_list = merged
        print(f"[dim]Auto capabilities: {caps_list}[/dim]")

    req = {
        "task": task,
        "required_capabilities": caps_list,
        "constraints": {
            "citations_required": citations,
            "freshness": freshness if freshness else None,
            "max_latency_ms": max_latency_ms if max_latency_ms > 0 else None,
            "max_cost_usd": max_cost_usd if max_cost_usd > 0 else None,
        },
    }

    res = _post("/shop", req)
    print(f"[bold]Status:[/bold] {res['status']}")
    if res.get("explanation"):
        print("[dim]" + " • ".join(res["explanation"]) + "[/dim]")

    recs = res["recommendations"]
    if not recs:
        print("[yellow]No recommendations.[/yellow]")
        return

    t = Table(title="Top Recommendations")
    t.add_column("#", justify="right")
    t.add_column("app_id")
    t.add_column("name")
    t.add_column("score", justify="right")
    for i, r in enumerate(recs, 1):
        t.add_row(str(i), r["app_id"], r["name"], str(r["score"]))
    print(t)

    # Print why for top pick
    top = recs[0]
    print(f"\n[bold]Top pick:[/bold] {top['name']} ({top['app_id']})")
    for line in top["why"]:
        print(f" - {line}")

    if execute_top:
        ex_req = {
            "app_id": top["app_id"],
            "task": task,
            "inputs": {},
            "require_citations": citations,
        }
        ex = _post("/execute", ex_req)
        print("\n[bold]Execution result:[/bold]")
        print(f"ok={ex['ok']}")
        if ex["validation_errors"]:
            print("[red]Validation errors:[/red]")
            for e in ex["validation_errors"]:
                print(f" - {e}")
        if ex.get("provenance"):
            print("[bold]Provenance:[/bold]")
            print(ex["provenance"])
        if ex.get("output") is not None:
            print("[bold]Output:[/bold]")
            print(ex["output"])

@app.command()
def publish(path: str):
    """Publish an app manifest (idempotent upsert)."""
    p = Path(path)
    if not p.exists():
        raise typer.BadParameter(f"File not found: {path}")

    manifest = json.loads(p.read_text(encoding="utf-8"))
    if "id" not in manifest:
        raise typer.BadParameter("Manifest missing required field: id")

    app_id = manifest["id"]
    r = requests.put(f"{API_BASE_URL}/apps/{app_id}", json=manifest, timeout=20)
    r.raise_for_status()
    out = r.json()
    print("[bold green]Published:[/bold green]", out["id"], "-", out["name"])


@app.command()
def runs(n: int = 10):
    """Show recent execution receipts."""
    rows = _get("/runs")[:n]
    t = Table(title=f"Recent Runs (top {n})")
    t.add_column("id", justify="right")
    t.add_column("app_id")
    t.add_column("ok")
    t.add_column("latency_ms", justify="right")
    t.add_column("created_at")
    for r in rows:
        t.add_row(
            str(r["id"]),
            r["app_id"],
            str(r["ok"]),
            str(r["latency_ms"]),
            r["created_at"],
        )
    print(t)


if __name__ == "__main__":
    app()
