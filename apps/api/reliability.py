"""
Reliability helpers: idempotency-key cache for unsafe HTTP methods.

Backed by the shared cache layer (Redis when configured, in-memory fallback).
Caches the full response body keyed by (method, path, user_id, key) for a TTL.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from marketplace.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24h


def _cache_key(method: str, path: str, user_id: str, key: str) -> str:
    digest = hashlib.sha256(f"{method}|{path}|{user_id}|{key}".encode()).hexdigest()
    return f"idem:{digest}"


def _user_id_from_request(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "id", None) is not None:
        return str(user.id)
    return "anon"


async def idempotency_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method.upper() not in IDEMPOTENT_METHODS:
        return await call_next(request)

    key: str | None = request.headers.get(IDEMPOTENCY_HEADER)
    if not key:
        return await call_next(request)

    if len(key) > 128 or not key.isprintable():
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "Invalid Idempotency-Key"}},
        )

    user_id = _user_id_from_request(request)
    ck = _cache_key(request.method.upper(), request.url.path, user_id, key)

    cached = cache_get(ck)
    if isinstance(cached, dict) and "status" in cached and "body" in cached:
        return JSONResponse(
            status_code=cached["status"],
            content=cached["body"],
            headers={"Idempotent-Replay": "true"},
        )

    response = await call_next(request)

    # Only cache successful JSON responses to avoid replaying transient errors.
    if 200 <= response.status_code < 300 and isinstance(response, JSONResponse):
        try:
            body_obj = json.loads(response.body)
            cache_set(
                ck,
                {"status": response.status_code, "body": body_obj},
                _DEFAULT_TTL_SECONDS,
            )
        except Exception:  # noqa: BLE001 - non-JSON body, skip caching
            pass

    return response
