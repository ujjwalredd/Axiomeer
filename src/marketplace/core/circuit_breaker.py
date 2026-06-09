"""
Per-host circuit breaker for outbound provider calls.

Three states:
  closed  -> normal, failures counted
  open    -> all calls fail fast with CircuitOpenError until cool-off elapses
  half_open -> single probe allowed; success closes, failure re-opens

State is in-process only (resets on restart) — fine for the current single-
worker deployment. For multi-worker / multi-pod, back this with Redis or a
shared store.
"""
from __future__ import annotations

import os
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar
from urllib.parse import urlparse

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when the circuit is open and the call is short-circuited."""


_FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "5"))
_RESET_AFTER_SECONDS = float(os.getenv("CB_RESET_AFTER_SECONDS", "30"))


@dataclass
class _State:
    failures: int = 0
    opened_at: float | None = None
    half_open: bool = False


_state_by_host: dict[str, _State] = {}
_lock = threading.Lock()


def _host_of(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def _get_state(host: str) -> _State:
    with _lock:
        s = _state_by_host.get(host)
        if s is None:
            s = _State()
            _state_by_host[host] = s
        return s


def _is_open(state: _State) -> bool:
    if state.opened_at is None:
        return False
    if time.monotonic() - state.opened_at >= _RESET_AFTER_SECONDS:
        # Cool-off complete; allow one probe (half-open).
        state.opened_at = None
        state.half_open = True
        return False
    return True


def record_success(host: str) -> None:
    state = _get_state(host)
    with _lock:
        state.failures = 0
        state.opened_at = None
        state.half_open = False


def record_failure(host: str) -> None:
    state = _get_state(host)
    with _lock:
        state.failures += 1
        if state.half_open or state.failures >= _FAILURE_THRESHOLD:
            state.opened_at = time.monotonic()
            state.half_open = False


def check(url: str) -> str:
    """Raise CircuitOpenError if the host is currently in open state.
    Returns the resolved host (used by callers to record outcome)."""
    host = _host_of(url)
    if not host:
        return host
    state = _get_state(host)
    with _lock:
        if _is_open(state):
            raise CircuitOpenError(f"Circuit open for host {host!r}; try again later")
    return host


async def call_async(url: str, fn: Callable[[], Awaitable[T]]) -> T:
    host = check(url)
    try:
        result = await fn()
    except Exception:
        if host:
            record_failure(host)
        raise
    if host:
        record_success(host)
    return result


def call_sync(url: str, fn: Callable[[], T]) -> T:
    host = check(url)
    try:
        result = fn()
    except Exception:
        if host:
            record_failure(host)
        raise
    if host:
        record_success(host)
    return result


def reset_all() -> None:
    """Test/admin helper — clear every breaker."""
    with _lock:
        _state_by_host.clear()


def snapshot() -> dict[str, dict[str, object]]:
    """Return current state per host for /metrics or admin debugging."""
    with _lock:
        out = {}
        for host, s in _state_by_host.items():
            out[host] = {
                "failures": s.failures,
                "open": s.opened_at is not None,
                "half_open": s.half_open,
                "opened_at_monotonic": s.opened_at,
            }
        return out
