"""
Axiomeer Python SDK

Official Python client for the Axiomeer AI Agent Marketplace.
Discover and execute tools, APIs, RAG systems, and datasets through natural language.
"""

from axiomeer.client import AgentMarketplace
from axiomeer.models import ShopResult, ExecutionResult, AppListing
from axiomeer.exceptions import (
    AxiomeerError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ExecutionError,
)

__version__ = "0.1.2"
__all__ = [
    "AgentMarketplace",
    "ShopResult",
    "ExecutionResult",
    "AppListing",
    "AxiomeerError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ExecutionError",
    "__version__",
]
