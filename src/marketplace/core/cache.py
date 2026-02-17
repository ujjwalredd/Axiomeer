"""
Unified cache backend: Redis when available, in-memory fallback.
"""
from __future__ import annotations

import json
import logging
import os
import time
from threading import Lock
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client: Optional[Any] = None
_memory_store: dict[str, dict] = {}
_memory_lock = Lock()


def _init_redis() -> bool:
    global _redis_client
    if _redis_client is not None:
        return True
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return False
    try:
        import redis
        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis cache connected")
        return True
    except Exception as e:
        logger.warning(f"Redis unavailable, using in-memory cache: {e}")
        return False


def cache_get(key: str) -> Optional[Any]:
    """Get value from cache. Returns None if missing or expired."""
    if _init_redis():
        try:
            raw = _redis_client.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
    with _memory_lock:
        entry = _memory_store.get(key)
        if not entry or entry["expires_at"] <= time.time():
            _memory_store.pop(key, None)
            return None
        return entry["value"]


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    """Set value in cache with TTL."""
    if ttl_seconds <= 0:
        return
    if _init_redis():
        try:
            _redis_client.setex(key, ttl_seconds, json.dumps(value, default=str, ensure_ascii=False))
            return
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
    with _memory_lock:
        _memory_store[key] = {"value": value, "expires_at": time.time() + ttl_seconds}


def cache_available() -> bool:
    """Whether Redis is available."""
    return _init_redis()
