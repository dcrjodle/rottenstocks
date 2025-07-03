"""
Tests for health check endpoints.

Tests basic and detailed health checks with various scenarios.
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestBasicHealthEndpoint:
    """Test the basic health endpoint."""
    
    def test_health_endpoint_success(self, client: TestClient):
        """Test successful health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert data["status"] == "healthy"
        assert data["service"] == "RottenStocks API"
        assert data["version"] == "1.0.0"
        assert data["environment"] == "development"  # From test settings
        assert isinstance(data["timestamp"], (int, float))
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] >= 0
    
    def test_health_endpoint_headers(self, client: TestClient):
        """Test health endpoint response headers."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Should have correlation ID and timing headers
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
        
        # Correlation ID should not be empty
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) > 0
        assert correlation_id != "unknown"
        
        # Process time should be a valid number
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
    
    @pytest.mark.asyncio
    async def test_health_endpoint_async(self, async_client: AsyncClient):
        """Test health endpoint with async client."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "RottenStocks API"
    
    def test_health_endpoint_multiple_requests(self, client: TestClient):
        """Test multiple health check requests."""
        responses = []
        
        for _ in range(5):
            response = client.get("/health")
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        
        # Each should have unique correlation IDs
        correlation_ids = [
            resp.headers.get("X-Correlation-ID") 
            for resp in responses
        ]
        assert len(set(correlation_ids)) == 5  # All unique


class TestDetailedHealthEndpoint:
    """Test the detailed health endpoint."""
    
    def test_detailed_health_endpoint_success(self, client: TestClient):
        """Test successful detailed health check."""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check basic fields (same as basic health)
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["service"] == "RottenStocks API"
        assert data["version"] == "1.0.0"
        assert data["environment"] == "development"
        assert isinstance(data["timestamp"], (int, float))
        assert isinstance(data["uptime"], (int, float))
        
        # Check detailed fields
        assert "checks" in data
        assert "configuration" in data
        assert "correlation_id" in data
        
        # Correlation ID should match header
        assert data["correlation_id"] == response.headers["X-Correlation-ID"]
    
    def test_detailed_health_checks_structure(self, client: TestClient):
        """Test the structure of health checks."""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        checks = data["checks"]
        assert isinstance(checks, dict)
        
        # Should have these check categories
        expected_checks = ["database", "redis", "external_apis"]
        for check_name in expected_checks:
            assert check_name in checks
            
            check_result = checks[check_name]
            assert isinstance(check_result, dict)
            assert "healthy" in check_result
            assert "message" in check_result
            assert isinstance(check_result["healthy"], bool)
            assert isinstance(check_result["message"], str)
    
    def test_detailed_health_configuration_structure(self, client: TestClient):
        """Test the structure of configuration info."""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        config = data["configuration"]
        assert isinstance(config, dict)
        
        # Should have these configuration sections
        expected_sections = [
            "environment", "debug", "database_configured", 
            "redis_configured", "external_apis", "security", "features"
        ]
        
        for section in expected_sections:
            assert section in config
    
    def test_detailed_health_external_apis_config(self, client: TestClient):
        """Test external APIs configuration in health check."""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        external_apis = data["configuration"]["external_apis"]
        assert isinstance(external_apis, dict)
        
        # Should check these APIs
        expected_apis = ["reddit", "alpha_vantage", "gemini"]
        for api_name in expected_apis:
            assert api_name in external_apis
            assert isinstance(external_apis[api_name], bool)
    
    @pytest.mark.asyncio
    async def test_detailed_health_endpoint_async(self, async_client: AsyncClient):
        """Test detailed health endpoint with async client."""
        response = await async_client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "checks" in data
        assert "configuration" in data
        assert data["service"] == "RottenStocks API"


class TestHealthEndpointErrorScenarios:
    """Test health endpoints under error conditions."""
    
    @patch('app.api.v1.endpoints.health._check_database')
    async def test_detailed_health_with_database_failure(self, mock_db_check, client: TestClient):
        """Test detailed health when database check fails."""
        # Mock database check to return unhealthy
        mock_db_check.return_value = {
            "healthy": False,
            "message": "Database connection failed",
            "response_time_ms": 0,
        }
        
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Overall status should be unhealthy due to database failure
        assert data["status"] == "unhealthy"
        
        # Database check should show as unhealthy
        assert data["checks"]["database"]["healthy"] is False
        assert "failed" in data["checks"]["database"]["message"].lower()
    
    @patch('app.api.v1.endpoints.health._check_redis')
    async def test_detailed_health_with_redis_failure(self, mock_redis_check, client: TestClient):
        """Test detailed health when Redis check fails."""
        # Mock Redis check to return unhealthy
        mock_redis_check.return_value = {
            "healthy": False,
            "message": "Redis connection failed",
            "response_time_ms": 0,
        }
        
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Overall status should be unhealthy due to Redis failure
        assert data["status"] == "unhealthy"
        
        # Redis check should show as unhealthy
        assert data["checks"]["redis"]["healthy"] is False
        assert "failed" in data["checks"]["redis"]["message"].lower()
    
    @patch('app.api.v1.endpoints.health._check_external_apis')
    async def test_detailed_health_with_external_api_failure(self, mock_api_check, client: TestClient):
        """Test detailed health when external API checks fail."""
        # Mock external API check to return unhealthy
        mock_api_check.return_value = {
            "healthy": False,
            "message": "External API check failed",
            "apis": {},
        }
        
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Overall status should be unhealthy due to external API failure
        assert data["status"] == "unhealthy"
        
        # External APIs check should show as unhealthy
        assert data["checks"]["external_apis"]["healthy"] is False
        assert "failed" in data["checks"]["external_apis"]["message"].lower()


class TestHealthEndpointPerformance:
    """Test health endpoint performance characteristics."""
    
    def test_health_endpoint_response_time(self, client: TestClient):
        """Test that health endpoint responds quickly."""
        import time
        
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond in less than 1 second
        
        # Check the X-Process-Time header
        process_time = float(response.headers["X-Process-Time"])
        assert process_time < 1.0  # Should process in less than 1 second
    
    def test_detailed_health_endpoint_response_time(self, client: TestClient):
        """Test that detailed health endpoint responds reasonably quickly."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/health/detailed")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0  # Should respond in less than 5 seconds
        
        # Check the X-Process-Time header
        process_time = float(response.headers["X-Process-Time"])
        assert process_time < 5.0  # Should process in less than 5 seconds


class TestHealthEndpointCaching:
    """Test health endpoint caching behavior."""
    
    def test_health_endpoint_no_cache_headers(self, client: TestClient):
        """Test that health endpoints don't set cache headers."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Health endpoints should not be cached
        cache_control = response.headers.get("Cache-Control")
        if cache_control:
            assert "no-cache" in cache_control.lower() or "no-store" in cache_control.lower()
    
    def test_health_endpoint_fresh_data(self, client: TestClient):
        """Test that health endpoints return fresh data on each request."""
        # Make two requests
        response1 = client.get("/health")
        response2 = client.get("/health")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Timestamps should be different (or very close)
        assert data1["timestamp"] <= data2["timestamp"]
        
        # Correlation IDs should be different
        assert response1.headers["X-Correlation-ID"] != response2.headers["X-Correlation-ID"]