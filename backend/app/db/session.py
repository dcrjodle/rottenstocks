"""
Database session management.

Provides async SQLAlchemy session factory and database connection
utilities for the application using the new database utilities.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.core.config import get_settings
from .config import get_database_config
from .utils import DatabaseManager
from .exceptions import handle_database_error, DatabaseErrorHandler

logger = logging.getLogger(__name__)

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

# Legacy support for existing code
settings = get_settings()
db_config = get_database_config()

# Create async engine using new configuration utilities
engine = create_async_engine(
    db_config.database_url,
    **db_config.get_engine_kwargs()
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Synchronous engine for Alembic
sync_engine = create_engine(
    db_config.sync_database_url,
    echo=db_config.echo,
    pool_size=db_config.pool_size,
    max_overflow=db_config.max_overflow,
    pool_timeout=db_config.pool_timeout,
    pool_recycle=db_config.pool_recycle,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session
    """
    async with DatabaseErrorHandler("Database session operation"):
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                # Convert to database error if needed
                raise handle_database_error(e)
            finally:
                await session.close()


async def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(db_config.database_url, **db_config.get_engine_kwargs())
        await _db_manager.initialize()
    
    return _db_manager


async def shutdown_database_manager() -> None:
    """Shutdown the global database manager."""
    global _db_manager
    
    if _db_manager is not None:
        await _db_manager.shutdown()
        _db_manager = None


@asynccontextmanager
async def get_managed_session() -> AsyncSession:
    """
    Get database session using the database manager.
    
    This is an alternative to get_db() that uses the DatabaseManager
    for better error handling and connection management.
    
    Usage:
        async with get_managed_session() as session:
            # Use session
    """
    db_manager = await get_database_manager()
    async with db_manager.get_session() as session:
        yield session


async def create_tables():
    """Create all database tables."""
    from app.db.base import Base
    
    async with DatabaseErrorHandler("Creating database tables"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def drop_tables():
    """Drop all database tables."""
    from app.db.base import Base
    
    async with DatabaseErrorHandler("Dropping database tables"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")


async def check_database_health() -> dict:
    """
    Check database health and connectivity.
    
    Returns:
        Dictionary with health check results
    """
    try:
        db_manager = await get_database_manager()
        return await db_manager.health_check()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


async def get_database_stats() -> dict:
    """
    Get database statistics.
    
    Returns:
        Dictionary with database statistics
    """
    try:
        db_manager = await get_database_manager()
        return await db_manager.get_table_stats()
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}


# Repository factory functions

async def get_stock_repository(session: AsyncSession = None):
    """Get Stock repository instance."""
    from .repositories import StockRepository
    
    if session is None:
        async with get_managed_session() as session:
            return StockRepository(session)
    return StockRepository(session)


async def get_expert_repository(session: AsyncSession = None):
    """Get Expert repository instance."""
    from .repositories import ExpertRepository
    
    if session is None:
        async with get_managed_session() as session:
            return ExpertRepository(session)
    return ExpertRepository(session)


async def get_rating_repository(session: AsyncSession = None):
    """Get Rating repository instance."""
    from .repositories import RatingRepository
    
    if session is None:
        async with get_managed_session() as session:
            return RatingRepository(session)
    return RatingRepository(session)


async def get_social_post_repository(session: AsyncSession = None):
    """Get SocialPost repository instance."""
    from .repositories import SocialPostRepository
    
    if session is None:
        async with get_managed_session() as session:
            return SocialPostRepository(session)
    return SocialPostRepository(session)


# Startup and shutdown handlers for FastAPI

async def startup_database():
    """Initialize database on application startup."""
    try:
        await get_database_manager()
        health = await check_database_health()
        if health["status"] == "healthy":
            logger.info("Database startup completed successfully")
        else:
            logger.error(f"Database startup failed: {health}")
    except Exception as e:
        logger.error(f"Database startup error: {e}")
        raise


async def shutdown_database():
    """Cleanup database on application shutdown."""
    try:
        await shutdown_database_manager()
        if engine:
            await engine.dispose()
        if sync_engine:
            sync_engine.dispose()
        logger.info("Database shutdown completed successfully")
    except Exception as e:
        logger.error(f"Database shutdown error: {e}")