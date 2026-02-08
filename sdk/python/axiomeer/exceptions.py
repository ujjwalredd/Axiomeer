"""
Exception classes for Axiomeer SDK
"""


class AxiomeerError(Exception):
    """Base exception for all Axiomeer SDK errors"""
    pass


class AuthenticationError(AxiomeerError):
    """Raised when authentication fails (401)"""
    pass


class RateLimitError(AxiomeerError):
    """Raised when rate limit is exceeded (429)"""

    def __init__(self, message="Rate limit exceeded. Please upgrade your tier or wait.", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class NotFoundError(AxiomeerError):
    """Raised when resource is not found (404)"""
    pass


class ExecutionError(AxiomeerError):
    """Raised when tool execution fails"""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details


class ValidationError(AxiomeerError):
    """Raised when request validation fails (422)"""
    pass
