"""
Redis-based rate limiting for external API clients.

Implements sliding window rate limiting with Redis to ensure API quotas
are not exceeded while maximizing throughput.
"""

import asyncio
import time

import redis.asyncio as redis
from structlog import get_logger

from app.core.config import get_settings
from app.external_apis.base.exceptions import RateLimitExceededError

logger = get_logger(__name__)
settings = get_settings()


class RateLimiter:
    """
    Redis-based sliding window rate limiter.
    
    Uses Redis sorted sets to implement a sliding window algorithm
    that tracks request timestamps and enforces rate limits.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        provider: str,
        requests_per_minute: int,
        burst_allowance: int = 0,
        window_size: int = 60,
        key_prefix: str = "rate_limit"
    ):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Redis client instance
            provider: API provider name (e.g., 'alpha_vantage')
            requests_per_minute: Maximum requests per minute
            burst_allowance: Additional requests allowed in burst
            window_size: Time window in seconds (default 60 for per-minute)
            key_prefix: Redis key prefix
        """
        self.redis = redis_client
        self.provider = provider
        self.requests_per_minute = requests_per_minute
        self.burst_allowance = burst_allowance
        self.window_size = window_size
        self.key_prefix = key_prefix
        self.max_requests = requests_per_minute + burst_allowance

        # Redis key for this provider
        self.key = f"{key_prefix}:{provider}"

        logger.info(
            "Rate limiter initialized",
            provider=provider,
            requests_per_minute=requests_per_minute,
            burst_allowance=burst_allowance,
            max_requests=self.max_requests
        )

    async def is_allowed(self, identifier: str = "default") -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier: Additional identifier for rate limiting (e.g., user_id)
            
        Returns:
            True if request is allowed, False otherwise
        """
        key = f"{self.key}:{identifier}"
        current_time = time.time()
        window_start = current_time - self.window_size

        async with self.redis.pipeline() as pipe:
            # Remove expired entries
            await pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            await pipe.zcard(key)

            # Execute pipeline
            results = await pipe.execute()
            request_count = results[1]

            if request_count < self.max_requests:
                # Add current request
                await self.redis.zadd(key, {str(current_time): current_time})
                await self.redis.expire(key, self.window_size * 2)  # Cleanup buffer

                logger.debug(
                    "Request allowed",
                    provider=self.provider,
                    identifier=identifier,
                    current_count=request_count + 1,
                    max_requests=self.max_requests
                )
                return True
            logger.warning(
                "Request denied - rate limit exceeded",
                provider=self.provider,
                identifier=identifier,
                current_count=request_count,
                max_requests=self.max_requests
            )
            return False

    async def wait_if_needed(self, identifier: str = "default") -> None:
        """
        Wait if necessary to respect rate limits.
        
        Args:
            identifier: Additional identifier for rate limiting
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded and wait time is too long
        """
        if await self.is_allowed(identifier):
            return

        # Calculate wait time
        wait_time = await self.get_wait_time(identifier)

        if wait_time > 300:  # Don't wait more than 5 minutes
            raise RateLimitExceededError(
                f"Rate limit exceeded, would need to wait {wait_time:.1f} seconds",
                provider=self.provider,
                retry_after=int(wait_time)
            )

        logger.info(
            "Rate limit reached, waiting",
            provider=self.provider,
            identifier=identifier,
            wait_time=wait_time
        )

        await asyncio.sleep(wait_time)

    async def get_wait_time(self, identifier: str = "default") -> float:
        """
        Get time to wait before next request is allowed.
        
        Args:
            identifier: Additional identifier for rate limiting
            
        Returns:
            Wait time in seconds
        """
        key = f"{self.key}:{identifier}"
        current_time = time.time()
        window_start = current_time - self.window_size

        # Get oldest request in current window
        oldest_requests = await self.redis.zrangebyscore(
            key, window_start, current_time, start=0, num=1, withscores=True
        )

        if not oldest_requests:
            return 0.0

        # Calculate when the oldest request will expire
        oldest_timestamp = oldest_requests[0][1]
        wait_time = max(0.0, oldest_timestamp + self.window_size - current_time)

        return wait_time

    async def get_current_usage(self, identifier: str = "default") -> dict:
        """
        Get current rate limit usage statistics.
        
        Args:
            identifier: Additional identifier for rate limiting
            
        Returns:
            Dictionary with usage statistics
        """
        key = f"{self.key}:{identifier}"
        current_time = time.time()
        window_start = current_time - self.window_size

        # Remove expired entries and count current requests
        async with self.redis.pipeline() as pipe:
            await pipe.zremrangebyscore(key, 0, window_start)
            await pipe.zcard(key)
            results = await pipe.execute()

        current_count = results[1]
        remaining = max(0, self.max_requests - current_count)
        wait_time = await self.get_wait_time(identifier) if remaining == 0 else 0.0

        return {
            "provider": self.provider,
            "identifier": identifier,
            "current_count": current_count,
            "max_requests": self.max_requests,
            "remaining": remaining,
            "reset_time": current_time + wait_time if wait_time > 0 else None,
            "window_size": self.window_size,
        }

    async def reset(self, identifier: str = "default") -> None:
        """
        Reset rate limit for identifier (useful for testing).
        
        Args:
            identifier: Additional identifier for rate limiting
        """
        key = f"{self.key}:{identifier}"
        await self.redis.delete(key)

        logger.info(
            "Rate limit reset",
            provider=self.provider,
            identifier=identifier
        )


class RateLimiterManager:
    """
    Manager for multiple rate limiters.
    
    Creates and manages rate limiters for different API providers
    with their specific rate limit configurations.
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize rate limiter manager.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self._limiters = {}

    def get_limiter(
        self,
        provider: str,
        requests_per_minute: int,
        burst_allowance: int = 0
    ) -> RateLimiter:
        """
        Get or create rate limiter for provider.
        
        Args:
            provider: API provider name
            requests_per_minute: Maximum requests per minute
            burst_allowance: Additional burst requests allowed
            
        Returns:
            RateLimiter instance
        """
        key = f"{provider}:{requests_per_minute}:{burst_allowance}"

        if key not in self._limiters:
            self._limiters[key] = RateLimiter(
                redis_client=self.redis,
                provider=provider,
                requests_per_minute=requests_per_minute,
                burst_allowance=burst_allowance
            )

        return self._limiters[key]

    def get_alpha_vantage_limiter(self) -> RateLimiter:
        """Get rate limiter configured for Alpha Vantage API."""
        return self.get_limiter(
            provider="alpha_vantage",
            requests_per_minute=settings.ALPHA_VANTAGE_RATE_LIMIT_PER_MINUTE,
            burst_allowance=0  # Alpha Vantage is strict about limits
        )

    def get_reddit_limiter(self) -> RateLimiter:
        """Get rate limiter configured for Reddit API."""
        return self.get_limiter(
            provider="reddit",
            requests_per_minute=settings.REDDIT_RATE_LIMIT_PER_MINUTE,
            burst_allowance=5  # Reddit allows some bursting
        )

    def get_gemini_limiter(self) -> RateLimiter:
        """Get rate limiter configured for Google Gemini API."""
        return self.get_limiter(
            provider="gemini",
            requests_per_minute=settings.GEMINI_RATE_LIMIT_PER_MINUTE,
            burst_allowance=100  # Gemini has high limits
        )
