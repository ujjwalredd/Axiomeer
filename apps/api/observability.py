"""
Observability: structured logging filter, Prometheus metrics.

Prometheus is optional — if `prometheus_client` is not installed, the helpers
become no-ops so the app still boots in minimal dev environments.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Histogram,
        generate_latest,
    )

    _registry = CollectorRegistry()
    REQUEST_COUNT = Counter(
        "axiomeer_http_requests_total",
        "HTTP request count",
        ["method", "path", "status"],
        registry=_registry,
    )
    REQUEST_LATENCY = Histogram(
        "axiomeer_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        registry=_registry,
    )
    PROVIDER_CALLS = Counter(
        "axiomeer_provider_calls_total",
        "Outbound provider calls",
        ["app_id", "outcome"],
        registry=_registry,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _registry = None
    REQUEST_COUNT = None
    REQUEST_LATENCY = None
    PROVIDER_CALLS = None
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain"


def _normalize_path(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


async def prometheus_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    if not PROMETHEUS_AVAILABLE:
        return await call_next(request)

    start = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = perf_counter() - start
        path = _normalize_path(request)
        REQUEST_COUNT.labels(request.method, path, str(status_code)).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(duration)


def record_provider_call(app_id: str, ok: bool) -> None:
    if PROMETHEUS_AVAILABLE and PROVIDER_CALLS is not None:
        PROVIDER_CALLS.labels(app_id or "unknown", "ok" if ok else "error").inc()


def register_metrics_endpoint(app: FastAPI, path: str = "/metrics/prom") -> None:
    """Expose Prometheus scrape endpoint. Separate path keeps the legacy
    /metrics JSON endpoint working until clients migrate."""

    @app.get(path, include_in_schema=False)
    def _metrics():
        if not PROMETHEUS_AVAILABLE:
            return PlainTextResponse(
                "prometheus_client not installed\n", status_code=503
            )
        return PlainTextResponse(generate_latest(_registry), media_type=CONTENT_TYPE_LATEST)


class RequestIdLogFilter(logging.Filter):
    """Inject request_id from contextvar (if available) into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Install the request-id filter and a richer format."""
    root = logging.getLogger()
    for h in root.handlers:
        h.addFilter(RequestIdLogFilter())
    fmt = "%(asctime)s | %(levelname)s | %(name)s | rid=%(request_id)s | %(message)s"
    for h in root.handlers:
        h.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    root.setLevel(level)
