"""
Dependency injection providers for external API clients.

Provides factory functions and dependency injection for external API clients
including Alpha Vantage, Reddit, and Google Gemini.
"""

from functools import lru_cache

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.external_apis.alpha_vantage.client import AlphaVantageClient
from app.external_apis.alpha_vantage.service import AlphaVantageService
from app.external_apis.reddit.client import RedditClient
from app.external_apis.reddit.service import RedditService
from app.external_apis.base.rate_limiter import RateLimiterManager
from app.external_apis.base.retry import CircuitBreaker, RetryConfig

settings = get_settings()


# Redis client for rate limiting and caching
@lru_cache
def get_redis_client() -> redis.Redis:
    """Get Redis client for external APIs."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


# Rate limiter manager
@lru_cache
def get_rate_limiter_manager() -> RateLimiterManager:
    """Get rate limiter manager."""
    redis_client = get_redis_client()
    return RateLimiterManager(redis_client)


# Alpha Vantage dependencies
@lru_cache
def get_alpha_vantage_client() -> AlphaVantageClient:
    """
    Get Alpha Vantage client with rate limiting and retry logic.
    
    Returns:
        Configured Alpha Vantage client
    """
    rate_limiter_manager = get_rate_limiter_manager()

    # Get Alpha Vantage specific rate limiter
    rate_limiter = rate_limiter_manager.get_alpha_vantage_limiter()

    # Configure retry logic for Alpha Vantage
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True
    )

    # Configure circuit breaker
    circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=300.0  # 5 minutes
    )

    return AlphaVantageClient(
        api_key=settings.ALPHA_VANTAGE_API_KEY,
        rate_limiter=rate_limiter,
        retry_config=retry_config,
        circuit_breaker=circuit_breaker
    )


def get_alpha_vantage_service(
    db: AsyncSession = Depends(get_db)
) -> AlphaVantageService:
    """
    Get Alpha Vantage service with database and cache dependencies.
    
    Args:
        db: Database session
        
    Returns:
        Configured Alpha Vantage service
    """
    client = get_alpha_vantage_client()
    redis_client = get_redis_client()

    return AlphaVantageService(
        client=client,
        db=db,
        redis_client=redis_client
    )


# Health check dependencies
async def get_external_apis_health() -> dict:
    """
    Get health status of all external APIs.
    
    Returns:
        Health status dictionary
    """
    health_status = {
        "external_apis": {},
        "rate_limiters": {},
        "cache": {}
    }

    # Check Alpha Vantage
    try:
        alpha_vantage_client = get_alpha_vantage_client()
        alpha_vantage_health = await alpha_vantage_client.health_check()
        health_status["external_apis"]["alpha_vantage"] = alpha_vantage_health
    except Exception as e:
        health_status["external_apis"]["alpha_vantage"] = {
            "provider": "alpha_vantage",
            "status": "unhealthy",
            "error": str(e)
        }

    # Check Reddit
    try:
        reddit_client = get_reddit_client()
        reddit_health = await reddit_client.health_check()
        health_status["external_apis"]["reddit"] = reddit_health
    except Exception as e:
        health_status["external_apis"]["reddit"] = {
            "provider": "reddit",
            "status": "unhealthy",
            "error": str(e)
        }

    # Check rate limiters
    try:
        rate_limiter_manager = get_rate_limiter_manager()
        
        # Alpha Vantage rate limiter
        alpha_vantage_limiter = rate_limiter_manager.get_alpha_vantage_limiter()
        av_usage = await alpha_vantage_limiter.get_current_usage()
        health_status["rate_limiters"]["alpha_vantage"] = av_usage
        
        # Reddit rate limiter
        reddit_limiter = rate_limiter_manager.get_reddit_limiter()
        reddit_usage = await reddit_limiter.get_current_usage()
        health_status["rate_limiters"]["reddit"] = reddit_usage
        
    except Exception as e:
        health_status["rate_limiters"]["error"] = str(e)

    # Check Redis cache
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        health_status["cache"]["redis"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        health_status["cache"]["redis"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }

    return health_status


# Future providers for other APIs
# These will be implemented in subsequent phases

@lru_cache
def get_reddit_client() -> RedditClient:
    """
    Get Reddit client with rate limiting.
    
    Returns:
        Configured Reddit client
    """
    rate_limiter_manager = get_rate_limiter_manager()
    
    # Get Reddit specific rate limiter
    rate_limiter = rate_limiter_manager.get_reddit_limiter()
    
    return RedditClient(rate_limiter=rate_limiter)


def get_reddit_service(
    db: AsyncSession = Depends(get_db)
) -> RedditService:
    """
    Get Reddit service with database dependencies.
    
    Args:
        db: Database session
        
    Returns:
        Configured Reddit service
    """
    return RedditService(db_session=db)


def get_gemini_client():
    """Get Google Gemini API client (placeholder for P3.3)."""
    raise NotImplementedError("Gemini client will be implemented in P3.3")


# Cleanup functions for testing
async def cleanup_external_api_resources():
    """Clean up external API resources (for testing)."""
    try:
        # Close Alpha Vantage client
        alpha_vantage_client = get_alpha_vantage_client()
        await alpha_vantage_client.close()

        # Close Reddit client
        reddit_client = get_reddit_client()
        await reddit_client.close()

        # Close Redis connections
        redis_client = get_redis_client()
        await redis_client.close()

    except Exception:
        # Log but don't raise in cleanup
        pass
