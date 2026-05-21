"""
Tests for the provider auto-quarantine.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from marketplace.core import quarantine
from marketplace.storage.db import Base, SessionLocal, engine
from marketplace.storage.runs import Run


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    try:
        s.query(Run).delete()
        s.commit()
        yield s
    finally:
        s.close()


def _add_run(db, app_id: str, ok: bool):
    now = datetime.now(timezone.utc).isoformat()
    db.add(Run(
        app_id=app_id, task="t", client_id=None, require_citations=False,
        ok=ok, output_json=None, validation_errors_json="[]",
        latency_ms=100, created_at=now,
    ))
    db.commit()


def test_quarantines_failing_provider(db):
    for _ in range(2):
        _add_run(db, "good-app", True)
    for _ in range(8):
        _add_run(db, "good-app", True)
    for _ in range(8):
        _add_run(db, "bad-app", False)
    for _ in range(2):
        _add_run(db, "bad-app", True)

    qids = quarantine.evaluate(db)
    assert "bad-app" in qids
    assert "good-app" not in qids


def test_below_min_runs_not_quarantined(db):
    for _ in range(3):
        _add_run(db, "few-runs", False)

    qids = quarantine.evaluate(db)
    assert "few-runs" not in qids


def test_filter_apps_drops_quarantined(monkeypatch):
    monkeypatch.setattr(quarantine, "current", lambda: {"bad-app"})
    out = quarantine.filter_apps([{"id": "good-app"}, {"id": "bad-app"}])
    assert [a["id"] for a in out] == ["good-app"]
