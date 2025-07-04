"""
Configuration for external API integration tests.

Provides fixtures and setup for testing external API integrations
with VCR cassettes and mocking.
"""

import pytest
import os
from unittest.mock import AsyncMock

# Ensure test environment variables
os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('ALPHA_VANTAGE_API_KEY', 'demo')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/15')  # Test DB


@pytest.fixture(scope="session")
def vcr_config():
    """VCR configuration for recording/replaying HTTP interactions."""
    return {
        "record_mode": "once",
        "match_on": ["method", "uri"],
        "filter_headers": ["apikey", "authorization"],
        "filter_query_parameters": ["apikey", "key"],
        "cassette_library_dir": os.path.join(os.path.dirname(__file__), "cassettes"),
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client for external API tests."""
    mock_redis = AsyncMock()
    
    # Default mock behaviors
    mock_redis.get.return_value = None  # Cache miss by default
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.keys.return_value = []
    mock_redis.ping.return_value = True
    
    return mock_redis


@pytest.fixture
def mock_db_session():
    """Mock database session for external API tests."""
    mock_db = AsyncMock()
    
    # Default mock behaviors
    mock_db.commit.return_value = None
    mock_db.rollback.return_value = None
    mock_db.execute.return_value = AsyncMock()
    
    return mock_db


@pytest.fixture
def mock_stock_repository():
    """Mock stock repository for external API tests."""
    mock_repo = AsyncMock()
    
    # Default mock behaviors
    mock_repo.get_by_symbol.return_value = None
    mock_repo.create.return_value = AsyncMock(
        id="test-stock-id",
        symbol="TEST",
        name="Test Company",
        exchange="NASDAQ"
    )
    mock_repo.update.return_value = AsyncMock()
    
    return mock_repo


@pytest.fixture
def sample_alpha_vantage_quote():
    """Sample Alpha Vantage quote data for testing."""
    return {
        "Global Quote": {
            "01. symbol": "AAPL",
            "02. open": "150.00",
            "03. high": "155.00",
            "04. low": "149.00",
            "05. price": "153.50",
            "06. volume": "1000000",
            "07. latest trading day": "2025-01-01",
            "08. previous close": "152.00",
            "09. change": "1.50",
            "10. change percent": "0.99%"
        }
    }


@pytest.fixture
def sample_alpha_vantage_overview():
    """Sample Alpha Vantage company overview data for testing."""
    return {
        "Symbol": "AAPL",
        "AssetType": "Common Stock",
        "Name": "Apple Inc",
        "Description": "Apple Inc. designs and manufactures consumer electronics...",
        "Exchange": "NASDAQ",
        "Currency": "USD",
        "Country": "USA",
        "Sector": "TECHNOLOGY",
        "Industry": "Consumer Electronics",
        "MarketCapitalization": "3000000000000",
        "PERatio": "25.5",
        "BookValue": "4.50",
        "DividendPerShare": "0.92",
        "DividendYield": "0.0060",
        "EPS": "6.05",
        "RevenuePerShareTTM": "24.32",
        "ProfitMargin": "0.249",
        "OperatingMarginTTM": "0.308",
        "ReturnOnAssetsTTM": "0.206",
        "ReturnOnEquityTTM": "1.566",
        "RevenueTTM": "394328000000",
        "GrossProfitTTM": "169148000000",
        "DilutedEPSTTM": "6.05",
        "QuarterlyEarningsGrowthYOY": "0.111",
        "QuarterlyRevenueGrowthYOY": "0.008",
        "AnalystTargetPrice": "185.50",
        "TrailingPE": "25.36",
        "ForwardPE": "22.73",
        "PriceToSalesRatioTTM": "7.65",
        "PriceToBookRatio": "39.78",
        "EVToRevenue": "7.48",
        "EVToEBITDA": "24.27",
        "Beta": "1.240",
        "52WeekHigh": "199.62",
        "52WeekLow": "164.08",
        "50DayMovingAverage": "181.89",
        "200DayMovingAverage": "175.44",
        "SharesOutstanding": "15204100000",
        "DividendDate": "2024-11-14",
        "ExDividendDate": "2024-11-11"
    }


@pytest.fixture
def sample_alpha_vantage_search():
    """Sample Alpha Vantage search results for testing."""
    return {
        "bestMatches": [
            {
                "1. symbol": "AAPL",
                "2. name": "Apple Inc.",
                "3. type": "Equity",
                "4. region": "United States",
                "5. marketOpen": "09:30",
                "6. marketClose": "16:00",
                "7. timezone": "UTC-05",
                "8. currency": "USD",
                "9. matchScore": "1.0000"
            },
            {
                "1. symbol": "APLE",
                "2. name": "Apple Hospitality REIT Inc.",
                "3. type": "Equity",
                "4. region": "United States",
                "5. marketOpen": "09:30",
                "6. marketClose": "16:00",
                "7. timezone": "UTC-05",
                "8. currency": "USD",
                "9. matchScore": "0.8571"
            }
        ]
    }