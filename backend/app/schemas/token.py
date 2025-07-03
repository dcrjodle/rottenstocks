"""Token-related schemas for authentication."""

from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class RefreshToken(BaseModel):
    """Refresh token request."""
    refresh_token: str