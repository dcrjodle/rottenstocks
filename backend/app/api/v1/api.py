"""
API v1 router configuration.

Combines all API endpoints into a single router for the application.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])

# TODO: Add other routers as they're implemented
# api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
# api_router.include_router(ratings.router, prefix="/ratings", tags=["ratings"])
# api_router.include_router(social.router, prefix="/social", tags=["social"])
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])