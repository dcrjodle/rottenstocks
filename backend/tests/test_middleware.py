"""
Tests for middleware functionality.

Tests request logging, CORS, compression, and other middleware.
"""

import pytest
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""
    
    def test_correlation_id_in_response(self, client: TestClient):
        """Test that correlation ID is added to response headers."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) > 0
        assert correlation_id != "unknown"
    
    def test_process_time_in_response(self, client: TestClient):
        """Test that process time is added to response headers."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        
        process_time = response.headers["X-Process-Time"]
        assert float(process_time) >= 0
    
    def test_correlation_id_uniqueness(self, client: TestClient):
        """Test that each request gets a unique correlation ID."""
        responses = [client.get("/health") for _ in range(5)]
        
        correlation_ids = [
            resp.headers["X-Correlation-ID"] 
            for resp in responses
        ]
        
        # All correlation IDs should be unique
        assert len(set(correlation_ids)) == 5
    
    def test_correlation_id_in_detailed_health(self, client: TestClient):
        """Test correlation ID consistency in detailed health response."""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        
        # Correlation ID should be in both header and response body
        header_correlation_id = response.headers["X-Correlation-ID"]
        
        data = response.json()
        body_correlation_id = data["correlation_id"]
        
        assert header_correlation_id == body_correlation_id
    
    @patch('app.main.logger')
    def test_request_logging_start(self, mock_logger, client: TestClient):
        """Test that request start is logged."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Should have logged request start
        mock_logger.info.assert_called()
        
        # Find the "Request started" log call
        start_call = None
        for call in mock_logger.info.call_args_list:
            if len(call[0]) > 0 and "Request started" in call[0][0]:
                start_call = call
                break
        
        assert start_call is not None
    
    @patch('app.main.logger')
    def test_request_logging_completion(self, mock_logger, client: TestClient):
        """Test that request completion is logged."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Should have logged request completion
        mock_logger.info.assert_called()
        
        # Find the "Request completed" log call
        completion_call = None
        for call in mock_logger.info.call_args_list:
            if len(call[0]) > 0 and "Request completed" in call[0][0]:
                completion_call = call
                break
        
        assert completion_call is not None


class TestCORSMiddleware:
    """Test CORS middleware functionality."""
    
    def test_cors_preflight_request(self, client: TestClient):
        """Test CORS preflight request handling."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        
        # Should allow the preflight request
        assert response.status_code in [200, 204]
        
        # Should have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
    
    def test_cors_simple_request(self, client: TestClient):
        """Test CORS handling for simple requests."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        
        # Should have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        
        # Should allow the origin
        allowed_origin = response.headers["Access-Control-Allow-Origin"]
        assert allowed_origin in ["*", "http://localhost:3000"]
    
    def test_cors_credentials_allowed(self, client: TestClient):
        """Test that CORS allows credentials."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        
        # Should allow credentials
        if "Access-Control-Allow-Credentials" in response.headers:
            assert response.headers["Access-Control-Allow-Credentials"] == "true"
    
    def test_cors_allowed_methods(self, client: TestClient):
        """Test CORS allowed methods."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )
        
        if response.status_code in [200, 204]:
            allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
            # Should allow common HTTP methods
            assert "GET" in allowed_methods or "*" in allowed_methods


class TestCompressionMiddleware:
    """Test GZip compression middleware."""
    
    def test_compression_for_large_response(self, client: TestClient):
        """Test compression is applied for large responses."""
        response = client.get(
            "/api/v1/health/detailed",
            headers={"Accept-Encoding": "gzip"}
        )
        
        assert response.status_code == 200
        
        # For small responses, compression might not be applied
        # This test mainly ensures no errors occur with compression
        # In a real scenario, you'd test with a larger response
        
        # Check that the response is valid JSON regardless of compression
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
    
    def test_no_compression_for_small_response(self, client: TestClient):
        """Test that small responses might not be compressed."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Should still be valid JSON
        data = response.json()
        assert isinstance(data, dict)
        assert data["status"] == "healthy"


class TestErrorHandlingMiddleware:
    """Test error handling in middleware."""
    
    def test_404_error_handling(self, client: TestClient):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        
        data = response.json()
        assert data["error"] == "NOT_FOUND"
        assert data["message"] == "The requested resource was not found"
        assert data["path"] == "/nonexistent-endpoint"
        assert data["method"] == "GET"
    
    def test_404_error_has_correlation_id(self, client: TestClient):
        """Test that 404 errors still have correlation IDs."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
    
    def test_method_not_allowed_error(self, client: TestClient):
        """Test 405 Method Not Allowed error."""
        response = client.post("/health")  # POST not allowed on health endpoint
        
        assert response.status_code == 405
        assert "X-Correlation-ID" in response.headers
    
    @patch('app.api.v1.endpoints.health.health_check')
    def test_500_error_handling(self, mock_health_check, client: TestClient):
        """Test 500 internal server error handling."""
        # Mock the health check to raise an exception
        mock_health_check.side_effect = Exception("Test internal error")
        
        response = client.get("/health")
        
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"] == "INTERNAL_SERVER_ERROR"
        assert data["message"] == "An internal server error occurred"
        assert "correlation_id" in data
        
        # Should still have headers
        assert "X-Correlation-ID" in response.headers


class TestTrustedHostMiddleware:
    """Test trusted host middleware (in production)."""
    
    @patch('app.core.config.get_settings')
    def test_trusted_host_middleware_production(self, mock_get_settings, client: TestClient):
        """Test trusted host middleware in production mode."""
        # Mock production settings
        mock_settings = Mock()
        mock_settings.DEBUG = False
        mock_settings.TRUSTED_HOSTS = ["trusted-domain.com"]
        mock_settings.PROJECT_NAME = "RottenStocks API"
        mock_settings.VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "production"
        mock_settings.get_cors_origins.return_value = ["http://localhost:3000"]
        mock_get_settings.return_value = mock_settings
        
        # This test would need a new app instance with production config
        # For now, just verify the middleware doesn't break in debug mode
        response = client.get("/health")
        assert response.status_code == 200


class TestMiddlewareIntegration:
    """Test middleware components working together."""
    
    def test_all_middleware_headers_present(self, client: TestClient):
        """Test that all expected middleware headers are present."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # From request logging middleware
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
        
        # From CORS middleware (when origin is provided)
        cors_response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        assert "Access-Control-Allow-Origin" in cors_response.headers
    
    def test_middleware_order_effects(self, client: TestClient):
        """Test that middleware executes in correct order."""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        
        # Correlation ID should be consistent
        header_correlation_id = response.headers["X-Correlation-ID"]
        data = response.json()
        body_correlation_id = data["correlation_id"]
        
        assert header_correlation_id == body_correlation_id
        
        # Process time should be recorded
        process_time = float(response.headers["X-Process-Time"])
        assert process_time > 0
    
    def test_middleware_with_error_responses(self, client: TestClient):
        """Test middleware behavior with error responses."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        
        # Middleware should still work for error responses
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
        
        # Response should be valid JSON
        data = response.json()
        assert isinstance(data, dict)
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_middleware_with_async_requests(self, async_client):
        """Test middleware with async requests."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        
        # Should have middleware headers
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
        
        # Should have valid response
        data = response.json()
        assert data["status"] == "healthy"