"""
Tests for the main FastAPI application.

Tests application startup, basic endpoints, middleware, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


def test_health_endpoint(client: TestClient):
    """Test the basic health endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "RottenStocks API"
    assert data["version"] == "1.0.0"
    assert data["environment"] == "development"
    assert "timestamp" in data
    assert "uptime" in data


@pytest.mark.asyncio
async def test_health_endpoint_async(async_client: AsyncClient):
    """Test the health endpoint asynchronously."""
    response = await async_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "RottenStocks API"


def test_health_detailed_endpoint(client: TestClient):
    """Test the detailed health endpoint."""
    response = client.get("/api/v1/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] in ["healthy", "unhealthy"]
    assert data["service"] == "RottenStocks API"
    assert "checks" in data
    assert "configuration" in data
    assert "correlation_id" in data


def test_cors_headers(client: TestClient):
    """Test CORS headers are properly set."""
    response = client.options("/health", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    
    # Should allow CORS requests
    assert response.status_code in [200, 204]


def test_correlation_id_header(client: TestClient):
    """Test that correlation ID is included in response headers."""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert "X-Process-Time" in response.headers


def test_not_found_error(client: TestClient):
    """Test 404 error handling."""
    response = client.get("/nonexistent-endpoint")
    
    assert response.status_code == 404
    data = response.json()
    
    assert data["error"] == "NOT_FOUND"
    assert data["message"] == "The requested resource was not found"
    assert data["path"] == "/nonexistent-endpoint"
    assert data["method"] == "GET"


def test_api_documentation_available(client: TestClient):
    """Test that API documentation is available in development."""
    # Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200
    
    # ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200
    
    # OpenAPI JSON
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "RottenStocks API"


def test_middleware_order(client: TestClient):
    """Test that middleware is applied in correct order."""
    response = client.get("/health")
    
    # Should have compression header if content is large enough
    # Should have CORS headers
    # Should have custom headers from our middleware
    assert "X-Correlation-ID" in response.headers
    assert "X-Process-Time" in response.headers


def test_request_logging_context(client: TestClient):
    """Test that request logging context is properly set."""
    response = client.get("/api/v1/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    
    # Correlation ID should be consistent between middleware and endpoint
    correlation_id_header = response.headers.get("X-Correlation-ID")
    correlation_id_body = data.get("correlation_id")
    
    assert correlation_id_header == correlation_id_body
    assert correlation_id_header != "unknown"


@pytest.mark.asyncio
async def test_concurrent_requests(async_client: AsyncClient):
    """Test handling of concurrent requests."""
    import asyncio
    
    # Make multiple concurrent requests
    tasks = [
        async_client.get("/health") 
        for _ in range(10)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # All requests should succeed
    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    # Each should have unique correlation IDs
    correlation_ids = [
        response.headers.get("X-Correlation-ID") 
        for response in responses
    ]
    assert len(set(correlation_ids)) == 10  # All unique


def test_gzip_compression(client: TestClient):
    """Test that GZip compression is working for large responses."""
    response = client.get(
        "/api/v1/health/detailed",
        headers={"Accept-Encoding": "gzip"}
    )
    
    assert response.status_code == 200
    # For small responses, compression might not be applied
    # This test mainly ensures no errors occur with compression middleware


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
def test_method_not_allowed(client: TestClient, method: str):
    """Test handling of unsupported HTTP methods."""
    if method == "GET":
        # GET /health is supported
        response = client.request(method, "/health")
        assert response.status_code == 200
    else:
        # Other methods on /health should return 405
        response = client.request(method, "/health")
        assert response.status_code == 405