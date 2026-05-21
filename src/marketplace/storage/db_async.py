"""
Async SQLAlchemy engine + session factory.

Scaffold for the Phase 3 migration. Routes that need to run lots of work
concurrently inside a single event loop can use AsyncSessionLocal via the
get_async_db dependency below; sync routes keep using marketplace.storage.db.

Activation: set DATABASE_URL_ASYNC, e.g.
    DATABASE_URL_ASYNC=postgresql+asyncpg://user:pass@host/db
    DATABASE_URL_ASYNC=sqlite+aiosqlite:///./marketplace.db

Drivers required at runtime (install on demand to keep base image small):
    pip install asyncpg          # Postgres
    pip install aiosqlite        # SQLite (tests / dev)
"""
from __future__ import annotations

import os
from typing import AsyncIterator

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    _ASYNC_AVAILABLE = True
except ImportError:  # pragma: no cover - older sqlalchemy
    AsyncSession = None
    async_sessionmaker = None
    create_async_engine = None
    _ASYNC_AVAILABLE = False


_async_engine = None
AsyncSessionLocal = None


def _derive_async_url(sync_url: str | None) -> str | None:
    """Map common sync DSNs to their async equivalent."""
    if not sync_url:
        return None
    if "+asyncpg" in sync_url or "+aiosqlite" in sync_url:
        return sync_url
    if sync_url.startswith("postgresql://") or sync_url.startswith("postgres://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
            "postgres://", "postgresql+asyncpg://", 1
        )
    if sync_url.startswith("sqlite:///"):
        return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return None


def get_async_engine():
    """Lazy-init the async engine. Returns None if async stack unavailable."""
    global _async_engine, AsyncSessionLocal
    if not _ASYNC_AVAILABLE:
        return None
    if _async_engine is not None:
        return _async_engine

    url = os.getenv("DATABASE_URL_ASYNC") or _derive_async_url(os.getenv("DATABASE_URL"))
    if not url:
        return None

    kwargs: dict = {"pool_pre_ping": True}
    if "sqlite" not in url:
        kwargs.update(
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        )

    _async_engine = create_async_engine(url, **kwargs)
    AsyncSessionLocal = async_sessionmaker(_async_engine, expire_on_commit=False)
    return _async_engine


async def get_async_db() -> AsyncIterator:
    """FastAPI dependency: yield an AsyncSession.

    Raises RuntimeError when the async stack is not configured so callers fail
    loud instead of silently falling back to the sync session.
    """
    engine = get_async_engine()
    if engine is None or AsyncSessionLocal is None:
        raise RuntimeError(
            "Async DB not configured. Set DATABASE_URL_ASYNC (e.g. "
            "postgresql+asyncpg://...) and install the async driver."
        )
    async with AsyncSessionLocal() as session:
        yield session
