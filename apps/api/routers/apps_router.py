"""
CRUD routes for AppListing.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.services import refresh_semantic_index, row_to_app_out
from marketplace.auth.dependencies import check_user_rate_limit
from marketplace.core.models import AppCreate, AppOut
from marketplace.storage.models import AppListing
from marketplace.storage.users import User

router = APIRouter(tags=["apps"])


@router.get("/apps", response_model=list[AppOut])
def list_apps(db: Session = Depends(get_db)):
    rows = db.query(AppListing).all()
    return [row_to_app_out(r) for r in rows]


@router.post("/apps", response_model=AppOut)
def create_app(
    app_in: AppCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
):
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

    refresh_semantic_index(request.app, db)
    return row_to_app_out(row)


@router.get("/apps/{app_id}", response_model=AppOut)
def get_app(app_id: str, db: Session = Depends(get_db)):
    r = db.get(AppListing, app_id)
    if not r:
        raise HTTPException(status_code=404, detail="App not found")
    return row_to_app_out(r)


@router.put("/apps/{app_id}", response_model=AppOut)
def upsert_app(
    app_id: str,
    app_in: AppCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
):
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

    refresh_semantic_index(request.app, db)
    return row_to_app_out(row)
