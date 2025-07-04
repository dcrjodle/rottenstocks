"""
Tests for Alpha Vantage API client.

Tests the Alpha Vantage client functionality with mocked responses.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from decimal import Decimal

from app.external_apis.alpha_vantage.client import AlphaVantageClient
from app.external_apis.alpha_vantage.schemas import (
    AlphaVantageQuote,
    AlphaVantageOverview,
    AlphaVantageSearchResults,
    AlphaVantageError,
)
from app.external_apis.base.exceptions import ExternalAPIError, ValidationError


class TestAlphaVantageClient:
    """Test Alpha Vantage API client."""
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client."""
        return AsyncMock()
    
    @pytest.fixture
    async def client(self, mock_http_client):
        """Create Alpha Vantage client for testing."""
        client = AlphaVantageClient(api_key="test_api_key")
        client.http_client = mock_http_client
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_quote_success(self, client, mock_http_client):
        """Test successful quote retrieval."""
        # Mock successful quote response
        mock_response = {
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
        mock_http_client.get.return_value = mock_response
        
        response = await client.get_quote("AAPL")
        
        assert response.success is True
        assert isinstance(response.data, AlphaVantageQuote)
        assert response.data.symbol == "AAPL"
        assert response.data.price == Decimal("153.50")
        assert response.data.change == Decimal("1.50")
    
    @pytest.mark.asyncio
    async def test_get_quote_api_error(self, client, mock_http_client):
        """Test quote retrieval with API error."""
        # Mock API error response
        mock_response = {
            "Error Message": "Invalid API call"
        }
        mock_http_client.get.return_value = mock_response
        
        with pytest.raises(ExternalAPIError) as exc_info:
            await client.get_quote("INVALID")
        
        assert "Invalid API call" in str(exc_info.value)
        assert exc_info.value.provider == "alpha_vantage"
    
    @pytest.mark.asyncio
    async def test_get_quote_invalid_format(self, client, mock_http_client):
        """Test quote retrieval with invalid response format."""
        # Mock response without Global Quote
        mock_response = {"SomeOtherData": "value"}
        mock_http_client.get.return_value = mock_response
        
        with pytest.raises(ValidationError) as exc_info:
            await client.get_quote("AAPL")
        
        assert "Invalid quote response format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_quote_empty_data(self, client, mock_http_client):
        """Test quote retrieval with empty data."""
        # Mock response with empty Global Quote
        mock_response = {"Global Quote": {}}
        mock_http_client.get.return_value = mock_response
        
        with pytest.raises(ValidationError) as exc_info:
            await client.get_quote("AAPL")
        
        assert "Empty quote data" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_company_overview_success(self, client, mock_http_client):
        """Test successful company overview retrieval."""
        mock_response = {
            "Symbol": "AAPL",
            "AssetType": "Common Stock",
            "Name": "Apple Inc.",
            "Description": "Apple Inc. designs and manufactures...",
            "Exchange": "NASDAQ",
            "Currency": "USD",
            "Country": "USA",
            "Sector": "Technology",
            "Industry": "Consumer Electronics",
            "MarketCapitalization": "3000000000000",
            "PERatio": "25.5",
            "BookValue": "4.50"
        }
        mock_http_client.get.return_value = mock_response
        
        response = await client.get_company_overview("AAPL")
        
        assert response.success is True
        assert isinstance(response.data, AlphaVantageOverview)
        assert response.data.symbol == "AAPL"
        assert response.data.name == "Apple Inc."
        assert response.data.market_capitalization == 3000000000000
    
    @pytest.mark.asyncio
    async def test_get_company_overview_invalid_symbol(self, client, mock_http_client):
        """Test company overview with invalid symbol."""
        # Mock empty response (invalid symbol)
        mock_response = {}
        mock_http_client.get.return_value = mock_response
        
        with pytest.raises(ValidationError) as exc_info:
            await client.get_company_overview("INVALID")
        
        assert "Invalid or empty overview data" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_symbols_success(self, client, mock_http_client):
        """Test successful symbol search."""
        mock_response = {
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
                }
            ]
        }
        mock_http_client.get.return_value = mock_response
        
        response = await client.search_symbols("Apple")
        
        assert response.success is True
        assert isinstance(response.data, AlphaVantageSearchResults)
        assert len(response.data.best_matches) == 1
        assert response.data.best_matches[0].symbol == "AAPL"
        assert response.data.best_matches[0].name == "Apple Inc."
    
    @pytest.mark.asyncio
    async def test_search_symbols_no_matches(self, client, mock_http_client):
        """Test symbol search with no matches."""
        mock_response = {"bestMatches": []}
        mock_http_client.get.return_value = mock_response
        
        response = await client.search_symbols("NonExistentCompany")
        
        assert response.success is True
        assert len(response.data.best_matches) == 0
    
    @pytest.mark.asyncio
    async def test_get_daily_time_series_success(self, client, mock_http_client):
        """Test successful daily time series retrieval."""
        mock_response = {
            "Meta Data": {
                "1. Information": "Daily Prices",
                "2. Symbol": "AAPL",
                "3. Last Refreshed": "2025-01-01",
                "4. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": {
                "2025-01-01": {
                    "1. open": "150.00",
                    "2. high": "155.00",
                    "3. low": "149.00",
                    "4. close": "153.50",
                    "5. volume": "1000000"
                }
            }
        }
        mock_http_client.get.return_value = mock_response
        
        response = await client.get_daily_time_series("AAPL")
        
        assert response.success is True
        assert response.data.symbol == "AAPL"
        assert len(response.data.data) == 1
    
    @pytest.mark.asyncio
    async def test_get_batch_quotes_success(self, client, mock_http_client):
        """Test successful batch quote retrieval."""
        # Mock quote response
        quote_response = {
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
        mock_http_client.get.return_value = quote_response
        
        results = await client.get_batch_quotes(["AAPL", "GOOGL"])
        
        assert len(results) == 2
        assert "AAPL" in results
        assert "GOOGL" in results
        assert results["AAPL"].success is True
        assert results["GOOGL"].success is True
    
    @pytest.mark.asyncio
    async def test_get_batch_quotes_partial_failure(self, client, mock_http_client):
        """Test batch quotes with partial failures."""
        def mock_get(url, params=None):
            if params and params.get("symbol") == "AAPL":
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
            else:
                return {"Error Message": "Invalid symbol"}
        
        mock_http_client.get.side_effect = mock_get
        
        results = await client.get_batch_quotes(["AAPL", "INVALID"])
        
        assert len(results) == 2
        assert results["AAPL"].success is True
        assert results["INVALID"].success is False
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        with patch.object(client, 'get_quote') as mock_get_quote:
            mock_response = Mock()
            mock_response.success = True
            mock_get_quote.return_value = mock_response
            
            result = await client.health_check()
            
            assert result["provider"] == "alpha_vantage"
            assert result["status"] == "healthy"
            assert result["api_accessible"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure."""
        with patch.object(client, 'get_quote') as mock_get_quote:
            mock_get_quote.side_effect = Exception("API unavailable")
            
            result = await client.health_check()
            
            assert result["provider"] == "alpha_vantage"
            assert result["status"] == "unhealthy"
            assert result["api_accessible"] is False
            assert "API unavailable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_rate_limit_note_error(self, client, mock_http_client):
        """Test rate limit note error handling."""
        mock_response = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
        }
        mock_http_client.get.return_value = mock_response
        
        with pytest.raises(ExternalAPIError) as exc_info:
            await client.get_quote("AAPL")
        
        assert "API call frequency limit reached" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_information_error(self, client, mock_http_client):
        """Test information error handling."""
        mock_response = {
            "Information": "Invalid API call. Please retry or visit the documentation."
        }
        mock_http_client.get.return_value = mock_response
        
        with pytest.raises(ExternalAPIError) as exc_info:
            await client.get_quote("AAPL")
        
        assert "Invalid API call" in str(exc_info.value)