"""
Security utilities for authentication and authorization.

Provides JWT token management, password hashing, and security utilities
following FastAPI security best practices.
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.token import TokenPayload

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm="HS256"
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenPayload]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        token_data = TokenPayload(**payload)
        return token_data
    except (JWTError, ValidationError):
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """Generate a secure API key."""
    import secrets
    return secrets.token_urlsafe(32)


def validate_api_key(api_key: str) -> bool:
    """Validate an API key format."""
    # Basic validation - can be enhanced with database lookup
    return len(api_key) >= 32 and api_key.isalnum()