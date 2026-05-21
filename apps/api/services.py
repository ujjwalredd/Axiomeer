"""
Service-layer helpers shared by the API routers.

Keeps router modules thin: business logic that touches the DB or transforms
ORM rows lives here. No FastAPI dependency on these functions so they can be
unit-tested directly.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy.orm import Session

from marketplace.core.models import AppOut, TrustOut
from marketplace.core.router import _latency_score
from marketplace.settings import TRUST_CACHE_TTL
from marketplace.storage.messages import ConversationMessage
from marketplace.storage.models import AppListing
from marketplace.storage.runs import Run

from apps.api.dependencies import TRUST_CACHE_KEY, cache_get, cache_set

logger = logging.getLogger(__name__)


def row_to_app_out(r: AppListing) -> AppOut:
    """Convert an ORM AppListing row to an AppOut response."""
    try:
        metadata = json.loads(r.extra_metadata) if r.extra_metadata else {}
    except Exception:
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


def refresh_semantic_index(app: FastAPI, db: Session) -> None:
    """Refresh the semantic search index with all products from the database."""
    semantic_engine = getattr(app.state, "semantic_search", None)
    if semantic_engine and semantic_engine.is_available():
        rows = db.query(AppListing).all()
        products = [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "capabilities": [c for c in r.capabilities.split(",") if c],
            }
            for r in rows
        ]
        if products:
            semantic_engine.add_products(products)


def p95(values: list[int]) -> int | None:
    if not values:
        return None
    values = sorted(values)
    idx = max(0, int(round(0.95 * (len(values) - 1))))
    return values[idx]


def trust_scores_by_app(db: Session) -> dict[str, TrustOut]:
    """Compute (and cache) trust scores for every app."""
    cached = cache_get(TRUST_CACHE_KEY)
    if cached and isinstance(cached, dict):
        try:
            return {k: TrustOut(**v) for k, v in cached.items()}
        except Exception:
            # Stale or schema-incompatible cache entry — recompute below.
            pass

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
        p95_latency = p95(latencies)
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

    cache_set(TRUST_CACHE_KEY, {k: v.model_dump() for k, v in results.items()}, TRUST_CACHE_TTL)
    return results


def history_for_client(db: Session, client_id: str, limit: int) -> list[dict]:
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.client_id == client_id)
        .order_by(ConversationMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        {"role": r.role, "content": r.content, "created_at": r.created_at}
        for r in rows
    ]


def log_message(db: Session, client_id: str, role: str, content: str) -> None:
    msg = ConversationMessage(
        client_id=client_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(msg)
    db.commit()
