"""
Tests for Redis-based rate limiter.

Tests the rate limiting functionality with Redis backend.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
import time
import redis.asyncio as redis

from app.external_apis.base.rate_limiter import RateLimiter, RateLimiterManager
from app.external_apis.base.exceptions import RateLimitExceededError


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for testing."""
        client = redis.from_url("redis://localhost:6379/15", decode_responses=True)
        
        # Clean up any existing test data
        await client.flushdb()
        
        yield client
        
        # Clean up after test
        await client.flushdb()
        await client.aclose()
    
    @pytest.fixture
    def rate_limiter(self, redis_client):
        """Create rate limiter for testing."""
        return RateLimiter(
            redis_client=redis_client,
            provider="test_provider",
            requests_per_minute=10,
            burst_allowance=2,
            window_size=60
        )
    
    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(self, rate_limiter):
        """Test that requests are allowed under the rate limit."""
        # First request should be allowed
        result = await rate_limiter.is_allowed("test_user")
        assert result is True
        
        # Multiple requests under limit should be allowed
        for i in range(5):
            result = await rate_limiter.is_allowed("test_user")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_is_allowed_over_limit(self, rate_limiter):
        """Test that requests are denied over the rate limit."""
        # Make max_requests (12) requests to hit the limit
        for i in range(12):
            result = await rate_limiter.is_allowed("test_user")
            assert result is True
        
        # The next request should be denied
        result = await rate_limiter.is_allowed("test_user")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_wait_if_needed_under_limit(self, rate_limiter):
        """Test wait_if_needed when under limit."""
        # Should not wait and should succeed
        await rate_limiter.wait_if_needed("test_user")
        
        # Should be able to make additional requests without waiting
        for i in range(5):
            await rate_limiter.wait_if_needed("test_user")
    
    @pytest.mark.asyncio
    async def test_wait_if_needed_over_limit_short_wait(self, rate_limiter):
        """Test wait_if_needed when over limit with short wait."""
        # Fill up the rate limit
        for i in range(12):
            await rate_limiter.wait_if_needed("test_user")
        
        # Mock get_wait_time to return short wait and test waiting
        with patch.object(rate_limiter, 'get_wait_time', return_value=0.1):
            with patch('asyncio.sleep') as mock_sleep:
                await rate_limiter.wait_if_needed("test_user")
                mock_sleep.assert_called_once_with(0.1)
    
    @pytest.mark.asyncio
    async def test_wait_if_needed_over_limit_long_wait(self, rate_limiter):
        """Test wait_if_needed when wait time is too long."""
        # Fill up the rate limit
        for i in range(12):
            await rate_limiter.wait_if_needed("test_user")
        
        # Mock get_wait_time to return long wait
        with patch.object(rate_limiter, 'get_wait_time', return_value=400):  # > 5 minutes
            with pytest.raises(RateLimitExceededError) as exc_info:
                await rate_limiter.wait_if_needed("test_user")
            
            assert exc_info.value.retry_after == 400
    
    @pytest.mark.asyncio
    async def test_get_wait_time_no_requests(self, rate_limiter):
        """Test get_wait_time when no requests in window."""
        wait_time = await rate_limiter.get_wait_time("test_user")
        assert wait_time == 0.0
    
    @pytest.mark.asyncio
    async def test_get_wait_time_with_requests(self, rate_limiter):
        """Test get_wait_time with requests in window."""
        # Fill up the rate limit
        for i in range(12):
            await rate_limiter.is_allowed("test_user")
        
        # Get wait time - should be positive since we're at limit
        wait_time = await rate_limiter.get_wait_time("test_user")
        assert wait_time > 0.0
    
    @pytest.mark.asyncio
    async def test_get_current_usage(self, rate_limiter):
        """Test getting current usage statistics."""
        # Make some requests
        for i in range(8):
            await rate_limiter.is_allowed("test_user")
        
        usage = await rate_limiter.get_current_usage("test_user")
        
        assert usage["provider"] == "test_provider"
        assert usage["current_count"] == 8
        assert usage["max_requests"] == 12  # 10 + 2 burst
        assert usage["remaining"] == 4
    
    @pytest.mark.asyncio
    async def test_reset(self, rate_limiter):
        """Test resetting rate limit for identifier."""
        # Make some requests
        for i in range(8):
            await rate_limiter.is_allowed("test_user")
        
        # Verify we have usage
        usage = await rate_limiter.get_current_usage("test_user")
        assert usage["current_count"] == 8
        
        # Reset and verify usage is cleared
        await rate_limiter.reset("test_user")
        usage = await rate_limiter.get_current_usage("test_user")
        assert usage["current_count"] == 0


class TestRateLimiterManager:
    """Test rate limiter manager."""
    
    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for testing."""
        client = redis.from_url("redis://localhost:6379/15", decode_responses=True)
        await client.flushdb()
        yield client
        await client.flushdb()
        await client.aclose()
    
    @pytest.fixture
    def manager(self, redis_client):
        """Create rate limiter manager."""
        return RateLimiterManager(redis_client)
    
    def test_get_limiter_creates_new(self, manager):
        """Test that get_limiter creates new rate limiter."""
        limiter = manager.get_limiter("test_provider", 100, 10)
        
        assert limiter.provider == "test_provider"
        assert limiter.requests_per_minute == 100
        assert limiter.burst_allowance == 10
    
    def test_get_limiter_returns_cached(self, manager):
        """Test that get_limiter returns cached instance."""
        limiter1 = manager.get_limiter("test_provider", 100, 10)
        limiter2 = manager.get_limiter("test_provider", 100, 10)
        
        assert limiter1 is limiter2
    
    def test_get_alpha_vantage_limiter(self, manager):
        """Test Alpha Vantage specific limiter."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_RATE_LIMIT_PER_MINUTE = 5
            
            limiter = manager.get_alpha_vantage_limiter()
            
            assert limiter.provider == "alpha_vantage"
            assert limiter.requests_per_minute == 5
            assert limiter.burst_allowance == 0  # Alpha Vantage is strict
    
    def test_get_reddit_limiter(self, manager):
        """Test Reddit specific limiter."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.REDDIT_RATE_LIMIT_PER_MINUTE = 55
            
            limiter = manager.get_reddit_limiter()
            
            assert limiter.provider == "reddit"
            assert limiter.requests_per_minute == 55
            assert limiter.burst_allowance == 5  # Reddit allows some bursting
    
    def test_get_gemini_limiter(self, manager):
        """Test Gemini specific limiter."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_RATE_LIMIT_PER_MINUTE = 1000
            
            limiter = manager.get_gemini_limiter()
            
            assert limiter.provider == "gemini"
            assert limiter.requests_per_minute == 1000
            assert limiter.burst_allowance == 100  # Gemini has high limits