"""
FastAPI dependencies for request validation and common functionality.

Provides reusable dependencies for authentication, database sessions,
and other common request processing needs.
"""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import verify_token
from app.schemas.token import TokenPayload
from app.db.session import get_db

settings = get_settings()

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


def get_current_user_id(
    request: Request,
    token: Optional[str] = Depends(security)
) -> Optional[str]:
    """
    Extract current user ID from JWT token.
    
    Returns None if no token provided or token is invalid.
    Use this for optional authentication.
    """
    if not token:
        return None
    
    try:
        payload = verify_token(token.credentials)
        if payload is None:
            return None
        return payload.sub
    except JWTError:
        return None


def get_current_user_id_required(
    user_id: Optional[str] = Depends(get_current_user_id)
) -> str:
    """
    Extract current user ID from JWT token (required).
    
    Raises HTTPException if no valid token provided.
    Use this for endpoints that require authentication.
    """
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")


def get_request_logger(request: Request):
    """Get the request-specific logger."""
    return getattr(request.state, "logger", None)


async def get_database(
    db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    """
    Database session dependency.
    
    Use this dependency to inject database sessions into endpoints.
    Example:
        @router.get("/stocks/")
        async def get_stocks(db: AsyncSession = Depends(get_database)):
            # Use db session
    """
    return db


# TODO: Add Redis connection dependency when Redis is implemented
# def get_redis() -> Generator:
#     """Get Redis connection."""
#     try:
#         redis_client = get_redis_client()
#         yield redis_client
#     finally:
#         redis_client.close()


class CommonQueryParams:
    """Common query parameters for list endpoints."""
    
    def __init__(
        self,
        page: int = 1,
        limit: int = 20,
        skip: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
    ):
        self.page = max(1, page)
        self.limit = min(max(1, limit), 100)  # Limit between 1 and 100
        self.skip = skip if skip is not None else (self.page - 1) * self.limit
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "asc"
        self.search = search.strip() if search else None


def common_parameters(
    page: int = 1,
    limit: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    search: Optional[str] = None,
) -> CommonQueryParams:
    """Dependency for common pagination and filtering parameters."""
    return CommonQueryParams(
        page=page, 
        limit=limit, 
        sort_by=sort_by, 
        sort_order=sort_order,
        search=search
    )


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded."""
    
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"}
        )


def check_rate_limit(request: Request) -> None:
    """
    Check rate limiting for the current request.
    
    TODO: Implement actual rate limiting with Redis.
    For now, this is a placeholder.
    """
    # Placeholder for rate limiting logic
    # In a real implementation, this would:
    # 1. Get client IP or user ID
    # 2. Check request count in Redis
    # 3. Increment counter
    # 4. Raise RateLimitExceeded if limit exceeded
    pass


def api_key_auth(request: Request) -> Optional[str]:
    """
    Optional API key authentication.
    
    Checks for API key in headers and validates it.
    Returns API key if valid, None otherwise.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    
    # TODO: Implement actual API key validation
    # For now, accept any non-empty key
    return api_key if api_key else None


def require_api_key(
    api_key: Optional[str] = Depends(api_key_auth)
) -> str:
    """
    Required API key authentication.
    
    Raises HTTPException if no valid API key provided.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key