"""
Tests for base HTTP client functionality.

Tests the core HTTP client with rate limiting, retries, and error handling.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch

from app.external_apis.base.client import BaseHTTPClient
from app.external_apis.base.exceptions import (
    ExternalAPIError,
    RateLimitExceededError,
    TimeoutError,
    ConnectionError,
    ValidationError,
)
from app.external_apis.base.rate_limiter import RateLimiter
from app.external_apis.base.retry import RetryConfig


class TestBaseHTTPClient:
    """Test base HTTP client functionality."""
    
    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter."""
        mock_limiter = AsyncMock(spec=RateLimiter)
        mock_limiter.wait_if_needed = AsyncMock()
        return mock_limiter
    
    @pytest.fixture
    def retry_config(self):
        """Retry configuration for testing."""
        return RetryConfig(max_attempts=2, base_delay=0.1)
    
    @pytest.fixture
    async def client(self, mock_rate_limiter, retry_config):
        """Create test client."""
        client = BaseHTTPClient(
            base_url="https://api.example.com",
            provider="test_provider",
            rate_limiter=mock_rate_limiter,
            retry_config=retry_config,
            timeout=5.0
        )
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_successful_request(self, client):
        """Test successful HTTP request."""
        with patch.object(client.client, 'request') as mock_request:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_request.return_value = mock_response
            
            result = await client.get("/test")
            
            assert result == {"data": "test"}
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_called(self, client, mock_rate_limiter):
        """Test that rate limiting is called before requests."""
        with patch.object(client.client, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_request.return_value = mock_response
            
            await client.get("/test")
            
            mock_rate_limiter.wait_if_needed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, client):
        """Test HTTP error response handling."""
        with patch.object(client.client, 'request') as mock_request:
            # Mock error response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"error": "Not found"}
            mock_response.text = "Not found"
            mock_request.return_value = mock_response
            
            with pytest.raises(ExternalAPIError) as exc_info:
                await client.get("/test")
            
            assert exc_info.value.status_code == 404
            assert "Not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """Test timeout error handling."""
        with patch.object(client.client, 'request') as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(TimeoutError) as exc_info:
                await client.get("/test")
            
            assert exc_info.value.provider == "test_provider"
    
    @pytest.mark.asyncio
    async def test_connection_error(self, client):
        """Test connection error handling."""
        with patch.object(client.client, 'request') as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(ConnectionError) as exc_info:
                await client.get("/test")
            
            assert exc_info.value.provider == "test_provider"
    
    @pytest.mark.asyncio
    async def test_json_validation_error(self, client):
        """Test JSON validation error handling."""
        with patch.object(client.client, 'request') as mock_request:
            # Mock response with invalid JSON
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.text = "invalid json"
            mock_request.return_value = mock_response
            
            with pytest.raises(ValidationError) as exc_info:
                await client.get("/test")
            
            assert exc_info.value.provider == "test_provider"
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_error(self, client, mock_rate_limiter):
        """Test rate limit exceeded error."""
        mock_rate_limiter.wait_if_needed.side_effect = RateLimitExceededError(
            "Rate limit exceeded",
            provider="test_provider",
            retry_after=60
        )
        
        with pytest.raises(RateLimitExceededError) as exc_info:
            await client.get("/test")
        
        assert exc_info.value.retry_after == 60
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, client):
        """Test retry logic on failures."""
        with patch.object(client.client, 'request') as mock_request:
            # First call fails, second succeeds
            mock_response_fail = Mock()
            mock_response_fail.status_code = 503
            mock_response_fail.json.return_value = {"error": "Service unavailable"}
            mock_response_fail.text = "Service unavailable"
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": "test"}
            
            mock_request.side_effect = [mock_response_fail, mock_response_success]
            
            # Should succeed after retry
            result = await client.get("/test")
            
            assert result == {"data": "test"}
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_correlation_id_added(self, client):
        """Test that correlation ID is added to requests."""
        with patch.object(client.client, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_request.return_value = mock_response
            
            await client.get("/test")
            
            # Check that correlation ID header was added
            call_args = mock_request.call_args
            headers = call_args[1]['headers']
            assert 'X-Correlation-ID' in headers
            assert len(headers['X-Correlation-ID']) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check functionality."""
        with patch.object(client, 'get') as mock_get:
            mock_get.return_value = {"status": "ok"}
            
            result = await client.health_check()
            
            assert result["provider"] == "test_provider"
            assert result["status"] == "healthy"
            assert result["base_url"] == "https://api.example.com"
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure handling."""
        with patch.object(client, 'get') as mock_get:
            mock_get.side_effect = ExternalAPIError("API error", provider="test_provider")
            
            result = await client.health_check()
            
            assert result["provider"] == "test_provider"
            assert result["status"] == "unhealthy"
            assert "API error" in result["error"]