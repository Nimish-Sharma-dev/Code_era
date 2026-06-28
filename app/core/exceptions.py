"""
Domain exception hierarchy for the FinAI platform.

Centralised exceptions allow middleware to translate them to appropriate
HTTP responses without coupling domain logic to FastAPI.
"""

from __future__ import annotations

from typing import Any, Optional


class FinAIBaseError(Exception):
    """Base exception for all platform errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


# ── Authentication & Authorisation ───────────────────────────────────────────


class AuthenticationError(FinAIBaseError):
    """Raised when authentication fails (invalid/expired credentials)."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any) -> None:
        super().__init__(message, code="AUTH_FAILED", status_code=401, **kwargs)


class AuthorizationError(FinAIBaseError):
    """Raised when a user lacks permission for an action."""

    def __init__(self, message: str = "Insufficient permissions", **kwargs: Any) -> None:
        super().__init__(message, code="FORBIDDEN", status_code=403, **kwargs)


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    def __init__(self) -> None:
        super().__init__(message="Token has expired", code="TOKEN_EXPIRED")


# ── Resource Errors ───────────────────────────────────────────────────────────


class NotFoundError(FinAIBaseError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} with identifier '{identifier}' not found",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictError(FinAIBaseError):
    """Raised when a resource creation conflicts with existing data."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, code="CONFLICT", status_code=409, **kwargs)


class ValidationError(FinAIBaseError):
    """Raised when business-logic validation fails (beyond schema validation)."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(message, code="VALIDATION_ERROR", status_code=422, details=details)


# ── Financial Domain Errors ───────────────────────────────────────────────────


class InsufficientFundsError(FinAIBaseError):
    """Raised when a wallet or account has insufficient balance."""

    def __init__(self, available: float, required: float) -> None:
        super().__init__(
            message=f"Insufficient funds. Available: {available}, Required: {required}",
            code="INSUFFICIENT_FUNDS",
            status_code=422,
            details={"available": available, "required": required},
        )


class RiskLimitExceededError(FinAIBaseError):
    """Raised when a proposed transaction exceeds the user's risk profile."""

    def __init__(self, message: str = "Risk limit exceeded") -> None:
        super().__init__(message, code="RISK_LIMIT_EXCEEDED", status_code=422)


class DebtRatioExceededError(FinAIBaseError):
    """Raised when proposed debt would exceed safe debt-to-income ratios."""

    def __init__(self, current_ratio: float, max_ratio: float) -> None:
        super().__init__(
            message=f"Debt-to-income ratio {current_ratio:.1%} exceeds maximum {max_ratio:.1%}",
            code="DEBT_RATIO_EXCEEDED",
            status_code=422,
            details={"current_ratio": current_ratio, "max_ratio": max_ratio},
        )


# ── External Service Errors ───────────────────────────────────────────────────


class MarketDataError(FinAIBaseError):
    """Raised when fetching market data fails."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(
            message=f"Market data error from {source}: {message}",
            code="MARKET_DATA_ERROR",
            status_code=503,
            details={"source": source},
        )


class MLModelError(FinAIBaseError):
    """Raised when ML model inference fails."""

    def __init__(self, model: str, message: str) -> None:
        super().__init__(
            message=f"ML model '{model}' error: {message}",
            code="ML_MODEL_ERROR",
            status_code=503,
            details={"model": model},
        )


class DatabaseError(FinAIBaseError):
    """Raised when a database operation fails unexpectedly."""

    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(message, code="DATABASE_ERROR", status_code=503)


class CacheError(FinAIBaseError):
    """Raised when a Redis cache operation fails."""

    def __init__(self, message: str = "Cache operation failed") -> None:
        super().__init__(message, code="CACHE_ERROR", status_code=503)


class GraphError(FinAIBaseError):
    """Raised when a Neo4j graph operation fails."""

    def __init__(self, message: str = "Graph operation failed") -> None:
        super().__init__(message, code="GRAPH_ERROR", status_code=503)


class RateLimitError(FinAIBaseError):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            message="Rate limit exceeded",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after_seconds": retry_after},
        )
