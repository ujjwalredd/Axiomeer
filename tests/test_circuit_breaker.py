"""
Unit tests for the per-host circuit breaker.
"""
from __future__ import annotations

import asyncio
import os
import time

import pytest

from marketplace.core import circuit_breaker as cb


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    cb.reset_all()
    monkeypatch.setattr(cb, "_FAILURE_THRESHOLD", 3, raising=True)
    monkeypatch.setattr(cb, "_RESET_AFTER_SECONDS", 0.05, raising=True)
    yield
    cb.reset_all()


def test_closed_state_passes_calls_through():
    result = cb.call_sync("https://example.com/x", lambda: 42)
    assert result == 42


def test_opens_after_threshold_failures():
    def boom():
        raise RuntimeError("upstream down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call_sync("https://flaky.example/x", boom)

    with pytest.raises(cb.CircuitOpenError):
        cb.call_sync("https://flaky.example/x", boom)


def test_half_open_lets_one_probe_then_closes_on_success():
    def boom():
        raise RuntimeError("down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call_sync("https://probe.example/x", boom)
    with pytest.raises(cb.CircuitOpenError):
        cb.call_sync("https://probe.example/x", boom)

    time.sleep(0.06)
    assert cb.call_sync("https://probe.example/x", lambda: "ok") == "ok"
    assert cb.call_sync("https://probe.example/x", lambda: "ok") == "ok"


def test_half_open_reopens_on_failure():
    def boom():
        raise RuntimeError("down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call_sync("https://reopen.example/x", boom)

    time.sleep(0.06)
    with pytest.raises(RuntimeError):
        cb.call_sync("https://reopen.example/x", boom)
    with pytest.raises(cb.CircuitOpenError):
        cb.call_sync("https://reopen.example/x", boom)


def test_async_path():
    async def main():
        async def boom():
            raise RuntimeError("down")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call_async("https://async.example/x", boom)
        with pytest.raises(cb.CircuitOpenError):
            await cb.call_async("https://async.example/x", boom)

    asyncio.run(main())


def test_independent_hosts_dont_affect_each_other():
    def boom():
        raise RuntimeError("down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call_sync("https://hostA.example/", boom)
    with pytest.raises(cb.CircuitOpenError):
        cb.call_sync("https://hostA.example/", boom)

    assert cb.call_sync("https://hostB.example/", lambda: "ok") == "ok"
