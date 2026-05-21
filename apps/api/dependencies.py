"""
Shared FastAPI dependencies and cache helpers for the API layer.
"""
from __future__ import annotations

import json
from typing import Any

from marketplace.storage.db import SessionLocal
from marketplace.storage.users import User

TRUST_CACHE_KEY = "axiomeer:trust_scores_all"


def get_db():
    """Yield a SQLAlchemy session and ensure it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def cache_key(prefix: str, payload: dict) -> str:
    return f"{prefix}:{json.dumps(payload, sort_keys=True, default=str)}"


def cache_get(key: str) -> Any | None:
    try:
        from marketplace.core.cache import cache_get as _get
        return _get(key)
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    try:
        from marketplace.core.cache import cache_set as _set
        _set(key, value, ttl_seconds)
    except Exception:
        pass


def scoped_client_id(client_id: str | None, user: User) -> str | None:
    """Scope client_id to authenticated user to prevent cross-user history leakage."""
    if not client_id:
        return None
    from marketplace.settings import AUTH_ENABLED
    if AUTH_ENABLED and user.id > 0:
        return f"u{user.id}:{client_id}"
    return client_id
