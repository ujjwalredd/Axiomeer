"""
Workflow status store.

Persists workflow execution state in the shared cache (Redis when configured,
in-memory fallback) so polling clients can retrieve progress across requests
and worker restarts (within the cache TTL).
"""
from __future__ import annotations

import uuid
from typing import Any

from marketplace.core.cache import cache_get, cache_set

_TTL_SECONDS = 60 * 60 * 24  # workflows live 24h after creation


def _key(workflow_id: str) -> str:
    return f"workflow:{workflow_id}"


def new_workflow_id() -> str:
    return uuid.uuid4().hex


def create(workflow_id: str, payload: dict[str, Any]) -> None:
    cache_set(_key(workflow_id), payload, _TTL_SECONDS)


def update(workflow_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    existing = cache_get(_key(workflow_id))
    if not isinstance(existing, dict):
        return None
    existing.update(patch)
    cache_set(_key(workflow_id), existing, _TTL_SECONDS)
    return existing


def get(workflow_id: str) -> dict[str, Any] | None:
    val = cache_get(_key(workflow_id))
    return val if isinstance(val, dict) else None
