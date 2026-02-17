"""
HTTP executor for provider calls with retry logic and GET/POST support.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


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

    with httpx.Client() as client:
        if method == "POST":
            response = client.post(url, json=params, timeout=timeout)
        else:
            response = client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
