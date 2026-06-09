"""
FastAPI lifespan: DB schema bootstrap, manifest seeding, semantic index init,
periodic provider health monitor, graceful shutdown of shared resources.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from time import perf_counter

import httpx
from fastapi import FastAPI

from apps.api.bootstrap import bootstrap_manifests
from apps.api.dependencies import TRUST_CACHE_KEY, cache_set
from marketplace.core.executor import close_shared_async_client
from marketplace.storage.db import Base, SessionLocal, engine
from marketplace.storage.models import AppListing

logger = logging.getLogger(__name__)


async def _quarantine_monitor():
    """Periodically recompute the auto-quarantine set from recent Run history."""
    from marketplace.core.quarantine import refresh

    interval = 60 * 30  # every 30 min
    while True:
        try:
            db = SessionLocal()
            try:
                refresh(db)
            finally:
                db.close()
        except Exception as e:
            logger.warning("Quarantine monitor error: %s", e)
        await asyncio.sleep(interval)


async def _health_monitor():
    """Periodically ping internal provider URLs to refresh latency estimates."""
    from marketplace.settings import API_BASE_URL

    while True:
        await asyncio.sleep(300)
        try:
            db = SessionLocal()
            try:
                rows = (
                    db.query(AppListing)
                    .filter(AppListing.executor_url.like(f"{API_BASE_URL}%"))
                    .all()
                )
                async with httpx.AsyncClient(timeout=5) as client:
                    for r in rows:
                        t_start = perf_counter()
                        try:
                            await client.get(r.executor_url)
                            r.latency_est_ms = int((perf_counter() - t_start) * 1000)
                        except Exception:
                            pass
                db.commit()
                cache_set(TRUST_CACHE_KEY, {}, 1)
                logger.info("Health monitor: refreshed latency estimates")
            finally:
                db.close()
        except Exception as e:
            logger.warning("Health monitor error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_manifests()

    from marketplace.core.semantic_search import SemanticSearchEngine
    from marketplace.settings import SEMANTIC_SEARCH_ENABLED, SEMANTIC_SEARCH_MODEL

    semantic_engine = SemanticSearchEngine(
        model_name=SEMANTIC_SEARCH_MODEL, enabled=SEMANTIC_SEARCH_ENABLED,
    )
    app.state.semantic_search = semantic_engine

    if SEMANTIC_SEARCH_ENABLED:
        db = SessionLocal()
        try:
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
        finally:
            db.close()

    health_task = asyncio.create_task(_health_monitor())
    quarantine_task = asyncio.create_task(_quarantine_monitor())

    yield

    for task in (health_task, quarantine_task):
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    await close_shared_async_client()
