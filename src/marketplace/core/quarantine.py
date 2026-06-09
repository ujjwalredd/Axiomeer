"""
Provider auto-quarantine.

A background task scans the recent Run history per app. Apps with a success
rate below a threshold over a sliding window are added to a "quarantined" set
stored in the shared cache; the router consults this set and filters those
apps out of recommendations.

State is intentionally cache-backed rather than a schema column so this can
ship without an Alembic migration. To make quarantine durable across cache
expiry, persist `app_listing.disabled` in a follow-up migration and switch
the read path to that column.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from marketplace.core.cache import cache_get, cache_set
from marketplace.storage.runs import Run

logger = logging.getLogger(__name__)

QUARANTINE_KEY = "axiomeer:quarantine:apps"
_TTL_SECONDS = 60 * 60 * 25  # rebuild hourly; 25h TTL guarantees overlap


@dataclass
class QuarantineConfig:
    window_hours: int = int(os.getenv("QUARANTINE_WINDOW_HOURS", "24"))
    min_runs: int = int(os.getenv("QUARANTINE_MIN_RUNS", "10"))
    success_floor: float = float(os.getenv("QUARANTINE_SUCCESS_FLOOR", "0.5"))


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def evaluate(db: Session, cfg: QuarantineConfig | None = None) -> list[str]:
    """Compute the current quarantine list. Pure function — no side effects on DB."""
    cfg = cfg or QuarantineConfig()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cfg.window_hours)

    runs = db.query(Run).all()
    buckets: dict[str, list[bool]] = defaultdict(list)
    for r in runs:
        ts = _parse_iso(r.created_at)
        if ts is None or ts.tzinfo is None:
            # rows without tz info — treat as UTC
            ts = ts.replace(tzinfo=timezone.utc) if ts else None
        if ts is None or ts < cutoff:
            continue
        buckets[r.app_id].append(bool(r.ok))

    quarantined: list[str] = []
    for app_id, outcomes in buckets.items():
        if len(outcomes) < cfg.min_runs:
            continue
        success_rate = sum(outcomes) / len(outcomes)
        if success_rate < cfg.success_floor:
            quarantined.append(app_id)
    return sorted(quarantined)


def refresh(db: Session, cfg: QuarantineConfig | None = None) -> list[str]:
    """Recompute and persist the quarantine set."""
    qids = evaluate(db, cfg)
    cache_set(QUARANTINE_KEY, qids, _TTL_SECONDS)
    if qids:
        logger.info("Quarantined %d providers: %s", len(qids), qids)
    return qids


def current() -> set[str]:
    val = cache_get(QUARANTINE_KEY)
    if isinstance(val, list):
        return set(val)
    return set()


def filter_apps(apps: Iterable[dict]) -> list[dict]:
    """Return apps not currently quarantined. Used by the router."""
    q = current()
    if not q:
        return list(apps)
    return [a for a in apps if a.get("id") not in q]
