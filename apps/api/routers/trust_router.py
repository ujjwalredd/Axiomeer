"""
Trust score routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.services import trust_scores_by_app
from marketplace.core.models import TrustOut
from marketplace.storage.models import AppListing

router = APIRouter(tags=["trust"])


def _zero_trust(app_id: str) -> TrustOut:
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


@router.get("/trust", response_model=list[TrustOut])
def list_trust(db: Session = Depends(get_db)):
    scores = trust_scores_by_app(db)
    rows = db.query(AppListing).all()
    out: list[TrustOut] = []
    for r in rows:
        trust = scores.get(r.id)
        out.append(trust if trust else _zero_trust(r.id))
    return out


@router.get("/apps/{app_id}/trust", response_model=TrustOut)
def app_trust(app_id: str, db: Session = Depends(get_db)):
    scores = trust_scores_by_app(db)
    trust = scores.get(app_id)
    if trust:
        return trust
    row = db.get(AppListing, app_id)
    if not row:
        raise HTTPException(status_code=404, detail="App not found")
    return _zero_trust(app_id)
