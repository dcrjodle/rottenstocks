"""
Tests for security utilities.

Tests JWT token management, password hashing, and authentication.
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token, 
    verify_token,
    verify_password,
    get_password_hash,
    generate_api_key,
    validate_api_key,
)
from app.core.config import get_settings


class TestJWTTokens:
    """Test JWT token creation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "test_user_123"
        token = create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token structure
        settings = get_settings()
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload
        
        # Check expiration is set correctly
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        now = datetime.utcnow()
        
        # Should expire in approximately ACCESS_TOKEN_EXPIRE_MINUTES
        time_diff = exp_datetime - now
        expected_diff = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Allow 1 minute tolerance
        assert abs(time_diff.total_seconds() - expected_diff.total_seconds()) < 60
    
    def test_create_access_token_custom_expiry(self):
        """Test access token creation with custom expiry."""
        user_id = "test_user_123"
        custom_expiry = timedelta(hours=2)
        token = create_access_token(user_id, expires_delta=custom_expiry)
        
        settings = get_settings()
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        now = datetime.utcnow()
        
        time_diff = exp_datetime - now
        
        # Should expire in approximately 2 hours
        assert abs(time_diff.total_seconds() - custom_expiry.total_seconds()) < 60
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "test_user_123"
        token = create_refresh_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        settings = get_settings()
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        
        # Check expiration is set correctly for refresh token
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        now = datetime.utcnow()
        
        time_diff = exp_datetime - now
        expected_diff = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Allow 1 hour tolerance for refresh tokens
        assert abs(time_diff.total_seconds() - expected_diff.total_seconds()) < 3600
    
    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        user_id = "test_user_123"
        token = create_access_token(user_id)
        
        token_data = verify_token(token)
        
        assert token_data is not None
        assert token_data.sub == user_id
        assert token_data.type == "access"
        assert token_data.exp is not None
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        token_data = verify_token(invalid_token)
        
        assert token_data is None
    
    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        user_id = "test_user_123"
        # Create token that expires immediately
        expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))
        
        token_data = verify_token(expired_token)
        
        assert token_data is None
    
    def test_verify_token_wrong_secret(self):
        """Test token verification with wrong secret key."""
        user_id = "test_user_123"
        
        # Create token with different secret
        wrong_secret = "wrong-secret-key"
        token = jwt.encode(
            {"sub": user_id, "type": "access", "exp": datetime.utcnow() + timedelta(minutes=30)},
            wrong_secret,
            algorithm="HS256"
        )
        
        token_data = verify_token(token)
        
        assert token_data is None


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text
        assert hashed.startswith("$2b$")  # bcrypt hash format
    
    def test_password_verification_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_hash_uniqueness(self):
        """Test that hashing the same password produces different hashes."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Bcrypt includes salt, so hashes should be different
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestAPIKeys:
    """Test API key generation and validation."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()
        
        assert isinstance(api_key, str)
        assert len(api_key) >= 32
        assert api_key.replace("-", "").replace("_", "").isalnum()
    
    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        
        assert key1 != key2
    
    def test_validate_api_key_valid(self):
        """Test API key validation with valid key."""
        valid_key = generate_api_key()
        
        assert validate_api_key(valid_key) is True
    
    def test_validate_api_key_too_short(self):
        """Test API key validation with too short key."""
        short_key = "short"
        
        assert validate_api_key(short_key) is False
    
    def test_validate_api_key_invalid_characters(self):
        """Test API key validation with invalid characters."""
        invalid_key = "a" * 32 + "!@#$"  # 32 valid chars + invalid chars
        
        assert validate_api_key(invalid_key) is False
    
    def test_validate_api_key_empty(self):
        """Test API key validation with empty string."""
        assert validate_api_key("") is False


class TestSecurityIntegration:
    """Test security components working together."""
    
    def test_full_auth_flow(self):
        """Test complete authentication flow."""
        # 1. User registration (password hashing)
        user_id = "test_user_123"
        password = "secure_password_123"
        hashed_password = get_password_hash(password)
        
        # 2. User login (password verification + token creation)
        login_success = verify_password(password, hashed_password)
        assert login_success is True
        
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        # 3. Token verification (API access)
        access_token_data = verify_token(access_token)
        assert access_token_data is not None
        assert access_token_data.sub == user_id
        assert access_token_data.type == "access"
        
        refresh_token_data = verify_token(refresh_token)
        assert refresh_token_data is not None
        assert refresh_token_data.sub == user_id
        assert refresh_token_data.type == "refresh"
    
    def test_token_type_distinction(self):
        """Test that access and refresh tokens are distinguishable."""
        user_id = "test_user_123"
        
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        access_data = verify_token(access_token)
        refresh_data = verify_token(refresh_token)
        
        assert access_data.type == "access"
        assert refresh_data.type == "refresh"
        
        # Refresh tokens should have longer expiry
        assert refresh_data.exp > access_data.exp