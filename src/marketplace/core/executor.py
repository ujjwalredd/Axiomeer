"""
HTTP executor for provider calls with retry logic and GET/POST support.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import socket
from typing import Any
from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.goog",
    "metadata.azure.com",
    "metadata",
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
}


class UnsafeURLError(ValueError):
    """Raised when a URL targets a disallowed host (SSRF protection)."""


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_safe_url(url: str) -> str:
    """
    Validate URL is safe to fetch (SSRF protection).

    Enforces:
      - Scheme is http or https
      - Hostname is present
      - Hostname is not a known cloud-metadata / loopback alias
      - All resolved IPs are public (no RFC1918, loopback, link-local, etc.)

    Returns the input URL unchanged on success.
    Raises UnsafeURLError on failure.
    """
    if not url or not isinstance(url, str):
        raise UnsafeURLError("URL is required")

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError(f"URL scheme must be http or https, got: {parsed.scheme!r}")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL must include a hostname")

    host_lc = hostname.lower()
    if host_lc in _BLOCKED_HOSTNAMES:
        raise UnsafeURLError(f"Hostname not allowed: {hostname}")

    # If the hostname is an IP literal, check it directly.
    try:
        ip_literal = ipaddress.ip_address(host_lc)
        if _ip_is_blocked(ip_literal):
            raise UnsafeURLError(f"IP address not allowed: {ip_literal}")
        return url
    except ValueError:
        pass

    # Resolve DNS and verify every returned address is public.
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Unable to resolve host {hostname!r}: {exc}") from exc

    seen = set()
    for info in infos:
        addr = info[4][0]
        if addr in seen:
            continue
        seen.add(addr)
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            raise UnsafeURLError(f"Resolved address is not a valid IP: {addr}")
        if _ip_is_blocked(ip):
            raise UnsafeURLError(f"Host {hostname} resolves to disallowed address {addr}")

    return url


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def execute_http(
    url: str,
    method: str,
    params: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    """
    Execute HTTP request to provider with retry on transient failures.

    Args:
        url: Provider endpoint URL
        method: GET or POST
        params: Query params (GET) or JSON body (POST)
        timeout: Request timeout in seconds

    Returns:
        JSON response as dict

    Raises:
        httpx.HTTPError: On request failure after retries
    """
    method = (method or "GET").upper()
    if method not in ("GET", "POST"):
        method = "GET"

    validate_safe_url(url)

    async with httpx.AsyncClient() as client:
        if method == "POST":
            response = await client.post(
                url,
                json=params,
                timeout=timeout,
            )
        else:
            response = await client.get(
                url,
                params=params,
                timeout=timeout,
            )
        response.raise_for_status()
        return response.json()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
def execute_http_sync(
    url: str,
    method: str,
    params: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    """
    Synchronous version for use in sync contexts. Includes retry on transient failures.
    """
    method = (method or "GET").upper()
    if method not in ("GET", "POST"):
        method = "GET"

    validate_safe_url(url)

    with httpx.Client() as client:
        if method == "POST":
            response = client.post(url, json=params, timeout=timeout)
        else:
            response = client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
