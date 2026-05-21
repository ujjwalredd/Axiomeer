"""
Axiomeer FastAPI application.

Thin composition root: wire middleware, exception handlers, lifespan, and
include routers. All route handlers live under apps/api/routers/.
"""
from __future__ import annotations

import logging
import os
import sys
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Structured logging is configured by apps.api.observability.configure_logging
# after middleware setup; this initial basicConfig keeps imports safe.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

from apps.api.auth_routes import router as auth_router
from apps.api.lifespan import lifespan
from apps.api.middleware import (
    register_exception_handlers,
    request_id_middleware,
    security_headers_middleware,
)
from apps.api.observability import (
    configure_logging,
    prometheus_middleware,
    register_metrics_endpoint,
)
from apps.api.providers import router as providers_router
from apps.api.reliability import idempotency_middleware
from apps.api.routers.apps_router import router as apps_router_module
from apps.api.routers.capabilities_router import router as capabilities_router_module
from apps.api.routers.execute_router import router as execute_router_module
from apps.api.routers.health import record_metric
from apps.api.routers.health import router as health_router
from apps.api.routers.messages_router import router as messages_router_module
from apps.api.routers.providers_inline import router as providers_inline_router
from apps.api.routers.runs_router import router as runs_router_module
from apps.api.routers.shop_router import router as shop_router_module
from apps.api.routers.trust_router import router as trust_router_module
from apps.api.routers.v1 import router as v1_router

app = FastAPI(title="Axiomeer", version="0.2.0", lifespan=lifespan)

configure_logging()
register_exception_handlers(app)
app.middleware("http")(security_headers_middleware)
app.middleware("http")(idempotency_middleware)
app.middleware("http")(prometheus_middleware)
app.middleware("http")(request_id_middleware)
register_metrics_endpoint(app)

# CORS — restrict to configured origins in production. Wildcard ("*") is only
# valid without credentials per CORS spec; toggle accordingly.
_cors_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()] or ["*"]
_allow_credentials = _cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID", "Idempotency-Key"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def legacy_metrics_middleware(request: Request, call_next):
    """Populate the legacy in-memory metrics map for the /metrics JSON endpoint."""
    start = perf_counter()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        latency_ms = int((perf_counter() - start) * 1000)
        record_metric(request.url.path, latency_ms, True)
        raise
    latency_ms = int((perf_counter() - start) * 1000)
    record_metric(request.url.path, latency_ms, status_code >= 500)
    return response


# Routers grouped so each can be exposed both at "/" (back-compat) and under
# "/v1" (new versioned namespace). Existing SDK clients keep working at the
# unprefixed paths; new integrations should target /v1.
_VERSIONED_ROUTERS = [
    health_router,
    apps_router_module,
    shop_router_module,
    execute_router_module,
    runs_router_module,
    trust_router_module,
    messages_router_module,
    capabilities_router_module,
]

for r in _VERSIONED_ROUTERS:
    app.include_router(r)
    app.include_router(r, prefix="/v1")

# Inline provider endpoints (/providers/*) are deployment-internal — only
# mounted at root since manifests reference these absolute paths.
app.include_router(providers_inline_router)

# Other first-party providers (apps/api/providers.py).
app.include_router(providers_router)

# Auth + extra v1 features (tools/schemas, dashboard).
app.include_router(auth_router)
app.include_router(v1_router)
