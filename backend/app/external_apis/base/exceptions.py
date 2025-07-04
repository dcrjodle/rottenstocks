"""
Exception classes for external API integrations.

Provides a hierarchy of custom exceptions for handling various types of
API errors, rate limiting, and network issues.
"""

from typing import Any


class ExternalAPIError(Exception):
    """Base exception for all external API errors."""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.response_data = response_data or {}
        self.correlation_id = correlation_id

    def __str__(self) -> str:
        parts = [f"{self.provider}: {self.message}"]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.correlation_id:
            parts.append(f"[{self.correlation_id}]")
        return " ".join(parts)


class RateLimitExceededError(ExternalAPIError):
    """Raised when API rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: str = "unknown",
        retry_after: int | None = None,
        quota_reset: int | None = None,
        **kwargs
    ):
        super().__init__(message, provider, status_code=429, **kwargs)
        self.retry_after = retry_after
        self.quota_reset = quota_reset


class AuthenticationError(ExternalAPIError):
    """Raised when API authentication fails."""

    def __init__(self, message: str = "Authentication failed", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, status_code=401, **kwargs)


class AuthorizationError(ExternalAPIError):
    """Raised when API authorization fails."""

    def __init__(self, message: str = "Authorization failed", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, status_code=403, **kwargs)


class QuotaExhaustedError(ExternalAPIError):
    """Raised when API quota is exhausted."""

    def __init__(
        self,
        message: str = "API quota exhausted",
        provider: str = "unknown",
        quota_reset: int | None = None,
        **kwargs
    ):
        super().__init__(message, provider, status_code=429, **kwargs)
        self.quota_reset = quota_reset


class NetworkError(ExternalAPIError):
    """Raised when network-related errors occur."""

    def __init__(self, message: str = "Network error", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, **kwargs)


class TimeoutError(NetworkError):
    """Raised when API requests timeout."""

    def __init__(self, message: str = "Request timeout", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, **kwargs)


class ConnectionError(NetworkError):
    """Raised when connection to API fails."""

    def __init__(self, message: str = "Connection failed", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, **kwargs)


class ValidationError(ExternalAPIError):
    """Raised when API response validation fails."""

    def __init__(self, message: str = "Response validation failed", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, **kwargs)


class ServiceUnavailableError(ExternalAPIError):
    """Raised when API service is unavailable."""

    def __init__(self, message: str = "Service unavailable", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, status_code=503, **kwargs)


class BadRequestError(ExternalAPIError):
    """Raised when API request is malformed."""

    def __init__(self, message: str = "Bad request", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, status_code=400, **kwargs)


class NotFoundError(ExternalAPIError):
    """Raised when requested resource is not found."""

    def __init__(self, message: str = "Resource not found", provider: str = "unknown", **kwargs):
        super().__init__(message, provider, status_code=404, **kwargs)


class CircuitBreakerOpenError(ExternalAPIError):
    """Raised when circuit breaker is in open state."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        provider: str = "unknown",
        failure_count: int = 0,
        **kwargs
    ):
        super().__init__(message, provider, **kwargs)
        self.failure_count = failure_count


# Exception mapping for HTTP status codes
STATUS_CODE_EXCEPTIONS = {
    400: BadRequestError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    429: RateLimitExceededError,
    503: ServiceUnavailableError,
}


def get_exception_for_status_code(
    status_code: int,
    message: str = "API error",
    provider: str = "unknown",
    **kwargs
) -> ExternalAPIError:
    """Get appropriate exception class for HTTP status code."""
    exception_class = STATUS_CODE_EXCEPTIONS.get(status_code, ExternalAPIError)

    # Only pass status_code if it's the base ExternalAPIError class
    # Other classes have predefined status codes
    if exception_class == ExternalAPIError:
        return exception_class(message, provider, status_code=status_code, **kwargs)
    return exception_class(message, provider, **kwargs)
