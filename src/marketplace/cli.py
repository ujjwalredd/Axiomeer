import inspect
import typer
import requests
import click
import re
import os
from rich import print
from rich.table import Table
import json
from pathlib import Path
from marketplace.core.cap_extractor import extract_capabilities
from marketplace.settings import API_BASE_URL


def _patch_click_make_metavar():
    """Typer rich help calls make_metavar without ctx; Click>=8.3 requires ctx."""
    try:
        sig = inspect.signature(click.Parameter.make_metavar)
        if len(sig.parameters) == 2:
            original = click.Parameter.make_metavar

            def _make_metavar(self, ctx=None):
                if ctx is None:
                    ctx = click.Context(click.Command("marketplace"))
                return original(self, ctx)

            click.Parameter.make_metavar = _make_metavar
    except Exception:
        pass

    # TyperArgument/TyperOption in older Typer expect no ctx; Click 8.3 passes ctx.
    try:
        from typer import core as typer_core

        def _wrap_make_metavar(cls):
            def _typer_make_metavar(self, ctx=None):
                if ctx is None:
                    ctx = click.Context(click.Command("marketplace"))
                return click.Parameter.make_metavar(self, ctx)

            cls.make_metavar = _typer_make_metavar

        for cls in (typer_core.TyperArgument, typer_core.TyperOption):
            sig = inspect.signature(cls.make_metavar)
            if len(sig.parameters) == 1:
                _wrap_make_metavar(cls)
    except Exception:
        pass


_patch_click_make_metavar()

app = typer.Typer(add_completion=False)


def _get_headers():
    """Get headers including API key if available."""
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("AXIOMEER_API_KEY") or os.getenv("API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _post(path: str, payload: dict):
    """Make authenticated POST request."""
    headers = _get_headers()
    try:
        r = requests.post(f"{API_BASE_URL}{path}", json=payload, headers=headers, timeout=60)
        if not r.ok:
            print(f"[red]HTTP {r.status_code} for {path}[/red]")
            if r.status_code == 401:
                print("[yellow]Authentication required. Set your API key:[/yellow]")
                print("[dim]export AXIOMEER_API_KEY=your_api_key_here[/dim]")
                print("[dim]Or disable auth: export AUTH_ENABLED=false[/dim]")
            try:
                print(r.json())
            except Exception:
                print(r.text)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("\n[bold red]Authentication Error[/bold red]")
            print("To use the CLI with authentication enabled:")
            print("1. Create an API key at: http://localhost:8000/docs")
            print("2. Set it: [cyan]export AXIOMEER_API_KEY=your_key[/cyan]")
            print("3. Or disable auth in production by setting AUTH_ENABLED=false")
            raise SystemExit(1)
        raise


def _get(path: str):
    """Make authenticated GET request."""
    headers = _get_headers()
    try:
        r = requests.get(f"{API_BASE_URL}{path}", headers=headers, timeout=20)
        if not r.ok and r.status_code == 401:
            print(f"[red]HTTP {r.status_code} for {path}[/red]")
            print("[yellow]Authentication required. Set your API key:[/yellow]")
            print("[dim]export AXIOMEER_API_KEY=your_api_key_here[/dim]")
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("\n[bold red]Authentication Error[/bold red]")
            print("To use the CLI with authentication enabled:")
            print("1. Create an API key at: http://localhost:8000/docs")
            print("2. Set it: [cyan]export AXIOMEER_API_KEY=your_key[/cyan]")
            raise SystemExit(1)
        raise


def _extract_location(question: str) -> str | None:
    q = question.strip()
    m = re.search(r"\bin\s+([A-Za-z0-9 .,'-]+)", q, flags=re.IGNORECASE)
    if not m:
        return None
    loc = m.group(1).strip()
    loc = re.sub(
        r"\b(right now|currently|today|now|this morning|this afternoon|this evening)\b.*$",
        "",
        loc,
        flags=re.IGNORECASE,
    ).strip()
    loc = re.sub(r"[?.!,;:]+$", "", loc)
    return loc if loc else None


def _extract_fx_pair(question: str) -> tuple[str | None, str | None]:
    q = question.strip()
    m = re.search(r"\b([A-Za-z]{3})\s*/\s*([A-Za-z]{3})\b", q, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    m = re.search(r"\b([A-Za-z]{3})\s+to\s+([A-Za-z]{3})\b", q, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    return None, None


def _extract_subject(question: str) -> str | None:
    q = question.strip()
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
        r"\bfind\s+(.+)",
    ]
    for p in patterns:
        m = re.search(p, q, flags=re.IGNORECASE)
        if m:
            subject = m.group(1).strip()
            subject = re.sub(r"\b(cite sources|with sources|with citations|citations|sources)\b.*$", "", subject, flags=re.IGNORECASE).strip()
            subject = re.sub(r"\b(population|gdp|capital|area|currency)\b.*$", "", subject, flags=re.IGNORECASE).strip()
            subject = re.sub(r"^wikidata\s+entity\s+for\s+", "", subject, flags=re.IGNORECASE).strip()
            subject = re.sub(r"^entity\s+for\s+", "", subject, flags=re.IGNORECASE).strip()
            subject = re.sub(r"[?.!,;:]+$", "", subject)
            return subject
    return None


def _extract_lang_code(question: str) -> str | None:
    q = question.strip().lower()
    m = re.search(r"\blang(?:uage)?\s*[:=]?\s*([a-z]{2})\b", q)
    if m:
        return m.group(1)
    m = re.search(r"\bfor\s+([a-z]{2})\b", q)
    if m:
        return m.group(1)
    return None


def _geocode_location(location: str) -> dict | None:
    def _variants(loc: str) -> list[str]:
        variants = [loc.strip()]
        variants.append(loc.replace(",", " ").strip())
        if "," in loc:
            variants.append(loc.split(",", 1)[0].strip())
        variants.append(re.sub(r"\s+[A-Za-z]{2}$", "", loc).strip())
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
    task: str = typer.Argument(..., help="Natural-language task to shop for"),
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
    if not task:
        print("[red]Missing required task.[/red]")
        print('Usage: python -m marketplace.cli shop "your task here"')
        raise typer.Exit(code=1)

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

    # Print top 3 details
    for i, r in enumerate(recs[:3], 1):
        print(f"\n[bold]Recommendation {i}:[/bold] {r['name']} ({r['app_id']})")
        for line in r.get("why", []):
            print(f" - {line}")
        if r.get("rationale"):
            print(f"[dim]Rationale:[/dim] {r['rationale']}")
        if r.get("tradeoff"):
            print(f"[dim]Tradeoff:[/dim] {r['tradeoff']}")

    if execute_top:
        top = recs[0]
        # Let the provider/LLM extract parameters from the task intelligently
        # No hardcoded extraction logic - if it can't understand, it should fail gracefully
        ex_req = {
            "app_id": top["app_id"],
            "task": task,
            "inputs": {},  # Provider should extract from task
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
def publish(path: str = typer.Argument(None, help="Path to a manifest JSON file")):
    """Publish an app manifest (idempotent upsert)."""
    if not path:
        print("[red]Missing required manifest path.[/red]")
        print("Usage: python -m marketplace.cli publish manifests/<file>.json")
        raise typer.Exit(code=1)
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


@app.command()
def run(run_id: int):
    """Fetch a full execution receipt by run_id."""
    receipt = _get(f"/runs/{run_id}")
    print(receipt)


@app.command()
def trust(app_id: str = ""):
    """Show trust scores for all apps or a single app."""
    if app_id:
        rows = [_get(f"/apps/{app_id}/trust")]
    else:
        rows = _get("/trust")

    t = Table(title="App Trust Scores")
    t.add_column("app_id")
    t.add_column("trust_score", justify="right")
    t.add_column("success_rate", justify="right")
    t.add_column("citation_pass", justify="right")
    t.add_column("avg_latency", justify="right")
    t.add_column("p95_latency", justify="right")
    t.add_column("last_run_at")
    t.add_column("insufficient", justify="center")

    for r in rows:
        t.add_row(
            r["app_id"],
            f"{r['trust_score']:.2f}",
            f"{r['success_rate']:.2f}",
            f"{r['citation_pass_rate']:.2f}",
            str(r["avg_latency_ms"]) if r["avg_latency_ms"] is not None else "-",
            str(r["p95_latency_ms"]) if r["p95_latency_ms"] is not None else "-",
            r["last_run_at"] or "-",
            "yes" if r.get("insufficient_data") else "no",
        )
    print(t)


if __name__ == "__main__":
    app()
