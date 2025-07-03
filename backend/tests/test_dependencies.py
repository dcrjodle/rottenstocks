"""
Tests for FastAPI dependencies.

Tests authentication, pagination, and other request dependencies.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer

from app.api.v1.deps import (
    get_current_user_id,
    get_current_user_id_required,
    get_correlation_id,
    get_request_logger,
    CommonQueryParams,
    common_parameters,
    RateLimitExceeded,
    check_rate_limit,
    api_key_auth,
    require_api_key,
)
from app.core.security import create_access_token


class TestAuthenticationDependencies:
    """Test authentication-related dependencies."""
    
    def test_get_current_user_id_with_valid_token(self):
        """Test getting user ID with valid token."""
        user_id = "test_user_123"
        token = create_access_token(user_id)
        
        # Mock request and token
        mock_request = Mock(spec=Request)
        mock_token = Mock()
        mock_token.credentials = token
        
        result = get_current_user_id(mock_request, mock_token)
        
        assert result == user_id
    
    def test_get_current_user_id_with_no_token(self):
        """Test getting user ID with no token provided."""
        mock_request = Mock(spec=Request)
        
        result = get_current_user_id(mock_request, None)
        
        assert result is None
    
    def test_get_current_user_id_with_invalid_token(self):
        """Test getting user ID with invalid token."""
        mock_request = Mock(spec=Request)
        mock_token = Mock()
        mock_token.credentials = "invalid.token.here"
        
        result = get_current_user_id(mock_request, mock_token)
        
        assert result is None
    
    def test_get_current_user_id_required_with_valid_user(self):
        """Test required user ID with valid user."""
        user_id = "test_user_123"
        
        result = get_current_user_id_required(user_id)
        
        assert result == user_id
    
    def test_get_current_user_id_required_with_no_user(self):
        """Test required user ID with no user."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_id_required(None)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail


class TestRequestUtilities:
    """Test request utility dependencies."""
    
    def test_get_correlation_id(self):
        """Test getting correlation ID from request."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        mock_request.state.correlation_id = "test-correlation-123"
        
        result = get_correlation_id(mock_request)
        
        assert result == "test-correlation-123"
    
    def test_get_correlation_id_missing(self):
        """Test getting correlation ID when not set."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        # correlation_id not set
        
        result = get_correlation_id(mock_request)
        
        assert result == "unknown"
    
    def test_get_request_logger(self):
        """Test getting request logger."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        mock_logger = Mock()
        mock_request.state.logger = mock_logger
        
        result = get_request_logger(mock_request)
        
        assert result is mock_logger
    
    def test_get_request_logger_missing(self):
        """Test getting request logger when not set."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        # logger not set
        
        result = get_request_logger(mock_request)
        
        assert result is None


class TestPaginationDependencies:
    """Test pagination-related dependencies."""
    
    def test_common_query_params_defaults(self):
        """Test CommonQueryParams with default values."""
        params = CommonQueryParams()
        
        assert params.page == 1
        assert params.limit == 20
        assert params.skip == 0
    
    def test_common_query_params_custom_values(self):
        """Test CommonQueryParams with custom values."""
        params = CommonQueryParams(page=3, limit=50)
        
        assert params.page == 3
        assert params.limit == 50
        assert params.skip == 100  # (3-1) * 50
    
    def test_common_query_params_validation(self):
        """Test CommonQueryParams validation."""
        # Test minimum page
        params = CommonQueryParams(page=0)
        assert params.page == 1  # Should be clamped to 1
        
        # Test negative page
        params = CommonQueryParams(page=-5)
        assert params.page == 1
        
        # Test minimum limit
        params = CommonQueryParams(limit=0)
        assert params.limit == 1  # Should be clamped to 1
        
        # Test maximum limit
        params = CommonQueryParams(limit=200)
        assert params.limit == 100  # Should be clamped to 100
    
    def test_common_query_params_with_skip(self):
        """Test CommonQueryParams with explicit skip value."""
        params = CommonQueryParams(page=2, limit=10, skip=15)
        
        assert params.page == 2
        assert params.limit == 10
        assert params.skip == 15  # Should use provided skip, not calculated
    
    def test_common_parameters_dependency(self):
        """Test the common_parameters dependency function."""
        params = common_parameters(page=2, limit=25)
        
        assert isinstance(params, CommonQueryParams)
        assert params.page == 2
        assert params.limit == 25
        assert params.skip == 25  # (2-1) * 25


class TestRateLimitingDependencies:
    """Test rate limiting dependencies."""
    
    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception."""
        exc = RateLimitExceeded()
        
        assert exc.status_code == 429
        assert exc.detail == "Rate limit exceeded"
        assert "Retry-After" in exc.headers
        assert exc.headers["Retry-After"] == "60"
    
    def test_rate_limit_exceeded_custom_message(self):
        """Test RateLimitExceeded with custom message."""
        custom_message = "Custom rate limit message"
        exc = RateLimitExceeded(detail=custom_message)
        
        assert exc.detail == custom_message
    
    def test_check_rate_limit_placeholder(self):
        """Test rate limit check (placeholder implementation)."""
        mock_request = Mock(spec=Request)
        
        # Should not raise exception (placeholder implementation)
        try:
            check_rate_limit(mock_request)
        except Exception:
            pytest.fail("check_rate_limit should not raise exception in placeholder mode")


class TestAPIKeyDependencies:
    """Test API key authentication dependencies."""
    
    def test_api_key_auth_with_valid_key(self):
        """Test API key authentication with valid key."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-API-Key": "valid-api-key-here"}
        
        result = api_key_auth(mock_request)
        
        assert result == "valid-api-key-here"
    
    def test_api_key_auth_with_no_key(self):
        """Test API key authentication with no key."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        
        result = api_key_auth(mock_request)
        
        assert result is None
    
    def test_api_key_auth_with_empty_key(self):
        """Test API key authentication with empty key."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-API-Key": ""}
        
        result = api_key_auth(mock_request)
        
        assert result is None
    
    def test_require_api_key_with_valid_key(self):
        """Test required API key with valid key."""
        api_key = "valid-api-key"
        
        result = require_api_key(api_key)
        
        assert result == api_key
    
    def test_require_api_key_with_no_key(self):
        """Test required API key with no key."""
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(None)
        
        assert exc_info.value.status_code == 401
        assert "Valid API key required" in exc_info.value.detail
        assert "WWW-Authenticate" in exc_info.value.headers
        assert exc_info.value.headers["WWW-Authenticate"] == "ApiKey"


class TestDependencyIntegration:
    """Test dependencies working together."""
    
    def test_auth_and_pagination_together(self):
        """Test authentication and pagination dependencies together."""
        # Setup authentication
        user_id = "test_user_123"
        token = create_access_token(user_id)
        
        mock_request = Mock(spec=Request)
        mock_token = Mock()
        mock_token.credentials = token
        
        # Test authentication
        auth_user_id = get_current_user_id(mock_request, mock_token)
        assert auth_user_id == user_id
        
        # Test pagination
        pagination = common_parameters(page=2, limit=30)
        assert pagination.page == 2
        assert pagination.limit == 30
        assert pagination.skip == 30
    
    def test_request_context_dependencies(self):
        """Test request context dependencies."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        mock_request.state.correlation_id = "test-correlation-456"
        mock_request.state.logger = Mock()
        
        # Test getting correlation ID
        correlation_id = get_correlation_id(mock_request)
        assert correlation_id == "test-correlation-456"
        
        # Test getting logger
        logger = get_request_logger(mock_request)
        assert logger is mock_request.state.logger