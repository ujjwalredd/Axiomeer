"""
Exception classes for the Axiomeer SDK.

All errors carry the server-provided `request_id` (when available) so users can
correlate failures with server logs and traces.
"""
from __future__ import annotations

from typing import Any, Optional


class AxiomeerError(Exception):
    """Base exception for all Axiomeer SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        code: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.code = code
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        suffix = []
        if self.status_code is not None:
            suffix.append(f"status={self.status_code}")
        if self.request_id:
            suffix.append(f"request_id={self.request_id}")
        if self.code:
            suffix.append(f"code={self.code}")
        return f"{base} ({', '.join(suffix)})" if suffix else base


class AuthenticationError(AxiomeerError):
    """401 — invalid or missing credentials."""


class PermissionError(AxiomeerError):
    """403 — authenticated but not allowed."""


class NotFoundError(AxiomeerError):
    """404 — resource missing."""


class ConflictError(AxiomeerError):
    """409 — resource already exists or conflicting state."""


class ValidationError(AxiomeerError):
    """422 — request body failed validation."""


class RateLimitError(AxiomeerError):
    """429 — exceeded quota / rate limit. `retry_after` is seconds when set."""

    def __init__(
        self,
        message: str = "Rate limit exceeded.",
        *,
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(AxiomeerError):
    """5xx — server-side failure. SDKs should backoff + retry idempotent calls."""


class NetworkError(AxiomeerError):
    """Local network/transport failure (DNS, connection refused, TLS)."""


class TimeoutError(AxiomeerError):  # noqa: A001 - intentional shadow
    """Request exceeded the configured timeout."""


class ExecutionError(AxiomeerError):
    """Provider returned an error during /execute. `details` carries the body."""
