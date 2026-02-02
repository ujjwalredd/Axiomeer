import json
import requests
from datetime import datetime, timezone
from time import perf_counter

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from marketplace.core.models import (
    ShopRequest, ShopResponse,
    AppCreate, AppOut,
    ExecuteRequest, ExecuteResponse, Provenance,
    RunOut,
)
from marketplace.core.router import recommend
from marketplace.core.validate import validate_output
from marketplace.storage.db import Base, engine, SessionLocal
from marketplace.storage.models import AppListing
from marketplace.storage.runs import Run

app = FastAPI(title="Axiomeer", version="0.1.0")

Base.metadata.create_all(bind=engine)


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

    recs, explanation = recommend(req, apps, k=3)

    return ShopResponse(
        status="OK" if recs else "NO_MATCH",
        recommendations=recs,
        explanation=explanation,
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
        r = requests.get(app_row.executor_url, timeout=10)
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
        )
        for r in rows
    ]


# ---- Mock Providers ----

@app.get("/providers/weather")
def provider_weather():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "answer": "Indianapolis: 31 F, cloudy (mock data).",
        "citations": ["mock://weather-provider/v1"],
        "retrieved_at": now,
        "quality": "mock",
    }


@app.get("/providers/static-weather")
def provider_static_weather():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "answer": "Weather patterns are driven by solar heating, pressure gradients, and Earth's rotation (Coriolis).",
        "citations": ["mock://static-weather-pack/v1"],
        "retrieved_at": now,
    }


@app.get("/providers/openmeteo_weather")
def provider_openmeteo_weather(lat: float = 39.7684, lon: float = -86.1581):
    """Default lat/lon is Indianapolis."""
    now = datetime.now(timezone.utc).isoformat()

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code,wind_speed_10m"
        "&timezone=UTC"
    )

    r = requests.get(url, timeout=10)
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
