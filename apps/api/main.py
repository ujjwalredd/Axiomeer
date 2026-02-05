import json
import requests
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from marketplace.core.models import (
    ShopRequest, ShopResponse, SalesAgentMessage, SalesAgentRecommendation,
    AppCreate, AppOut,
    ExecuteRequest, ExecuteResponse, Provenance,
    RunOut,
    MessageIn, MessageOut,
)
from marketplace.core.router import recommend
from marketplace.core.validate import validate_output
from marketplace.llm.sales_agent import sales_recommendation, sales_no_match, SalesAgentError
from marketplace.settings import MEMORY_MAX_MESSAGES, EXECUTOR_TIMEOUT
from marketplace.storage.db import Base, engine, SessionLocal
from marketplace.storage.models import AppListing
from marketplace.storage.messages import ConversationMessage
from marketplace.storage.runs import Run

@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_manifests()
    yield


app = FastAPI(title="Axiomeer", version="0.2.0", lifespan=lifespan)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _row_to_app_out(r: AppListing) -> AppOut:
    """Convert an ORM AppListing row to an AppOut response."""
    return AppOut(
        id=r.id,
        name=r.name,
        description=r.description,
        capabilities=[c for c in r.capabilities.split(",") if c],
        freshness=r.freshness,
        citations_supported=r.citations_supported,
        latency_est_ms=r.latency_est_ms,
        cost_est_usd=r.cost_est_usd,
        executor_type=r.executor_type,
        executor_url=r.executor_url,
    )

def _history_for_client(db: Session, client_id: str, limit: int) -> list[dict]:
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.client_id == client_id)
        .order_by(ConversationMessage.id.desc())
        .limit(limit)
        .all()
    )
    # Return oldest -> newest for readability
    rows.reverse()
    return [
        {"role": r.role, "content": r.content, "created_at": r.created_at}
        for r in rows
    ]

def _log_message(db: Session, client_id: str, role: str, content: str):
    msg = ConversationMessage(
        client_id=client_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(msg)
    db.commit()


# ---- Health ----

@app.get("/health")
def health():
    return {"status": "ok"}


# ---- Apps CRUD ----

@app.get("/apps", response_model=list[AppOut])
def list_apps(db: Session = Depends(get_db)):
    rows = db.query(AppListing).all()
    return [_row_to_app_out(r) for r in rows]


@app.post("/apps", response_model=AppOut)
def create_app(app_in: AppCreate, db: Session = Depends(get_db)):
    existing = db.get(AppListing, app_in.id)
    if existing:
        raise HTTPException(status_code=409, detail="App with this id already exists")

    row = AppListing(
        id=app_in.id,
        name=app_in.name,
        description=app_in.description,
        capabilities=",".join(app_in.capabilities),
        freshness=app_in.freshness,
        citations_supported=app_in.citations_supported,
        latency_est_ms=app_in.latency_est_ms,
        cost_est_usd=app_in.cost_est_usd,
        executor_type=app_in.executor_type,
        executor_url=app_in.executor_url,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_app_out(row)


@app.get("/apps/{app_id}", response_model=AppOut)
def get_app(app_id: str, db: Session = Depends(get_db)):
    r = db.get(AppListing, app_id)
    if not r:
        raise HTTPException(status_code=404, detail="App not found")
    return _row_to_app_out(r)


@app.put("/apps/{app_id}", response_model=AppOut)
def upsert_app(app_id: str, app_in: AppCreate, db: Session = Depends(get_db)):
    if app_id != app_in.id:
        raise HTTPException(status_code=400, detail="Path app_id must match body id")

    row = db.get(AppListing, app_id)
    if row is None:
        row = AppListing(id=app_in.id)
        db.add(row)

    row.name = app_in.name
    row.description = app_in.description
    row.capabilities = ",".join(app_in.capabilities)
    row.freshness = app_in.freshness
    row.citations_supported = app_in.citations_supported
    row.latency_est_ms = app_in.latency_est_ms
    row.cost_est_usd = app_in.cost_est_usd
    row.executor_type = app_in.executor_type
    row.executor_url = app_in.executor_url

    db.commit()
    db.refresh(row)
    return _row_to_app_out(row)


# ---- Shop ----

@app.post("/shop", response_model=ShopResponse)
def shop(req: ShopRequest, db: Session = Depends(get_db)) -> ShopResponse:
    history = []
    if req.client_id:
        history = _history_for_client(db, req.client_id, MEMORY_MAX_MESSAGES)

    rows = db.query(AppListing).all()
    apps = []
    for r in rows:
        apps.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "capabilities": [c for c in r.capabilities.split(",") if c],
            "freshness": r.freshness,
            "citations_supported": r.citations_supported,
            "latency_est_ms": r.latency_est_ms,
            "cost_est_usd": r.cost_est_usd,
        })

    # Let the sales agent infer domain; do not enforce required_capabilities here.
    req_for_rank = req.model_copy(update={"required_capabilities": []})
    recs, _ = recommend(req_for_rank, apps, k=len(apps))
    if not recs:
        try:
            sales = sales_no_match(
                task=req.task,
                constraints=req.constraints.model_dump(),
                history=history,
            )
        except SalesAgentError as e:
            raise HTTPException(status_code=503, detail={"code": str(e)})
        if req.client_id:
            _log_message(db, req.client_id, "client", req.task)
            _log_message(db, req.client_id, "sales_agent", sales["message"])
        return ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[sales["message"]],
            sales_agent=SalesAgentMessage(
                summary=sales["message"],
                final_choice="NO_MATCH",
                recommendations=[],
            ),
        )

    app_lookup = {a["id"]: a for a in apps}
    candidates = []
    for r in recs:
        a = app_lookup.get(r.app_id, {})
        candidates.append({
            "app_id": r.app_id,
            "name": r.name,
            "score": r.score,
            "capabilities": a.get("capabilities", []),
            "freshness": a.get("freshness"),
            "citations_supported": a.get("citations_supported"),
            "latency_est_ms": a.get("latency_est_ms"),
            "cost_est_usd": a.get("cost_est_usd"),
        })

    try:
        sales = sales_recommendation(
            task=req.task,
            constraints=req.constraints.model_dump(),
            candidates=candidates,
            requested_caps=req.required_capabilities,
            history=history,
        )
    except SalesAgentError as e:
        raise HTTPException(status_code=503, detail={"code": str(e)})

    if sales["final_choice"] == "NO_MATCH":
        if req.client_id:
            _log_message(db, req.client_id, "client", req.task)
            _log_message(db, req.client_id, "sales_agent", sales["summary"])
        return ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[sales["summary"]],
            sales_agent=SalesAgentMessage(
                summary=sales["summary"],
                final_choice="NO_MATCH",
                recommendations=[],
            ),
        )

    chosen_id = sales["final_choice"]
    sales_recs = sales["recommendations"]
    sales_order = {r["app_id"]: i for i, r in enumerate(sales_recs)}
    sales_details = {r["app_id"]: r for r in sales_recs}

    recs_enriched: list[Recommendation] = []
    for r in recs:
        if r.app_id in sales_details:
            details = sales_details[r.app_id]
            r = r.model_copy(update={
                "rationale": details.get("rationale"),
                "tradeoff": details.get("tradeoff"),
            })
        if not r.rationale or not r.tradeoff:
            rationale_bits: list[str] = []
            tradeoff_bits: list[str] = []
            for line in r.why:
                if line.startswith("Capability match") or line.startswith("Freshness matches") or line.startswith("Supports citations"):
                    rationale_bits.append(line)
                if line.startswith("Estimated latency") or line.startswith("Estimated cost"):
                    tradeoff_bits.append(line)
            update_fields: dict[str, str | None] = {}
            if not r.rationale and rationale_bits:
                update_fields["rationale"] = "; ".join(rationale_bits)
            if not r.tradeoff and tradeoff_bits:
                update_fields["tradeoff"] = "; ".join(tradeoff_bits)
            if update_fields:
                r = r.model_copy(update=update_fields)
        recs_enriched.append(r)

    recs_sorted = sorted(
        recs_enriched,
        key=lambda r: (0, sales_order[r.app_id]) if r.app_id in sales_order else (1, 0),
    )

    if req.client_id:
        _log_message(db, req.client_id, "client", req.task)
        _log_message(db, req.client_id, "sales_agent", f"Final choice: {chosen_id}. {sales['summary']}")

    sales_agent_msg = SalesAgentMessage(
        summary=sales["summary"],
        final_choice=chosen_id,
        recommendations=[
            SalesAgentRecommendation(
                app_id=r["app_id"],
                rationale=r["rationale"],
                tradeoff=r["tradeoff"],
            )
            for r in sales["recommendations"]
        ],
    )

    return ShopResponse(
        status="OK",
        recommendations=recs_sorted,
        explanation=[sales["summary"]],
        sales_agent=sales_agent_msg,
    )


# ---- Execute ----

@app.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest, db: Session = Depends(get_db)) -> ExecuteResponse:
    t0 = perf_counter()
    now = datetime.now(timezone.utc).isoformat()

    payload = None
    errors: list[str] = []
    ok = False
    require_citations = True

    def log_run():
        latency_ms = int((perf_counter() - t0) * 1000)
        run = Run(
            app_id=req.app_id,
            task=req.task,
            client_id=req.client_id,
            require_citations=require_citations,
            ok=ok,
            output_json=json.dumps(payload) if payload is not None else None,
            validation_errors_json=json.dumps(errors),
            latency_ms=latency_ms,
            created_at=now,
        )
        db.add(run)
        db.commit()

    app_row = db.get(AppListing, req.app_id)
    if not app_row:
        errors = ["Unknown app_id"]
        log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors)

    require_citations = bool(req.require_citations or app_row.citations_supported)

    if app_row.executor_type != "http_api":
        errors = ["Unsupported executor_type"]
        log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors)

    if not app_row.executor_url:
        errors = ["Missing executor_url"]
        log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors)

    try:
        r = requests.get(app_row.executor_url, params=req.inputs, timeout=EXECUTOR_TIMEOUT)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        errors = [f"Execution failed: {e}"]
        log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors)

    errors = validate_output(payload, require_citations=require_citations)
    if errors:
        log_run()
        return ExecuteResponse(
            app_id=req.app_id, ok=False, output=payload,
            provenance=None, validation_errors=errors,
        )

    prov = Provenance(
        sources=payload.get("citations", []) if isinstance(payload, dict) else [],
        retrieved_at=payload.get("retrieved_at", ""),
        notes=[],
    )

    ok = True
    log_run()
    if req.client_id and isinstance(payload, dict):
        _log_message(db, req.client_id, "provider", json.dumps(payload, ensure_ascii=True))
    return ExecuteResponse(app_id=req.app_id, ok=True, output=payload, provenance=prov, validation_errors=[])


# ---- Runs ----

@app.get("/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    rows = db.query(Run).order_by(Run.id.desc()).limit(50).all()
    return [
        RunOut(
            id=r.id,
            app_id=r.app_id,
            task=r.task,
            require_citations=r.require_citations,
            ok=r.ok,
            latency_ms=r.latency_ms,
            created_at=r.created_at,
            validation_errors=json.loads(r.validation_errors_json or "[]"),
            client_id=r.client_id,
        )
        for r in rows
    ]


# ---- Conversation Memory ----

@app.post("/messages", response_model=MessageOut)
def create_message(msg: MessageIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    row = ConversationMessage(
        client_id=msg.client_id,
        role=msg.role,
        content=msg.content,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return MessageOut(
        id=row.id,
        client_id=row.client_id,
        role=row.role,
        content=row.content,
        created_at=row.created_at,
    )


@app.get("/history", response_model=list[MessageOut])
def get_history(client_id: str, limit: int = MEMORY_MAX_MESSAGES, db: Session = Depends(get_db)):
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.client_id == client_id)
        .order_by(ConversationMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        MessageOut(
            id=r.id,
            client_id=r.client_id,
            role=r.role,
            content=r.content,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ---- Providers ----

@app.get("/providers/openmeteo_weather")
def provider_openmeteo_weather(
    lat: float | None = None,
    lon: float | None = None,
    timezone_name: str | None = None,
):
    now = datetime.now(timezone.utc).isoformat()
    if lat is None or lon is None:
        return {
            "answer": "Missing required parameters: lat and lon.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }
    if not timezone_name:
        timezone_name = "UTC"

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "timezone": timezone_name,
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    current = data.get("current", {})
    temp = current.get("temperature_2m", None)
    code = current.get("weather_code", None)
    wind = current.get("wind_speed_10m", None)

    return {
        "answer": f"At {current.get('time','')}, temperature is {temp} C, weather_code={code}, wind_speed={wind} km/h (Open-Meteo).",
        "citations": ["https://open-meteo.com/"],
        "retrieved_at": now,
        "quality": "verified",
    }


@app.get("/providers/wikipedia")
def provider_wikipedia(q: str | None = None):
    """Wikipedia summary provider. Free, no API key."""
    now = datetime.now(timezone.utc).isoformat()

    if not q or not q.strip():
        return {
            "answer": "No query provided. Please specify a topic to search.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{q}"
    r = requests.get(url, timeout=10, headers={"User-Agent": "Axiomeer/0.1"})

    if r.status_code == 404:
        return {
            "answer": f"No Wikipedia article found for '{q}'.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    r.raise_for_status()
    data = r.json()

    title = data.get("title", q)
    extract = data.get("extract", "")
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

    return {
        "answer": f"{title}: {extract}",
        "citations": [page_url] if page_url else [f"https://en.wikipedia.org/wiki/{q}"],
        "retrieved_at": now,
        "quality": "verified",
    }


@app.get("/providers/restcountries")
def provider_restcountries(q: str | None = None):
    """REST Countries provider. Free, no API key."""
    now = datetime.now(timezone.utc).isoformat()

    if not q or not q.strip():
        return {
            "answer": "No country name provided.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    url = f"https://restcountries.com/v3.1/name/{q.strip()}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            return {
                "answer": f"No country found matching '{q}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
        r.raise_for_status()
        data = r.json()
        country = data[0] if data else {}
        name = country.get("name", {}).get("common", q)
        capital = ", ".join(country.get("capital", ["N/A"]))
        region = country.get("region", "N/A")
        population = country.get("population", "N/A")
        languages = ", ".join(country.get("languages", {}).values()) if country.get("languages") else "N/A"
        return {
            "answer": f"{name}: Capital: {capital}, Region: {region}, Population: {population:,} , Languages: {languages}.",
            "citations": [f"https://restcountries.com/v3.1/name/{q}"],
            "retrieved_at": now,
            "quality": "verified",
        }
    except Exception as e:
        return {
            "answer": f"Error fetching country data: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }


@app.get("/providers/exchangerate")
def provider_exchangerate(base: str | None = None, target: str | None = None):
    """Exchange rate provider. Free, no API key."""
    now = datetime.now(timezone.utc).isoformat()

    if not base or not base.strip():
        return {
            "answer": "No base currency provided.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    base = base.strip().upper()
    target = target.strip().upper() if isinstance(target, str) and target.strip() else None
    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("result") != "success":
            return {
                "answer": f"Exchange rate API returned non-success for '{base}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
        rates = data.get("rates", {})
        if target:
            if target in rates and target != base:
                rate_strs = [f"{target}: {rates[target]}"]
            else:
                rate_strs = []
        else:
            symbols = sorted([c for c in rates.keys() if c != base])
            rate_strs = [f"{c}: {rates[c]}" for c in symbols[:10]]
        return {
            "answer": f"Exchange rates for 1 {base}: {', '.join(rate_strs[:6])}. Last updated: {data.get('time_last_update_utc', 'N/A')}.",
            "citations": [f"https://open.er-api.com/v6/latest/{base}"],
            "retrieved_at": now,
            "quality": "verified",
        }
    except Exception as e:
        return {
            "answer": f"Error fetching exchange rates: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }


@app.get("/providers/dictionary")
def provider_dictionary(word: str | None = None):
    """Free Dictionary API provider. No API key."""
    now = datetime.now(timezone.utc).isoformat()

    if not word or not word.strip():
        return {
            "answer": "No word provided.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    word = word.strip().lower()
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            return {
                "answer": f"No definition found for '{word}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
        r.raise_for_status()
        data = r.json()
        entry = data[0] if data else {}
        meanings = entry.get("meanings", [])
        defs = []
        for m in meanings[:3]:
            part = m.get("partOfSpeech", "")
            d = m.get("definitions", [{}])[0].get("definition", "")
            defs.append(f"({part}) {d}")
        return {
            "answer": f"{word}: {'; '.join(defs)}",
            "citations": [f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"],
            "retrieved_at": now,
            "quality": "verified",
        }
    except Exception as e:
        return {
            "answer": f"Error fetching definition: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }


@app.get("/providers/openlibrary")
def provider_openlibrary(q: str | None = None):
    """Open Library book search. Free, no API key."""
    now = datetime.now(timezone.utc).isoformat()

    if not q or not q.strip():
        return {
            "answer": "No search query provided.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    try:
        r = requests.get(
            "https://openlibrary.org/search.json",
            params={"q": q.strip(), "limit": 3},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        docs = data.get("docs", [])
        if not docs:
            return {
                "answer": f"No books found for '{q}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
        results = []
        for doc in docs[:3]:
            title = doc.get("title", "Unknown")
            author = ", ".join(doc.get("author_name", ["Unknown"]))
            year = doc.get("first_publish_year", "N/A")
            results.append(f'"{title}" by {author} ({year})')
        return {
            "answer": f"Books matching '{q}': {'; '.join(results)}.",
            "citations": [f"https://openlibrary.org/search?q={q}"],
            "retrieved_at": now,
            "quality": "verified",
        }
    except Exception as e:
        return {
            "answer": f"Error searching books: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }


@app.get("/providers/wikidata")
def provider_wikidata(q: str | None = None, limit: int = 3):
    """Wikidata entity search. Free, no API key."""
    now = datetime.now(timezone.utc).isoformat()

    if not q or not q.strip():
        return {
            "answer": "No search query provided.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    params = {
        "action": "wbsearchentities",
        "search": q.strip(),
        "language": "en",
        "format": "json",
        "limit": max(1, min(int(limit), 5)),
    }
    try:
        r = requests.get("https://www.wikidata.org/w/api.php", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data.get("search", [])
        if not results:
            return {
                "answer": f"No Wikidata entities found for '{q}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
        lines = []
        citations = []
        for item in results[:3]:
            label = item.get("label", "Unknown")
            desc = item.get("description", "")
            url = item.get("url", "")
            lines.append(f"{label} — {desc}".strip(" —"))
            if url:
                citations.append(url)
        return {
            "answer": f"Wikidata results for '{q}': " + "; ".join(lines) + ".",
            "citations": citations,
            "retrieved_at": now,
            "quality": "verified",
        }
    except Exception as e:
        return {
            "answer": f"Error fetching Wikidata data: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }


@app.get("/providers/wikipedia_dumps")
def provider_wikipedia_dumps(lang: str | None = None):
    """Wikipedia dumps locator. Returns latest pages-articles dump URL."""
    now = datetime.now(timezone.utc).isoformat()

    if not lang or not lang.strip():
        return {
            "answer": "No language code provided (e.g., en, es, fr).",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }

    lang = lang.strip().lower()
    dump_url = f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-pages-articles.xml.bz2"
    return {
        "answer": f"Latest Wikipedia dump for '{lang}': {dump_url}",
        "citations": [dump_url, "https://dumps.wikimedia.org/legal.html"],
        "retrieved_at": now,
        "quality": "verified",
    }


# ---- Auto-Bootstrap ----

MANIFESTS_DIR = Path(__file__).resolve().parent.parent.parent / "manifests"


def bootstrap_manifests():
    """Auto-register all manifests (idempotent upsert)."""
    if not MANIFESTS_DIR.exists():
        return
    db = SessionLocal()
    try:
        for manifest_path in sorted(MANIFESTS_DIR.glob("*.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                app_id = manifest.get("id")
                if not app_id:
                    continue
                row = db.get(AppListing, app_id)
                if row is None:
                    row = AppListing(id=app_id)
                    db.add(row)
                row.name = manifest.get("name", app_id)
                row.description = manifest.get("description", "")
                row.capabilities = ",".join(manifest.get("capabilities", []))
                row.freshness = manifest.get("freshness", "static")
                row.citations_supported = manifest.get("citations_supported", True)
                row.latency_est_ms = manifest.get("latency_est_ms", 500)
                row.cost_est_usd = manifest.get("cost_est_usd", 0.0)
                row.executor_type = manifest.get("executor_type", "http_api")
                row.executor_url = manifest.get("executor_url", "")
                db.commit()
            except Exception:
                continue
    finally:
        db.close()
