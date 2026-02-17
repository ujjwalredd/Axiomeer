"""
API v1 router: tools schemas, dashboard.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from marketplace.auth.dependencies import get_current_user
from marketplace.storage.db import SessionLocal
from marketplace.storage.models import AppListing
from marketplace.storage.users import User, UsageRecord

router = APIRouter(prefix="/v1", tags=["v1"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- Tool Schemas (OpenAI/Anthropic function calling) ----


@router.get("/tools/schemas")
def get_tool_schemas(
    format: str = Query("openai", description="openai or anthropic"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Export all tools as schemas for OpenAI function calling or Anthropic tool use.
    Use these schemas for AI agents to discover and call Axiomeer APIs.
    """
    rows = db.query(AppListing).all()
    tools: List[Dict[str, Any]] = []

    for r in rows:
        meta = json.loads(r.extra_metadata or "{}")
        input_schema = meta.get("input_schema", {})
        params_list = input_schema.get("parameters", [])
        if not params_list:
            params_list = ["task"]

        properties = {}
        for p in params_list:
            properties[p] = {"type": "string", "description": f"Parameter: {p}"}

        tool_def = {
            "name": r.id.replace("-", "_"),
            "description": f"{r.name}: {r.description}",
            "parameters": {
                "type": "object",
                "properties": {
                    **properties,
                    "task": {"type": "string", "description": "Natural language task"},
                },
                "required": ["task"] if "task" not in params_list else list(params_list),
            },
        }

        if format == "anthropic":
            tools.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "input_schema": tool_def["parameters"],
            })
        else:
            tools.append({"type": "function", "function": tool_def})

    return {"tools": tools, "format": format, "count": len(tools)}


# ---- Usage Dashboard ----


@router.get("/dashboard/usage")
def get_usage_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
) -> Dict[str, Any]:
    """
    Usage dashboard: requests, cost per endpoint for the authenticated user.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    records = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == current_user.id,
            UsageRecord.created_at >= since,
        )
        .all()
    )

    by_endpoint: Dict[str, Dict[str, Any]] = {}
    for r in records:
        key = r.endpoint
        if key not in by_endpoint:
            by_endpoint[key] = {"count": 0, "cost_usd": 0.0}
        by_endpoint[key]["count"] += 1
        by_endpoint[key]["cost_usd"] += r.cost_usd

    return {
        "user_id": current_user.id,
        "period_hours": hours,
        "usage_by_endpoint": by_endpoint,
        "total_requests": len(records),
        "total_cost_usd": sum(r.cost_usd for r in records),
    }
