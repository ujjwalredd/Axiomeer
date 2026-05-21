"""
Tests for cross-cutting middleware: request IDs, security headers, error envelope.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.middleware import (
    REQUEST_ID_HEADER,
    register_exception_handlers,
    request_id_middleware,
    security_headers_middleware,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(request_id_middleware)
    register_exception_handlers(app)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def test_request_id_is_generated_when_missing() -> None:
    client = TestClient(_make_app())
    r = client.get("/ok")
    assert r.status_code == 200
    assert REQUEST_ID_HEADER in r.headers
    assert len(r.headers[REQUEST_ID_HEADER]) >= 16


def test_request_id_is_echoed_when_provided() -> None:
    client = TestClient(_make_app())
    rid = "test-1234567890abcdef"
    r = client.get("/ok", headers={REQUEST_ID_HEADER: rid})
    assert r.headers[REQUEST_ID_HEADER] == rid


def test_security_headers_present() -> None:
    client = TestClient(_make_app())
    r = client.get("/ok")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "max-age=" in r.headers["Strict-Transport-Security"]


def test_unhandled_exception_returns_envelope() -> None:
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["request_id"]
    # Legacy `detail` field preserved for back-compat with existing SDK clients
    assert body["detail"] == body["error"]["message"]
