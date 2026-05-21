"""
/capabilities — deduplicated capability explorer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from marketplace.storage.models import AppListing

router = APIRouter(tags=["capabilities"])


@router.get("/capabilities")
def list_capabilities(db: Session = Depends(get_db)):
    rows = db.query(AppListing).all()
    caps: set[str] = set()
    for r in rows:
        for c in r.capabilities.split(","):
            c = c.strip()
            if c:
                caps.add(c)
    return {"capabilities": sorted(caps), "count": len(caps)}
