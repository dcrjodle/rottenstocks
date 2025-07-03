"""
Pytest configuration and shared fixtures.

Provides common test fixtures and configuration for the test suite.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        TESTING=True,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/rottenstocks_test",
        REDIS_URL="redis://localhost:6379/15",
        SECRET_KEY="test-secret-key-not-for-production",
        DEBUG=True,
        REDDIT_CLIENT_ID="test_reddit_client_id",
        REDDIT_CLIENT_SECRET="test_reddit_client_secret",
        REDDIT_USER_AGENT="TestBot/1.0",
        ALPHA_VANTAGE_API_KEY="test_alpha_vantage_key",
        GOOGLE_GEMINI_API_KEY="test_gemini_key",
    )


@pytest.fixture
def override_get_settings(test_settings: Settings):
    """Override the get_settings dependency."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_settings) -> TestClient:
    """Create a test client for synchronous tests."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(override_get_settings) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for asynchronous tests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def async_session(test_settings: Settings) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create test engine
    engine = create_async_engine(
        str(test_settings.DATABASE_URL),
        echo=False,  # Set to True for SQL debugging
        pool_size=1,
        max_overflow=0,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create session
    async with async_session_factory() as session:
        yield session
    
    # Clean up - drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def override_get_db(async_session: AsyncSession):
    """Override the get_db dependency for database tests."""
    async def _get_db_override():
        yield async_session
    
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


# TODO: Add Redis fixtures when Redis is implemented
# @pytest_asyncio.fixture
# async def redis_client():
#     """Create a test Redis client."""
#     pass


@pytest.fixture
def mock_correlation_id() -> str:
    """Provide a mock correlation ID for testing."""
    return "test-correlation-id-12345"