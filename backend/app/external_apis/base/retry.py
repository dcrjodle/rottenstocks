"""
Retry logic with exponential backoff for external API clients.

Provides configurable retry mechanisms for handling transient failures,
network issues, and rate limiting with intelligent backoff strategies.
"""

import asyncio
import random
from collections.abc import Callable
from typing import Any

from structlog import get_logger

from app.external_apis.base.exceptions import (
    CircuitBreakerOpenError,
    ExternalAPIError,
    NetworkError,
    RateLimitExceededError,
    ServiceUnavailableError,
    TimeoutError,
)

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: tuple = (
            NetworkError,
            TimeoutError,
            ServiceUnavailableError,
            RateLimitExceededError,
        ),
        stop_on: tuple = (
            CircuitBreakerOpenError,
        )
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retry_on: Exception types that should trigger retries
            stop_on: Exception types that should stop retries immediately
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on
        self.stop_on = stop_on

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Add jitter to avoid thundering herd
        if self.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0.0, delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if we should retry after an exception.
        
        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if we've exceeded max attempts
        if attempt >= self.max_attempts:
            return False

        # Don't retry on stop exceptions
        if isinstance(exception, self.stop_on):
            return False

        # Retry on specified exception types
        if isinstance(exception, self.retry_on):
            return True

        return False


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by temporarily stopping requests
    to a failing service and allowing it time to recover.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = ExternalAPIError
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open

    def should_allow_request(self) -> bool:
        """Check if request should be allowed through circuit breaker."""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if enough time has passed to try recovery
            if (self.last_failure_time and
                asyncio.get_event_loop().time() - self.last_failure_time >= self.recovery_timeout):
                self.state = "half-open"
                logger.info("Circuit breaker moving to half-open state")
                return True
            return False

        if self.state == "half-open":
            return True

        return False

    def record_success(self) -> None:
        """Record successful request."""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful recovery")
        elif self.state == "closed":
            # Reset failure count on success
            self.failure_count = 0

    def record_failure(self, exception: Exception) -> None:
        """Record failed request."""
        if isinstance(exception, self.expected_exception):
            self.failure_count += 1
            self.last_failure_time = asyncio.get_event_loop().time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    "Circuit breaker opened due to failures",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                )


async def retry_with_backoff(
    func: Callable,
    *args,
    retry_config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    correlation_id: str | None = None,
    **kwargs
) -> Any:
    """
    Execute function with retry logic and exponential backoff.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for function
        retry_config: Retry configuration
        circuit_breaker: Circuit breaker instance
        correlation_id: Correlation ID for logging
        **kwargs: Keyword arguments for function
        
    Returns:
        Function result
        
    Raises:
        Exception: Last exception if all retries fail
    """
    if retry_config is None:
        retry_config = RetryConfig()

    last_exception = None

    for attempt in range(retry_config.max_attempts + 1):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.should_allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is open after {circuit_breaker.failure_count} failures"
            )

        try:
            logger.debug(
                "Attempting API call",
                attempt=attempt + 1,
                max_attempts=retry_config.max_attempts + 1,
                correlation_id=correlation_id
            )

            result = await func(*args, **kwargs)

            # Record success
            if circuit_breaker:
                circuit_breaker.record_success()

            if attempt > 0:
                logger.info(
                    "API call succeeded after retries",
                    attempt=attempt + 1,
                    correlation_id=correlation_id
                )

            return result

        except Exception as e:
            last_exception = e

            # Record failure
            if circuit_breaker:
                circuit_breaker.record_failure(e)

            # Check if we should retry
            if not retry_config.should_retry(e, attempt):
                logger.error(
                    "API call failed, not retrying",
                    attempt=attempt + 1,
                    exception=str(e),
                    exception_type=type(e).__name__,
                    correlation_id=correlation_id
                )
                raise e

            # Calculate delay for next attempt
            if attempt < retry_config.max_attempts:
                delay = retry_config.calculate_delay(attempt)

                # Special handling for rate limit exceptions
                if isinstance(e, RateLimitExceededError) and hasattr(e, 'retry_after'):
                    delay = max(delay, e.retry_after)

                logger.warning(
                    "API call failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=retry_config.max_attempts + 1,
                    delay=delay,
                    exception=str(e),
                    exception_type=type(e).__name__,
                    correlation_id=correlation_id
                )

                await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        "All retry attempts exhausted",
        max_attempts=retry_config.max_attempts + 1,
        final_exception=str(last_exception),
        correlation_id=correlation_id
    )

    if last_exception:
        raise last_exception
    raise ExternalAPIError("All retry attempts failed with no exception recorded")


# Pre-configured retry configs for different scenarios
CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=30.0
)

AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=60.0
)

RATE_LIMIT_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=5.0,
    max_delay=300.0,
    retry_on=(RateLimitExceededError, ServiceUnavailableError)
)
