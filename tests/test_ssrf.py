"""
Regression tests for the SSRF protection in marketplace.core.executor.

Covers the URL validator added in response to the unauthenticated SSRF via
the app-registration -> /execute chain.
"""
from __future__ import annotations

import socket

import pytest

from marketplace.core.executor import UnsafeURLError, validate_safe_url


@pytest.fixture(autouse=True)
def _no_trusted_hosts(monkeypatch):
    """Empty the trusted-host allowlist so private/loopback addresses are blocked.

    The default allowlist includes 127.0.0.1/localhost to support first-party
    internal providers; for the SSRF regression tests we want strict behavior.
    """
    monkeypatch.setenv("EXECUTOR_TRUSTED_HOSTS", "")


@pytest.mark.parametrize(
    "url",
    [
        # Cloud metadata endpoints
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://metadata/",
        # Loopback (IPv4 + IPv6)
        "http://127.0.0.1/",
        "http://localhost/",
        "http://[::1]/",
        # RFC1918 private ranges
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        # Link-local
        "http://169.254.10.10/",
        # Unspecified
        "http://0.0.0.0/",
        # Disallowed schemes
        "file:///etc/passwd",
        "gopher://x/",
        "ftp://example.com/",
        # Empty / malformed
        "",
        "not-a-url",
    ],
)
def test_validate_safe_url_blocks_dangerous(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        validate_safe_url(url)


def test_validate_safe_url_allows_public_ip_literal() -> None:
    # 1.1.1.1 is a public IP literal — no DNS lookup needed.
    assert validate_safe_url("https://1.1.1.1/") == "https://1.1.1.1/"


def test_validate_safe_url_dns_failure_is_blocked(monkeypatch) -> None:
    def boom(*_a, **_kw):
        raise socket.gaierror("forced failure")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(UnsafeURLError):
        validate_safe_url("https://definitely-not-a-real-host.invalid/")


def test_validate_safe_url_blocks_when_dns_resolves_to_private(monkeypatch) -> None:
    def fake(*_a, **_kw):
        return [(2, 1, 6, "", ("10.0.0.5", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake)
    with pytest.raises(UnsafeURLError):
        validate_safe_url("https://attacker-controlled.example/")


def test_validate_safe_url_allows_public_dns(monkeypatch) -> None:
    def fake(*_a, **_kw):
        return [(2, 1, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake)
    assert validate_safe_url("https://example.com/") == "https://example.com/"


def test_trusted_hosts_bypass_private_check(monkeypatch) -> None:
    """First-party internal providers (e.g., 127.0.0.1 inside the cluster)
    must be reachable when explicitly allowlisted."""
    monkeypatch.setenv("EXECUTOR_TRUSTED_HOSTS", "127.0.0.1,localhost")
    assert validate_safe_url("http://127.0.0.1:8000/providers/x") == "http://127.0.0.1:8000/providers/x"
    assert validate_safe_url("http://localhost:8000/providers/x") == "http://localhost:8000/providers/x"
