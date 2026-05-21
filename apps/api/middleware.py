"""
Cross-cutting HTTP middleware: request IDs, security headers, error envelope.
"""
from __future__ import annotations

import logging
import uuid
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


def _new_request_id() -> str:
    return uuid.uuid4().hex


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    rid = request.headers.get(REQUEST_ID_HEADER) or _new_request_id()
    request.state.request_id = rid
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = rid
    return response


async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
    )
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response


def _envelope(code: str, message: str, request_id: str | None, details=None, status_code: int = 400):
    # `detail` is preserved alongside the structured `error` envelope so that
    # legacy SDK clients (which read FastAPI's default {"detail": "..."} shape)
    # keep working after the upgrade.
    body = {
        "detail": message,
        "error": {"code": code, "message": message, "request_id": request_id},
    }
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers that return a consistent error envelope."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        rid = getattr(request.state, "request_id", None)
        code = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "unprocessable_entity",
            429: "rate_limited",
        }.get(exc.status_code, "http_error")
        return _envelope(code, str(exc.detail), rid, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError):
        rid = getattr(request.state, "request_id", None)
        return _envelope(
            "validation_error",
            "Request validation failed",
            rid,
            details=exc.errors(),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None)
        logger.exception("Unhandled error", extra={"request_id": rid})
        return _envelope("internal_error", "Internal server error", rid, status_code=500)
