"""
Axiomeer Python SDK

Official Python client for the Axiomeer AI Agent Marketplace.
Discover and execute tools, APIs, RAG systems, and datasets through natural language.
"""

from importlib.metadata import PackageNotFoundError, version

from axiomeer.client import AgentMarketplace
from axiomeer.models import ShopResult, ExecutionResult, AppListing
from axiomeer.exceptions import (
    AxiomeerError,
    AuthenticationError,
    PermissionError,
    RateLimitError,
    NotFoundError,
    ConflictError,
    ValidationError,
    ExecutionError,
    ServerError,
    NetworkError,
    TimeoutError,
)

# Single source of truth for the version is pyproject.toml; read it from the
# installed package metadata rather than duplicating the literal here.
try:
    __version__ = version("axiomeer")
except PackageNotFoundError:  # not installed (e.g. running from a source tree)
    __version__ = "0.0.0.dev0"
__all__ = [
    "AgentMarketplace",
    "ShopResult",
    "ExecutionResult",
    "AppListing",
    "AxiomeerError",
    "AuthenticationError",
    "PermissionError",
    "RateLimitError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "ExecutionError",
    "ServerError",
    "NetworkError",
    "TimeoutError",
    "__version__",
]
