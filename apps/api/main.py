import json
import logging
import requests
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, time

# Structured logging: timestamp | level | module | message
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from marketplace.core.models import (
    ShopRequest, ShopResponse, SalesAgentMessage, SalesAgentRecommendation,
    AppCreate, AppOut,
    ExecuteRequest, ExecuteResponse, Provenance,
    RunOut, RunDetailOut, TrustOut,
    MessageIn, MessageOut,
)
from marketplace.core.router import recommend, _latency_score
from marketplace.core.validate import validate_output
from marketplace.llm.sales_agent import sales_recommendation, SalesAgentError
from marketplace.settings import (
    MEMORY_MAX_MESSAGES,
    EXECUTOR_TIMEOUT,
    SHOP_CACHE_TTL_SECONDS,
    PROVIDER_CACHE_TTL_WEATHER,
    PROVIDER_CACHE_TTL_FX,
    PROVIDER_CACHE_TTL_WIKI,
    PROVIDER_CACHE_TTL_WIKIDATA,
    PROVIDER_CACHE_TTL_WIKIDUMPS,
    PROVIDER_CACHE_TTL_RESTCOUNTRIES,
    PROVIDER_CACHE_TTL_OPENLIB,
    PROVIDER_CACHE_TTL_DICTIONARY,
)
from marketplace.storage.db import Base, engine, SessionLocal
from marketplace.storage.models import AppListing
from marketplace.storage.messages import ConversationMessage
from marketplace.storage.runs import Run
from marketplace.storage.users import User, UsageRecord

# Import provider endpoints
from apps.api.providers import router as providers_router

# Import authentication router and dependencies
from apps.api.auth_routes import router as auth_router
from apps.api.routers.v1 import router as v1_router
from marketplace.auth.dependencies import check_user_rate_limit

@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_manifests()

    # Initialize semantic search engine
    from marketplace.core.semantic_search import SemanticSearchEngine
    from marketplace.settings import SEMANTIC_SEARCH_ENABLED, SEMANTIC_SEARCH_MODEL

    semantic_engine = SemanticSearchEngine(
        model_name=SEMANTIC_SEARCH_MODEL,
        enabled=SEMANTIC_SEARCH_ENABLED
    )

    # Store in app state for access in endpoints
    app.state.semantic_search = semantic_engine

    # Pre-populate semantic index with existing products
    if SEMANTIC_SEARCH_ENABLED:
        db = SessionLocal()
        try:
            rows = db.query(AppListing).all()
            products = []
            for r in rows:
                products.append({
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "capabilities": [c for c in r.capabilities.split(",") if c],
                })
            if products:
                semantic_engine.add_products(products)
        finally:
            db.close()

    yield


app = FastAPI(title="Axiomeer", version="0.2.0", lifespan=lifespan)

# Include provider endpoints
app.include_router(providers_router)
app.include_router(auth_router)

def _cache_key(prefix: str, payload: dict) -> str:
    return f"{prefix}:{json.dumps(payload, sort_keys=True, default=str)}"


def _cache_get(key: str):
    try:
        from marketplace.core.cache import cache_get as _get
        return _get(key)
    except Exception:
        return None


def _cache_set(key: str, value, ttl_seconds: int):
    if ttl_seconds <= 0:
        return
    try:
        from marketplace.core.cache import cache_set as _set
        _set(key, value, ttl_seconds)
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _refresh_semantic_index(db: Session):
    """Refresh the semantic search index with all products from the database."""
    semantic_engine = getattr(app.state, "semantic_search", None)
    if semantic_engine and semantic_engine.is_available():
        rows = db.query(AppListing).all()
        products = []
        for r in rows:
            products.append({
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "capabilities": [c for c in r.capabilities.split(",") if c],
            })
        if products:
            semantic_engine.add_products(products)


def _row_to_app_out(r: AppListing) -> AppOut:
    """Convert an ORM AppListing row to an AppOut response."""
    try:
        metadata = json.loads(r.extra_metadata) if r.extra_metadata else {}
    except:
        metadata = {}

    return AppOut(
        id=r.id,
        name=r.name,
        description=r.description,
        category=r.category,
        subcategory=r.subcategory,
        tags=[t for t in r.tags.split(",") if t],
        capabilities=[c for c in r.capabilities.split(",") if c],
        freshness=r.freshness,
        citations_supported=r.citations_supported,
        product_type=r.product_type,
        latency_est_ms=r.latency_est_ms,
        cost_est_usd=r.cost_est_usd,
        executor_type=r.executor_type,
        executor_url=r.executor_url,
        metadata=metadata,
    )

def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    values = sorted(values)
    idx = max(0, int(round(0.95 * (len(values) - 1))))
    return values[idx]

def _trust_scores_by_app(db: Session) -> dict[str, TrustOut]:
    rows = db.query(Run).all()
    by_app: dict[str, list[Run]] = {}
    for r in rows:
        by_app.setdefault(r.app_id, []).append(r)

    results: dict[str, TrustOut] = {}
    for app_id, runs in by_app.items():
        total = len(runs)
        ok_runs = [r for r in runs if r.ok]
        ok_count = len(ok_runs)
        success_rate = ok_count / total if total else 0.0
        require_cite = [r for r in runs if r.require_citations]
        cite_ok = [r for r in require_cite if r.ok]
        citation_pass_rate = (len(cite_ok) / len(require_cite)) if require_cite else success_rate
        latencies = [r.latency_ms for r in runs if r.latency_ms is not None]
        avg_latency = int(sum(latencies) / len(latencies)) if latencies else None
        p95_latency = _p95(latencies)
        last_run_at = max((r.created_at for r in runs), default=None)
        latency_score = _latency_score(avg_latency or 1, None) if avg_latency else 0.5
        trust_score = (0.5 * success_rate) + (0.3 * citation_pass_rate) + (0.2 * latency_score)
        insufficient = total == 0
        results[app_id] = TrustOut(
            app_id=app_id,
            total_runs=total,
            success_rate=round(success_rate, 4),
            citation_pass_rate=round(citation_pass_rate, 4),
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            last_run_at=last_run_at,
            trust_score=round(trust_score, 4) if not insufficient else 0.5,
            insufficient_data=insufficient,
        )
    return results

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


@app.get("/semantic-search/stats")
def semantic_search_stats():
    """Get semantic search engine statistics."""
    semantic_engine = getattr(app.state, "semantic_search", None)
    if semantic_engine:
        return semantic_engine.get_stats()
    return {
        "enabled": False,
        "initialized": False,
        "error": "Semantic search engine not initialized",
    }


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

    meta = dict(app_in.metadata or {})
    meta["http_method"] = (app_in.http_method or "GET").upper()
    if app_in.input_schema:
        meta["input_schema"] = app_in.input_schema
    row = AppListing(
        id=app_in.id,
        name=app_in.name,
        description=app_in.description,
        category=app_in.category,
        subcategory=app_in.subcategory,
        tags=",".join(app_in.tags or []),
        capabilities=",".join(app_in.capabilities),
        freshness=app_in.freshness,
        citations_supported=app_in.citations_supported,
        product_type=app_in.product_type,
        latency_est_ms=app_in.latency_est_ms,
        cost_est_usd=app_in.cost_est_usd,
        executor_type=app_in.executor_type,
        executor_url=app_in.executor_url,
        extra_metadata=json.dumps(meta),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # Refresh semantic search index
    _refresh_semantic_index(db)

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
    row.category = app_in.category
    row.subcategory = app_in.subcategory
    row.tags = ",".join(app_in.tags or [])
    row.capabilities = ",".join(app_in.capabilities)
    row.freshness = app_in.freshness
    row.citations_supported = app_in.citations_supported
    row.product_type = app_in.product_type
    row.latency_est_ms = app_in.latency_est_ms
    row.cost_est_usd = app_in.cost_est_usd
    row.executor_type = app_in.executor_type
    row.executor_url = app_in.executor_url
    meta = dict(app_in.metadata or {})
    meta["http_method"] = (app_in.http_method or "GET").upper()
    if app_in.input_schema:
        meta["input_schema"] = app_in.input_schema
    row.extra_metadata = json.dumps(meta)

    db.commit()
    db.refresh(row)

    # Refresh semantic search index
    _refresh_semantic_index(db)

    return _row_to_app_out(row)


# ---- Shop ----

@app.post("/shop", response_model=ShopResponse)
def shop(
    req: ShopRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit)
) -> ShopResponse:
    # Log usage for authenticated users
    if current_user.id > 0:
        usage = UsageRecord(
            user_id=current_user.id,
            endpoint="/shop",
            method="POST",
            cost_usd=0.0
        )
        db.add(usage)
        db.commit()
    cache_key = _cache_key(
        "shop",
        {
            "task": req.task,
            "required_capabilities": sorted([c.strip().lower() for c in req.required_capabilities]),
            "constraints": req.constraints.model_dump(),
        },
    )
    cached = _cache_get(cache_key)
    if cached:
        return ShopResponse(**cached)

    history = []
    if req.client_id:
        history = _history_for_client(db, req.client_id, MEMORY_MAX_MESSAGES)

    trust_scores = _trust_scores_by_app(db)
    rows = db.query(AppListing).all()
    apps = []
    for r in rows:
        trust = trust_scores.get(r.id)
        apps.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "capabilities": [c for c in r.capabilities.split(",") if c],
            "freshness": r.freshness,
            "citations_supported": r.citations_supported,
            "latency_est_ms": r.latency_est_ms,
            "cost_est_usd": r.cost_est_usd,
            "trust_score": trust.trust_score if trust else None,
        })

    # Get semantic search engine from app state
    semantic_engine = getattr(app.state, "semantic_search", None)

    recs, router_expl, router_metrics = recommend(req, apps, k=len(apps), semantic_search_engine=semantic_engine)
    if not recs:
        message = "No suitable products matched strict routing thresholds."
        if router_expl:
            message = router_expl[0]
        if req.client_id:
            _log_message(db, req.client_id, "client", req.task)
            _log_message(db, req.client_id, "sales_agent", message)
        res = ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[message],
            sales_agent=SalesAgentMessage(
                summary=message,
                final_choice="NO_MATCH",
                recommendations=[],
            ),
            metrics=router_metrics,
        )
        _cache_set(cache_key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
        return res

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
            "trust_score": a.get("trust_score"),
        })

    from marketplace.settings import SALES_AGENT_TOP_K
    candidates_for_sales = candidates[:max(1, SALES_AGENT_TOP_K)]
    try:
        sales = sales_recommendation(
            task=req.task,
            constraints=req.constraints.model_dump(),
            candidates=candidates_for_sales,
            requested_caps=req.required_capabilities,
            history=history,
        )
    except SalesAgentError as e:
        summary = f"Sales agent failed: {e}. Returning NO_MATCH to avoid unsafe selection."
        if req.client_id:
            _log_message(db, req.client_id, "client", req.task)
            _log_message(db, req.client_id, "sales_agent", summary)
        res = ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[summary],
            sales_agent=SalesAgentMessage(
                summary=summary,
                final_choice="NO_MATCH",
                recommendations=[],
            ),
            metrics=router_metrics,
        )
        _cache_set(cache_key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
        return res

    if sales["final_choice"] == "NO_MATCH":
        if req.client_id:
            _log_message(db, req.client_id, "client", req.task)
            _log_message(db, req.client_id, "sales_agent", sales["summary"])
        res = ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[sales["summary"]],
            sales_agent=SalesAgentMessage(
                summary=sales["summary"],
                final_choice="NO_MATCH",
                recommendations=[],
            ),
            metrics=router_metrics,
        )
        _cache_set(cache_key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
        return res

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
        recs_enriched[:max(1, SALES_AGENT_TOP_K)],
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

    res = ShopResponse(
        status="OK",
        recommendations=recs_sorted,
        explanation=[sales["summary"]],
        sales_agent=sales_agent_msg,
        metrics=router_metrics,
    )
    _cache_set(cache_key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
    return res


# ---- Execute ----

@app.post("/execute", response_model=ExecuteResponse)
async def execute(
    req: ExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit)
) -> ExecuteResponse:
    # Log usage for authenticated users
    if current_user.id > 0:
        usage = UsageRecord(
            user_id=current_user.id,
            endpoint="/execute",
            method="POST",
            cost_usd=0.0  # Can be updated based on actual cost later
        )
        db.add(usage)
        db.commit()
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
        db.refresh(run)
        return run.id

    app_row = db.get(AppListing, req.app_id)
    if not app_row:
        errors = ["Unknown app_id"]
        run_id = log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors, run_id=run_id)

    # Only require citations if explicitly requested by the client AND the API supports them
    require_citations = bool(req.require_citations and app_row.citations_supported)

    if app_row.executor_type != "http_api":
        errors = ["Unsupported executor_type"]
        run_id = log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors, run_id=run_id)

    if not app_row.executor_url:
        errors = ["Missing executor_url"]
        run_id = log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors, run_id=run_id)

    # Extract parameters from task using LLM if inputs are empty
    final_inputs = req.inputs.copy() if req.inputs else {}

    logger.info(f"Execute {req.app_id}: inputs={final_inputs}, task='{req.task}'")

    if not final_inputs and req.task:
        logger.info(f"Attempting LLM parameter extraction for {req.app_id}")
        try:
            from marketplace.core.llm import extract_parameters_from_task
            meta = json.loads(app_row.extra_metadata or "{}")
            input_schema = meta.get("input_schema")
            extracted = extract_parameters_from_task(
                req.task, req.app_id, app_row.executor_url, input_schema=input_schema
            )
            if extracted:
                logger.info(f"Successfully extracted parameters: {extracted}")
                final_inputs.update(extracted)
            else:
                logger.info(f"No parameters extracted from task")
        except Exception as e:
            # If extraction fails, continue with empty inputs and let provider handle it
            logger.warning(f"Parameter extraction failed for {req.app_id}: {e}", exc_info=True)

    meta = json.loads(app_row.extra_metadata or "{}")
    http_method = meta.get("http_method", "GET")

    try:
        from marketplace.core.executor import execute_http
        payload = await execute_http(
            app_row.executor_url,
            method=http_method,
            params=final_inputs,
            timeout=EXECUTOR_TIMEOUT,
        )
    except Exception as e:
        errors = [f"Execution failed: {e}"]
        run_id = log_run()
        return ExecuteResponse(app_id=req.app_id, ok=False, validation_errors=errors, run_id=run_id)

    errors = validate_output(payload, require_citations=require_citations)
    if errors:
        run_id = log_run()
        return ExecuteResponse(
            app_id=req.app_id, ok=False, output=payload,
            provenance=None, validation_errors=errors, run_id=run_id,
        )

    prov = Provenance(
        sources=payload.get("citations", []) if isinstance(payload, dict) else [],
        retrieved_at=payload.get("retrieved_at", ""),
        notes=[],
    )

    ok = True
    run_id = log_run()
    if req.client_id and isinstance(payload, dict):
        _log_message(db, req.client_id, "provider", json.dumps(payload, ensure_ascii=True))
    return ExecuteResponse(app_id=req.app_id, ok=True, output=payload, provenance=prov, validation_errors=[], run_id=run_id)


# ---- API v1 versioning: /v1/shop, /v1/execute, /v1/apps ----
v1_router.post("/shop", response_model=ShopResponse)(shop)
v1_router.post("/execute", response_model=ExecuteResponse)(execute)
v1_router.get("/apps", response_model=list[AppOut])(list_apps)
v1_router.post("/apps", response_model=AppOut)(create_app)
v1_router.get("/apps/{app_id}", response_model=AppOut)(get_app)
v1_router.put("/apps/{app_id}", response_model=AppOut)(upsert_app)
app.include_router(v1_router)


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

@app.get("/runs/{run_id}", response_model=RunDetailOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    row = db.get(Run, run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    output = None
    if row.output_json:
        try:
            output = json.loads(row.output_json)
        except Exception:
            output = None
    return RunDetailOut(
        id=row.id,
        app_id=row.app_id,
        task=row.task,
        require_citations=row.require_citations,
        ok=row.ok,
        latency_ms=row.latency_ms,
        created_at=row.created_at,
        validation_errors=json.loads(row.validation_errors_json or "[]"),
        client_id=row.client_id,
        output=output,
    )

@app.get("/trust", response_model=list[TrustOut])
def list_trust(db: Session = Depends(get_db)):
    scores = _trust_scores_by_app(db)
    rows = db.query(AppListing).all()
    out: list[TrustOut] = []
    for r in rows:
        trust = scores.get(r.id)
        if trust:
            out.append(trust)
        else:
            out.append(TrustOut(
                app_id=r.id,
                total_runs=0,
                success_rate=0.0,
                citation_pass_rate=0.0,
                avg_latency_ms=None,
                p95_latency_ms=None,
                last_run_at=None,
                trust_score=0.5,
                insufficient_data=True,
            ))
    return out

@app.get("/apps/{app_id}/trust", response_model=TrustOut)
def app_trust(app_id: str, db: Session = Depends(get_db)):
    scores = _trust_scores_by_app(db)
    trust = scores.get(app_id)
    if trust:
        return trust
    row = db.get(AppListing, app_id)
    if not row:
        raise HTTPException(status_code=404, detail="App not found")
    return TrustOut(
        app_id=app_id,
        total_runs=0,
        success_rate=0.0,
        citation_pass_rate=0.0,
        avg_latency_ms=None,
        p95_latency_ms=None,
        last_run_at=None,
        trust_score=0.5,
        insufficient_data=True,
    )


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

    cache_key = _cache_key(
        "provider:openmeteo",
        {"lat": lat, "lon": lon, "timezone_name": timezone_name},
    )
    cached = _cache_get(cache_key)
    if cached:
        return cached

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

    res = {
        "answer": f"At {current.get('time','')}, temperature is {temp} C, weather_code={code}, wind_speed={wind} km/h (Open-Meteo).",
        "citations": ["https://open-meteo.com/"],
        "retrieved_at": now,
        "quality": "verified",
    }
    _cache_set(cache_key, res, PROVIDER_CACHE_TTL_WEATHER)
    return res


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

    cache_key = _cache_key("provider:wikipedia", {"q": q.strip()})
    cached = _cache_get(cache_key)
    if cached:
        return cached

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{q}"
    r = requests.get(url, timeout=10, headers={"User-Agent": "Axiomeer/0.1"})

    if r.status_code == 404:
        res = {
            "answer": f"No Wikipedia article found for '{q}'.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_WIKI)
        return res

    r.raise_for_status()
    data = r.json()

    title = data.get("title", q)
    extract = data.get("extract", "")
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

    res = {
        "answer": f"{title}: {extract}",
        "citations": [page_url] if page_url else [f"https://en.wikipedia.org/wiki/{q}"],
        "retrieved_at": now,
        "quality": "verified",
    }
    _cache_set(cache_key, res, PROVIDER_CACHE_TTL_WIKI)
    return res


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

    cache_key = _cache_key("provider:restcountries", {"q": q.strip()})
    cached = _cache_get(cache_key)
    if cached:
        return cached

    url = f"https://restcountries.com/v3.1/name/{q.strip()}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            res = {
                "answer": f"No country found matching '{q}'.",
                "citations": [f"https://restcountries.com/v3.1/name/{q}"],
                "retrieved_at": now,
                "quality": "verified",
            }
            _cache_set(cache_key, res, PROVIDER_CACHE_TTL_RESTCOUNTRIES)
            return res
        r.raise_for_status()
        data = r.json()
        country = data[0] if data else {}
        name = country.get("name", {}).get("common", q)
        capital = ", ".join(country.get("capital", ["N/A"]))
        region = country.get("region", "N/A")
        population = country.get("population", "N/A")
        languages = ", ".join(country.get("languages", {}).values()) if country.get("languages") else "N/A"
        res = {
            "answer": f"{name}: Capital: {capital}, Region: {region}, Population: {population:,} , Languages: {languages}.",
            "citations": [f"https://restcountries.com/v3.1/name/{q}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_RESTCOUNTRIES)
        return res
    except Exception as e:
        res = {
            "answer": f"Error fetching country data: {e}",
            "citations": [f"https://restcountries.com/v3.1/name/{q}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_RESTCOUNTRIES)
        return res


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
    cache_key = _cache_key("provider:exchangerate", {"base": base, "target": target})
    cached = _cache_get(cache_key)
    if cached:
        return cached

    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("result") != "success":
            res = {
                "answer": f"Exchange rate API returned non-success for '{base}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
            _cache_set(cache_key, res, PROVIDER_CACHE_TTL_FX)
            return res
        rates = data.get("rates", {})
        if target:
            if target in rates and target != base:
                rate_strs = [f"{target}: {rates[target]}"]
            else:
                rate_strs = []
        else:
            symbols = sorted([c for c in rates.keys() if c != base])
            rate_strs = [f"{c}: {rates[c]}" for c in symbols[:10]]
        res = {
            "answer": f"Exchange rates for 1 {base}: {', '.join(rate_strs[:6])}. Last updated: {data.get('time_last_update_utc', 'N/A')}.",
            "citations": [f"https://open.er-api.com/v6/latest/{base}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_FX)
        return res
    except Exception as e:
        res = {
            "answer": f"Error fetching exchange rates: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_FX)
        return res


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
    cache_key = _cache_key("provider:dictionary", {"word": word})
    cached = _cache_get(cache_key)
    if cached:
        return cached

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            res = {
                "answer": f"No definition found for '{word}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
            _cache_set(cache_key, res, PROVIDER_CACHE_TTL_DICTIONARY)
            return res
        r.raise_for_status()
        data = r.json()
        entry = data[0] if data else {}
        meanings = entry.get("meanings", [])
        defs = []
        for m in meanings[:3]:
            part = m.get("partOfSpeech", "")
            d = m.get("definitions", [{}])[0].get("definition", "")
            defs.append(f"({part}) {d}")
        res = {
            "answer": f"{word}: {'; '.join(defs)}",
            "citations": [f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_DICTIONARY)
        return res
    except Exception as e:
        res = {
            "answer": f"Error fetching definition: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_DICTIONARY)
        return res


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

    cache_key = _cache_key("provider:openlibrary", {"q": q.strip()})
    cached = _cache_get(cache_key)
    if cached:
        return cached

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
            res = {
                "answer": f"No books found for '{q}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
            _cache_set(cache_key, res, PROVIDER_CACHE_TTL_OPENLIB)
            return res
        results = []
        for doc in docs[:3]:
            title = doc.get("title", "Unknown")
            author = ", ".join(doc.get("author_name", ["Unknown"]))
            year = doc.get("first_publish_year", "N/A")
            results.append(f'"{title}" by {author} ({year})')
        res = {
            "answer": f"Books matching '{q}': {'; '.join(results)}.",
            "citations": [f"https://openlibrary.org/search?q={q}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_OPENLIB)
        return res
    except Exception as e:
        res = {
            "answer": f"Error searching books: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_OPENLIB)
        return res


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

    cache_key = _cache_key("provider:wikidata", {"q": q.strip(), "limit": limit})
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params = {
        "action": "wbsearchentities",
        "search": q.strip(),
        "language": "en",
        "format": "json",
        "limit": max(1, min(int(limit), 5)),
    }
    try:
        r = requests.get(
            "https://www.wikidata.org/w/api.php",
            params=params,
            timeout=10,
            headers={"User-Agent": "Axiomeer/0.1"},
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("search", [])
        if not results:
            res = {
                "answer": f"No Wikidata entities found for '{q}'.",
                "citations": [],
                "retrieved_at": now,
                "quality": "verified",
            }
            _cache_set(cache_key, res, PROVIDER_CACHE_TTL_WIKIDATA)
            return res
        lines = []
        citations = []
        for item in results[:3]:
            label = item.get("label", "Unknown")
            desc = item.get("description", "")
            url = item.get("url", "")
            lines.append(f"{label} — {desc}".strip(" —"))
            if url:
                citations.append(url)
        res = {
            "answer": f"Wikidata results for '{q}': " + "; ".join(lines) + ".",
            "citations": citations,
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_WIKIDATA)
        return res
    except Exception as e:
        res = {
            "answer": f"Error fetching Wikidata data: {e}",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }
        _cache_set(cache_key, res, PROVIDER_CACHE_TTL_WIKIDATA)
        return res


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

    cache_key = _cache_key("provider:wikipedia_dumps", {"lang": lang.strip().lower()})
    cached = _cache_get(cache_key)
    if cached:
        return cached

    lang = lang.strip().lower()
    dump_url = f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-pages-articles.xml.bz2"
    res = {
        "answer": f"Latest Wikipedia dump for '{lang}': {dump_url}",
        "citations": [dump_url, "https://dumps.wikimedia.org/legal.html"],
        "retrieved_at": now,
        "quality": "verified",
    }
    _cache_set(cache_key, res, PROVIDER_CACHE_TTL_WIKIDUMPS)
    return res


# ---- Auto-Bootstrap ----

MANIFESTS_DIR = Path(__file__).resolve().parent.parent.parent / "manifests"


def bootstrap_manifests():
    """Auto-register all manifests (idempotent upsert)."""
    if not MANIFESTS_DIR.exists():
        return
    db = SessionLocal()
    try:
        # Load from both old location (manifests/*.json) and new categories (manifests/categories/*/*.json)
        manifest_paths = list(MANIFESTS_DIR.glob("*.json")) + list(MANIFESTS_DIR.glob("categories/*/*.json"))

        for manifest_path in sorted(manifest_paths):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = AppCreate.model_validate(manifest).model_dump()
                app_id = manifest.get("id")
                if not app_id:
                    continue
                row = db.get(AppListing, app_id)
                if row is None:
                    row = AppListing(id=app_id)
                    db.add(row)
                row.name = manifest.get("name", app_id)
                row.description = manifest.get("description", "")
                row.category = manifest.get("category", "general")
                row.subcategory = manifest.get("subcategory")
                row.tags = ",".join(manifest.get("tags", []))
                row.capabilities = ",".join(manifest.get("capabilities", []))
                row.freshness = manifest.get("freshness", "static")
                row.citations_supported = manifest.get("citations_supported", True)
                row.product_type = manifest.get("product_type", "api")
                row.latency_est_ms = manifest.get("latency_est_ms", 500)
                row.cost_est_usd = manifest.get("cost_est_usd", 0.0)
                row.executor_type = manifest.get("executor_type", "http_api")
                row.executor_url = manifest.get("executor_url", "")
                meta = dict(manifest.get("metadata", {}))
                meta["http_method"] = (manifest.get("http_method") or "GET").upper()
                if manifest.get("input_schema"):
                    meta["input_schema"] = manifest["input_schema"]
                row.extra_metadata = json.dumps(meta)
                db.commit()
            except Exception as e:
                print(f"Error loading manifest {manifest_path}: {e}")
                continue
    finally:
        db.close()
