"""
Health, metrics, and semantic-search status routes.
"""
from __future__ import annotations

from threading import Lock

from fastapi import APIRouter, Depends, Request

from marketplace.auth.dependencies import check_user_rate_limit
from marketplace.storage.users import User

router = APIRouter(tags=["health"])

# Legacy in-memory request metrics. Prometheus is the modern path
# (apps.api.observability) but we keep this for backward-compat consumers.
_metrics_lock = Lock()
_metrics: dict[str, dict[str, int]] = {}


def record_metric(path: str, latency_ms: int, is_error: bool) -> None:
    with _metrics_lock:
        stats = _metrics.setdefault(
            path,
            {"count": 0, "error_count": 0, "total_latency_ms": 0, "max_latency_ms": 0},
        )
        latency_ms_int = max(0, int(latency_ms))
        stats["count"] += 1
        stats["total_latency_ms"] += latency_ms_int
        if latency_ms_int > stats["max_latency_ms"]:
            stats["max_latency_ms"] = latency_ms_int
        if is_error:
            stats["error_count"] += 1


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/metrics")
def metrics(current_user: User = Depends(check_user_rate_limit)):
    """Lightweight in-memory metrics. Requires authentication when AUTH_ENABLED=true."""
    with _metrics_lock:
        out: dict[str, dict[str, int | None]] = {}
        for path, stats in _metrics.items():
            count = stats["count"]
            avg_ms: int | None = None
            if count > 0:
                avg_ms = int(stats["total_latency_ms"] / count)
            out[path] = {
                "count": count,
                "error_count": stats["error_count"],
                "avg_latency_ms": avg_ms,
                "max_latency_ms": stats["max_latency_ms"],
            }
    return out


@router.get("/semantic-search/stats")
def semantic_search_stats(request: Request):
    semantic_engine = getattr(request.app.state, "semantic_search", None)
    if semantic_engine:
        return semantic_engine.get_stats()
    return {
        "enabled": False,
        "initialized": False,
        "error": "Semantic search engine not initialized",
    }
