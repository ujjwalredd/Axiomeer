# Async DB migration guide

The existing FastAPI routes use the synchronous SQLAlchemy session
(`marketplace.storage.db.SessionLocal`). To migrate a route to async without
touching the whole codebase at once, follow these steps.

## 1. Configure the async DSN

```bash
# Postgres in production
export DATABASE_URL_ASYNC=postgresql+asyncpg://user:pass@host/axiomeer

# SQLite for local dev / tests
export DATABASE_URL_ASYNC=sqlite+aiosqlite:///./marketplace.db
```

If unset, `marketplace.storage.db_async.get_async_engine()` returns `None`
and any route depending on `get_async_db` fails fast with a clear error.

## 2. Install the driver

```bash
pip install asyncpg     # for Postgres
pip install aiosqlite   # for SQLite
```

## 3. Convert one route

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from marketplace.storage.db_async import get_async_db
from marketplace.storage.models import AppListing

@router.get("/apps")
async def list_apps(db: AsyncSession = Depends(get_async_db)):
    rows = (await db.execute(select(AppListing))).scalars().all()
    return [...]
```

## 4. Run the route's tests

The sync and async sessions can coexist. Migrate routes one at a time and
keep the test suite green at each step.

## What stays sync (for now)

- Lifespan bootstrap (`Base.metadata.create_all` and manifest loading) —
  sync engine is fine and gives a clearer startup error path.
- The health monitor and quarantine background tasks — they create their own
  short-lived sync sessions per tick.

## When to finish the migration

Once `/execute`, `/execute/workflow`, and `/shop` are async-end-to-end, the
event loop can saturate the pool with concurrent provider calls. Until then,
async DB inside an otherwise-sync route does not improve throughput.
