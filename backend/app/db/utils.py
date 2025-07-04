"""
Database utilities for RottenStocks application.

This module provides standalone database connection management and utilities
that can be used independently of the main application configuration.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.dialects.postgresql import insert

from .base import BaseModel
from .exceptions import (
    DatabaseError,
    ConnectionError,
    DuplicateKeyError,
    ForeignKeyError,
    ValidationError,
    handle_database_error
)

logger = logging.getLogger(__name__)


def get_database_url(
    database_url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    driver: str = "asyncpg"
) -> str:
    """
    Get database URL from environment variables or parameters.
    
    Args:
        database_url: Complete database URL (takes precedence)
        user: Database username
        password: Database password
        host: Database host
        port: Database port
        database: Database name
        driver: Database driver (asyncpg, psycopg2, etc.)
    
    Returns:
        Complete database URL
    """
    if database_url:
        return database_url
    
    # Get from environment variables with defaults
    user = user or os.getenv("DB_USER", "postgres")
    password = password or os.getenv("DB_PASSWORD", "postgres")
    host = host or os.getenv("DB_HOST", "localhost")
    port = port or int(os.getenv("DB_PORT", "5432"))
    database = database or os.getenv("DB_NAME", "rottenstocks")
    
    return f"postgresql+{driver}://{user}:{password}@{host}:{port}/{database}"


class DatabaseConnection:
    """
    Standalone database connection manager.
    
    This class provides a simple way to create database connections
    without requiring the full application configuration.
    """
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        **engine_kwargs
    ):
        """
        Initialize database connection.
        
        Args:
            database_url: Database URL (defaults to environment variables)
            echo: Enable SQL query logging
            pool_size: Connection pool size
            max_overflow: Maximum pool overflow
            pool_timeout: Pool timeout in seconds
            **engine_kwargs: Additional engine parameters
        """
        self.database_url = database_url or get_database_url()
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.engine_kwargs = engine_kwargs
        
        self.engine: Optional[AsyncEngine] = None
        self.session: Optional[AsyncSession] = None
        
    async def __aenter__(self) -> "DatabaseConnection":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Create database engine and session."""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                **self.engine_kwargs
            )
            
            AsyncSessionLocal = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            self.session = AsyncSessionLocal()
            
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    async def disconnect(self) -> None:
        """Close database session and engine."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                
            if self.engine:
                await self.engine.dispose()
                self.engine = None
                
            logger.info("Database connection closed")
            
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        Execute a raw SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query result
        """
        if not self.session:
            raise ConnectionError("Database session not established")
        
        try:
            result = await self.session.execute(text(query), params or {})
            return result
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise handle_database_error(e)
    
    async def execute_and_fetch(self, query: str, params: Optional[Dict] = None) -> List[Tuple]:
        """
        Execute query and fetch all results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result tuples
        """
        result = await self.execute_query(query, params)
        return result.fetchall()
    
    async def execute_and_fetchone(self, query: str, params: Optional[Dict] = None) -> Optional[Tuple]:
        """
        Execute query and fetch one result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Single result tuple or None
        """
        result = await self.execute_query(query, params)
        return result.fetchone()
    
    async def commit(self) -> None:
        """Commit current transaction."""
        if not self.session:
            raise ConnectionError("Database session not established")
        
        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Transaction commit failed: {e}")
            await self.session.rollback()
            raise handle_database_error(e)
    
    async def rollback(self) -> None:
        """Rollback current transaction."""
        if not self.session:
            raise ConnectionError("Database session not established")
        
        try:
            await self.session.rollback()
        except SQLAlchemyError as e:
            logger.error(f"Transaction rollback failed: {e}")
            raise handle_database_error(e)


class DatabaseManager:
    """
    Application-level database manager.
    
    This class provides high-level database operations and connection management
    for the application.
    """
    
    def __init__(self, database_url: Optional[str] = None, **engine_kwargs):
        """
        Initialize database manager.
        
        Args:
            database_url: Database URL
            **engine_kwargs: Additional engine parameters
        """
        self.database_url = database_url or get_database_url()
        self.engine_kwargs = engine_kwargs
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
    
    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self.engine:
            return
        
        try:
            self.engine = create_async_engine(
                self.database_url,
                **self.engine_kwargs
            )
            
            self.session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Database manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise ConnectionError(f"Failed to initialize database manager: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown database engine."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            logger.info("Database manager shutdown")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """
        Get database session as async context manager.
        
        Yields:
            AsyncSession: Database session
        """
        if not self.session_factory:
            await self.initialize()
        
        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise handle_database_error(e)
        finally:
            await session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.
        
        Returns:
            Dictionary with health check results
        """
        if not self.engine:
            await self.initialize()
        
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                
                return {
                    "status": "healthy",
                    "database": "connected",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_table_stats(self) -> Dict[str, int]:
        """
        Get row counts for all tables.
        
        Returns:
            Dictionary with table names and row counts
        """
        stats = {}
        
        async with self.get_session() as session:
            # Get table names
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            # Get row counts
            for table in tables:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                stats[table] = count
        
        return stats


async def create_database_tables(database_url: Optional[str] = None) -> None:
    """
    Create all database tables.
    
    Args:
        database_url: Database URL
    """
    from .base import BaseModel
    
    database_url = database_url or get_database_url()
    
    # Use sync engine for table creation
    sync_url = database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    
    try:
        BaseModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    finally:
        engine.dispose()


async def drop_database_tables(database_url: Optional[str] = None) -> None:
    """
    Drop all database tables.
    
    Args:
        database_url: Database URL
    """
    from .base import BaseModel
    
    database_url = database_url or get_database_url()
    
    # Use sync engine for table operations
    sync_url = database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    
    try:
        BaseModel.metadata.drop_all(engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise
    finally:
        engine.dispose()


def upsert_query(table, constraint_columns: List[str], **values) -> Any:
    """
    Create PostgreSQL upsert query using ON CONFLICT.
    
    Args:
        table: SQLAlchemy table
        constraint_columns: Columns that define uniqueness
        **values: Values to insert/update
    
    Returns:
        SQLAlchemy insert statement with ON CONFLICT
    """
    stmt = insert(table).values(**values)
    
    # Create ON CONFLICT clause
    stmt = stmt.on_conflict_do_update(
        index_elements=constraint_columns,
        set_={key: stmt.excluded[key] for key in values.keys() if key not in constraint_columns}
    )
    
    return stmt


# Utility functions for common database operations

async def get_or_create(
    session: AsyncSession,
    model_class: BaseModel,
    defaults: Optional[Dict] = None,
    **kwargs
) -> Tuple[BaseModel, bool]:
    """
    Get existing instance or create new one.
    
    Args:
        session: Database session
        model_class: Model class
        defaults: Default values for creation
        **kwargs: Query parameters
    
    Returns:
        Tuple of (instance, created_flag)
    """
    try:
        # Try to get existing instance
        stmt = select(model_class).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        
        if instance:
            return instance, False
        
        # Create new instance
        create_kwargs = {**kwargs, **(defaults or {})}
        instance = model_class(**create_kwargs)
        session.add(instance)
        await session.flush()
        
        return instance, True
        
    except SQLAlchemyError as e:
        await session.rollback()
        raise handle_database_error(e)


async def bulk_insert_or_update(
    session: AsyncSession,
    model_class: BaseModel,
    data: List[Dict],
    constraint_columns: List[str]
) -> List[BaseModel]:
    """
    Bulk insert or update records.
    
    Args:
        session: Database session
        model_class: Model class
        data: List of dictionaries with record data
        constraint_columns: Columns that define uniqueness
    
    Returns:
        List of created/updated instances
    """
    try:
        if not data:
            return []
        
        # Use upsert for bulk operations
        stmt = upsert_query(model_class.__table__, constraint_columns, **data[0])
        
        for record in data:
            stmt = upsert_query(model_class.__table__, constraint_columns, **record)
            await session.execute(stmt)
        
        await session.flush()
        
        # Return the inserted/updated records
        # This is a simplified version - in practice you might want to return the actual records
        return []
        
    except SQLAlchemyError as e:
        await session.rollback()
        raise handle_database_error(e)