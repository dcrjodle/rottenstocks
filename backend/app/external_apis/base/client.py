"""
Base HTTP client for external API integrations.

Provides a standardized async HTTP client with rate limiting, retries,
circuit breaking, and comprehensive error handling.
"""

import json
import uuid
from typing import Any

import httpx
from structlog import get_logger

from app.core.config import get_settings
from app.external_apis.base.exceptions import (
    ConnectionError,
    NetworkError,
    TimeoutError,
    ValidationError,
    get_exception_for_status_code,
)
from app.external_apis.base.rate_limiter import RateLimiter
from app.external_apis.base.retry import (
    CircuitBreaker,
    RetryConfig,
    retry_with_backoff,
)

logger = get_logger(__name__)
settings = get_settings()


class BaseHTTPClient:
    """
    Base HTTP client for external APIs.
    
    Provides standardized functionality including:
    - Rate limiting with Redis
    - Automatic retries with exponential backoff
    - Circuit breaker pattern
    - Request/response logging
    - Error handling and mapping
    """

    def __init__(
        self,
        base_url: str,
        provider: str,
        rate_limiter: RateLimiter | None = None,
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None
    ):
        """
        Initialize HTTP client.
        
        Args:
            base_url: Base URL for API
            provider: Provider name for logging and error handling
            rate_limiter: Rate limiter instance
            retry_config: Retry configuration
            circuit_breaker: Circuit breaker instance
            timeout: Request timeout in seconds
            headers: Default headers to include with requests
        """
        self.base_url = base_url.rstrip('/')
        self.provider = provider
        self.rate_limiter = rate_limiter
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = circuit_breaker

        # Default headers
        default_headers = {
            "User-Agent": f"RottenStocks/{settings.VERSION}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            default_headers.update(headers)

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=default_headers,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
        )

        logger.info(
            "HTTP client initialized",
            provider=self.provider,
            base_url=self.base_url,
            timeout=timeout
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    def _generate_correlation_id(self) -> str:
        """Generate correlation ID for request tracking."""
        return str(uuid.uuid4())

    async def _make_request(
        self,
        method: str,
        url: str,
        correlation_id: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with error handling.
        
        Args:
            method: HTTP method
            url: Request URL
            correlation_id: Correlation ID for tracking
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            ExternalAPIError: On various error conditions
        """
        # Add correlation ID to headers
        headers = kwargs.get('headers', {})
        headers['X-Correlation-ID'] = correlation_id
        kwargs['headers'] = headers

        try:
            logger.debug(
                "Making HTTP request",
                provider=self.provider,
                method=method,
                url=url,
                correlation_id=correlation_id
            )

            response = await self.client.request(method, url, **kwargs)

            logger.debug(
                "HTTP response received",
                provider=self.provider,
                method=method,
                url=url,
                status_code=response.status_code,
                correlation_id=correlation_id
            )

            # Handle HTTP errors
            if response.status_code >= 400:
                await self._handle_http_error(response, correlation_id)

            return response

        except httpx.TimeoutException as e:
            logger.error(
                "Request timeout",
                provider=self.provider,
                method=method,
                url=url,
                correlation_id=correlation_id,
                error=str(e)
            )
            raise TimeoutError(
                f"Request timeout after {self.client.timeout} seconds",
                provider=self.provider,
                correlation_id=correlation_id
            )

        except httpx.ConnectError as e:
            logger.error(
                "Connection error",
                provider=self.provider,
                method=method,
                url=url,
                correlation_id=correlation_id,
                error=str(e)
            )
            raise ConnectionError(
                f"Failed to connect to {self.provider}",
                provider=self.provider,
                correlation_id=correlation_id
            )

        except httpx.RequestError as e:
            logger.error(
                "Network error",
                provider=self.provider,
                method=method,
                url=url,
                correlation_id=correlation_id,
                error=str(e)
            )
            raise NetworkError(
                f"Network error: {e!s}",
                provider=self.provider,
                correlation_id=correlation_id
            )

    async def _handle_http_error(self, response: httpx.Response, correlation_id: str):
        """
        Handle HTTP error responses.
        
        Args:
            response: HTTP response with error status
            correlation_id: Correlation ID for tracking
            
        Raises:
            ExternalAPIError: Appropriate exception for status code
        """
        try:
            error_data = response.json()
        except (json.JSONDecodeError, ValueError):
            error_data = {"message": response.text}

        # Extract error message
        error_message = (
            error_data.get('message') or
            error_data.get('error') or
            error_data.get('detail') or
            f"HTTP {response.status_code} error"
        )

        logger.error(
            "HTTP error response",
            provider=self.provider,
            status_code=response.status_code,
            error_message=error_message,
            correlation_id=correlation_id,
            response_data=error_data
        )

        # Create appropriate exception
        exception = get_exception_for_status_code(
            status_code=response.status_code,
            message=error_message,
            provider=self.provider,
            response_data=error_data,
            correlation_id=correlation_id
        )

        raise exception

    async def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | str | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Make HTTP request with rate limiting and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Endpoint URL (relative to base_url)
            params: Query parameters
            data: Form data
            json_data: JSON data
            headers: Additional headers
            **kwargs: Additional request parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            ExternalAPIError: On various error conditions
        """
        correlation_id = self._generate_correlation_id()

        # Build request kwargs
        request_kwargs = kwargs.copy()
        if params:
            request_kwargs['params'] = params
        if data:
            request_kwargs['data'] = data
        if json_data:
            request_kwargs['json'] = json_data
        if headers:
            request_kwargs['headers'] = {**(request_kwargs.get('headers', {})), **headers}

        # Rate limiting
        if self.rate_limiter:
            try:
                await self.rate_limiter.wait_if_needed()
            except Exception as e:
                logger.error(
                    "Rate limiting error",
                    provider=self.provider,
                    correlation_id=correlation_id,
                    error=str(e)
                )
                raise

        # Make request with retries
        async def _request():
            return await self._make_request(
                method=method,
                url=url,
                correlation_id=correlation_id,
                **request_kwargs
            )

        response = await retry_with_backoff(
            _request,
            retry_config=self.retry_config,
            circuit_breaker=self.circuit_breaker,
            correlation_id=correlation_id
        )

        # Parse JSON response
        try:
            response_data = response.json()

            logger.debug(
                "Request completed successfully",
                provider=self.provider,
                method=method,
                url=url,
                status_code=response.status_code,
                correlation_id=correlation_id
            )

            return response_data

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Failed to parse JSON response",
                provider=self.provider,
                method=method,
                url=url,
                correlation_id=correlation_id,
                response_text=response.text[:500],
                error=str(e)
            )
            raise ValidationError(
                f"Invalid JSON response from {self.provider}",
                provider=self.provider,
                correlation_id=correlation_id
            )

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", url, params=params, **kwargs)

    async def post(
        self,
        url: str,
        data: dict[str, Any] | str | None = None,
        json_data: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Make POST request."""
        return await self.request("POST", url, data=data, json_data=json_data, **kwargs)

    async def put(
        self,
        url: str,
        data: dict[str, Any] | str | None = None,
        json_data: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Make PUT request."""
        return await self.request("PUT", url, data=data, json_data=json_data, **kwargs)

    async def delete(
        self,
        url: str,
        **kwargs
    ) -> dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on the API.
        
        Returns:
            Health check results
        """
        try:
            # Most APIs have a simple endpoint we can hit
            response = await self.get("/")
            return {
                "provider": self.provider,
                "status": "healthy",
                "response_time": response.get("response_time"),
                "base_url": self.base_url
            }
        except Exception as e:
            return {
                "provider": self.provider,
                "status": "unhealthy",
                "error": str(e),
                "base_url": self.base_url
            }
