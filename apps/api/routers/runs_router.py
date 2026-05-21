"""
/runs routes — list and detail for execution runs.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from marketplace.auth.dependencies import check_user_rate_limit
from marketplace.core.models import RunDetailOut, RunOut
from marketplace.storage.runs import Run
from marketplace.storage.users import User

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db), current_user: User = Depends(check_user_rate_limit)):
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


@router.get("/runs/{run_id}", response_model=RunDetailOut)
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
