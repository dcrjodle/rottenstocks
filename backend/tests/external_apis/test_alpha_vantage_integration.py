"""
Integration tests for Alpha Vantage API using VCR.

Tests real API interactions with recorded cassettes for reliable testing.
"""

import pytest
import vcr
from unittest.mock import AsyncMock
import os

from app.external_apis.alpha_vantage.client import AlphaVantageClient
from app.external_apis.alpha_vantage.service import AlphaVantageService
from app.external_apis.alpha_vantage.schemas import (
    AlphaVantageQuote,
    AlphaVantageOverview,
    AlphaVantageSearchResults,
)


# VCR configuration
vcr_config = vcr.VCR(
    cassette_library_dir=os.path.join(os.path.dirname(__file__), 'cassettes'),
    record_mode='once',  # Record once, then replay
    match_on=['method', 'uri'],
    filter_headers=['apikey'],  # Don't record API keys
    filter_query_parameters=['apikey'],  # Don't record API keys in URLs
)


class TestAlphaVantageIntegration:
    """Integration tests with real Alpha Vantage API."""
    
    @pytest.fixture
    def api_key(self):
        """Get API key from environment or use demo key."""
        return os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
    
    @pytest.fixture
    async def client(self, api_key):
        """Create Alpha Vantage client for integration tests."""
        client = AlphaVantageClient(api_key=api_key)
        yield client
        await client.close()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for service tests."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for service tests."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, client, mock_db_session, mock_redis):
        """Create Alpha Vantage service for integration tests."""
        return AlphaVantageService(
            client=client,
            db=mock_db_session,
            redis_client=mock_redis
        )
    
    @vcr_config.use_cassette('alpha_vantage_quote_aapl.yaml')
    @pytest.mark.asyncio
    async def test_get_quote_integration(self, client):
        """Test getting real quote from Alpha Vantage."""
        response = await client.get_quote("AAPL")
        
        assert response.success is True
        assert isinstance(response.data, AlphaVantageQuote)
        assert response.data.symbol == "AAPL"
        assert response.data.price > 0
        assert response.data.volume > 0
    
    @vcr_config.use_cassette('alpha_vantage_overview_aapl.yaml')
    @pytest.mark.asyncio
    async def test_get_company_overview_integration(self, client):
        """Test getting real company overview from Alpha Vantage."""
        response = await client.get_company_overview("AAPL")
        
        assert response.success is True
        assert isinstance(response.data, AlphaVantageOverview)
        assert response.data.symbol == "AAPL"
        assert response.data.name == "Apple Inc"
        assert response.data.sector == "TECHNOLOGY"
        assert response.data.exchange == "NASDAQ"
    
    @vcr_config.use_cassette('alpha_vantage_search_apple.yaml')
    @pytest.mark.asyncio
    async def test_search_symbols_integration(self, client):
        """Test searching symbols in Alpha Vantage."""
        response = await client.search_symbols("Apple")
        
        assert response.success is True
        assert isinstance(response.data, AlphaVantageSearchResults)
        assert len(response.data.best_matches) > 0
        
        # Apple Inc (AAPL) should be in the matches
        symbols = [match.symbol for match in response.data.best_matches]
        assert "AAPL" in symbols
        
        # Find the Apple Inc match
        apple_match = next(match for match in response.data.best_matches if match.symbol == "AAPL")
        assert "Apple" in apple_match.name
    
    @vcr_config.use_cassette('alpha_vantage_time_series_aapl.yaml')
    @pytest.mark.asyncio
    async def test_get_daily_time_series_integration(self, client):
        """Test getting daily time series from Alpha Vantage."""
        response = await client.get_daily_time_series("AAPL", "compact")
        
        assert response.success is True
        assert response.data.symbol == "AAPL"
        assert len(response.data.data) > 0
        
        # Check that we have valid price data
        first_date = list(response.data.data.keys())[0]
        first_data = response.data.data[first_date]
        assert first_data.open_price > 0
        assert first_data.close_price > 0
        assert first_data.volume > 0
    
    @vcr_config.use_cassette('alpha_vantage_invalid_symbol.yaml')
    @pytest.mark.asyncio
    async def test_invalid_symbol_integration(self, client):
        """Test handling of invalid symbol."""
        # This should return an error response, not raise an exception
        response = await client.get_quote("INVALID_SYMBOL_XYZ")
        
        # The response structure depends on Alpha Vantage behavior
        # It might return success=False or empty data
        if not response.success:
            assert response.error is not None
        else:
            # Some invalid symbols might return empty data
            assert response.data is None or hasattr(response.data, 'symbol')
    
    @vcr_config.use_cassette('alpha_vantage_batch_quotes.yaml')
    @pytest.mark.asyncio
    async def test_batch_quotes_integration(self, client):
        """Test getting batch quotes from Alpha Vantage."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        results = await client.get_batch_quotes(symbols)
        
        assert len(results) == 3
        
        for symbol in symbols:
            assert symbol in results
            result = results[symbol]
            
            if result.success:
                assert isinstance(result.data, AlphaVantageQuote)
                assert result.data.symbol == symbol
            else:
                # Some symbols might fail due to rate limiting in batch
                assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, client):
        """Test health check with real API."""
        # Don't use VCR for health check to test real connectivity
        health = await client.health_check()
        
        assert health["provider"] == "alpha_vantage"
        assert health["status"] in ["healthy", "unhealthy"]
        assert "api_accessible" in health
    
    @vcr_config.use_cassette('alpha_vantage_service_quote.yaml')
    @pytest.mark.asyncio
    async def test_service_get_quote_integration(self, service):
        """Test service layer quote retrieval."""
        quote = await service.get_stock_quote("AAPL", use_cache=False)
        
        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price > 0
    
    @vcr_config.use_cassette('alpha_vantage_service_overview.yaml')
    @pytest.mark.asyncio
    async def test_service_get_overview_integration(self, service):
        """Test service layer overview retrieval."""
        overview = await service.get_company_overview("AAPL", use_cache=False)
        
        assert overview is not None
        assert overview.symbol == "AAPL"
        assert overview.name == "Apple Inc."
        assert overview.sector == "Technology"
    
    @vcr_config.use_cassette('alpha_vantage_service_search.yaml')
    @pytest.mark.asyncio
    async def test_service_search_integration(self, service):
        """Test service layer symbol search."""
        results = await service.search_symbols("Microsoft", use_cache=False)
        
        assert results is not None
        assert len(results.best_matches) > 0
        
        # Should find Microsoft
        found_msft = any(match.symbol == "MSFT" for match in results.best_matches)
        assert found_msft, "Microsoft (MSFT) should be found in search results"
    
    @pytest.mark.asyncio
    async def test_service_caching_integration(self, service, mock_redis):
        """Test service layer caching behavior."""
        # Mock cache miss then hit
        mock_redis.get.return_value = None  # Cache miss
        
        with vcr_config.use_cassette('alpha_vantage_service_cache_test.yaml'):
            # First call should hit API
            quote1 = await service.get_stock_quote("AAPL", use_cache=True)
            
            # Verify cache write was attempted
            mock_redis.setex.assert_called_once()
            
            # Mock cache hit
            import json
            mock_redis.get.return_value = json.dumps(quote1.dict())
            
            # Second call should use cache
            quote2 = await service.get_stock_quote("AAPL", use_cache=True)
            
            assert quote1.symbol == quote2.symbol
            assert quote1.price == quote2.price
    
    @vcr_config.use_cassette('alpha_vantage_rate_limiting.yaml')
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, client):
        """Test rate limiting behavior with real API."""
        # Make multiple rapid requests to test rate limiting
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META"]
        
        results = []
        for symbol in symbols:
            try:
                response = await client.get_quote(symbol)
                results.append((symbol, response.success))
            except Exception as e:
                results.append((symbol, False))
        
        # With rate limiting, some requests should succeed
        successful = [r for r in results if r[1]]
        assert len(successful) > 0, "At least some requests should succeed"
        
        # If we hit rate limits, later requests might fail
        # This is expected behavior
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, api_key):
        """Test error handling with invalid API key."""
        # Create client with invalid API key
        invalid_client = AlphaVantageClient(api_key="invalid_key_12345")
        
        try:
            with vcr_config.use_cassette('alpha_vantage_invalid_key.yaml'):
                response = await invalid_client.get_quote("AAPL")
                
                # Should handle the error gracefully
                if not response.success:
                    assert response.error is not None
                    assert "invalid" in response.error.error_message.lower() or \
                           "api" in response.error.error_message.lower()
        finally:
            await invalid_client.close()


class TestAlphaVantageServiceIntegration:
    """Integration tests for Alpha Vantage service with database operations."""
    
    @pytest.fixture
    def api_key(self):
        """Get API key from environment or use demo key."""
        return os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
    
    @pytest.fixture
    async def client(self, api_key):
        """Create Alpha Vantage client."""
        client = AlphaVantageClient(api_key=api_key)
        yield client
        await client.close()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session with repository."""
        mock_db = AsyncMock()
        mock_repository = AsyncMock()
        
        # Mock stock repository methods
        mock_repository.get_by_symbol.return_value = None  # No existing stock
        mock_repository.create.return_value = AsyncMock(
            id="test-id",
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ"
        )
        
        return mock_db, mock_repository
    
    @pytest.fixture
    def service_with_mocks(self, client, mock_db):
        """Create service with mocked database."""
        db_session, mock_repository = mock_db
        service = AlphaVantageService(client=client, db=db_session)
        service.stock_repository = mock_repository
        return service
    
    @vcr_config.use_cassette('alpha_vantage_service_stock_creation.yaml')
    @pytest.mark.asyncio
    async def test_create_stock_from_search_integration(self, service_with_mocks):
        """Test creating stock from Alpha Vantage search data."""
        stock = await service_with_mocks.create_stock_from_search("AAPL")
        
        assert stock is not None
        assert stock.symbol == "AAPL"
        
        # Verify database operations were called
        service_with_mocks.stock_repository.get_by_symbol.assert_called_with("AAPL")
        service_with_mocks.stock_repository.create.assert_called_once()
    
    @vcr_config.use_cassette('alpha_vantage_service_price_update.yaml')
    @pytest.mark.asyncio
    async def test_update_stock_price_integration(self, service_with_mocks):
        """Test updating stock price from Alpha Vantage."""
        # Mock existing stock
        mock_stock = AsyncMock()
        mock_stock.id = "test-id"
        mock_stock.symbol = "AAPL"
        mock_stock.update_price_data = AsyncMock()
        
        service_with_mocks.stock_repository.get_by_symbol.return_value = mock_stock
        
        success = await service_with_mocks.update_stock_price("AAPL")
        
        assert success is True
        mock_stock.update_price_data.assert_called_once()
        service_with_mocks.db.commit.assert_called_once()
    
    @vcr_config.use_cassette('alpha_vantage_service_enrich_data.yaml')
    @pytest.mark.asyncio
    async def test_enrich_stock_data_integration(self, service_with_mocks):
        """Test enriching stock data from Alpha Vantage overview."""
        # Mock existing stock
        mock_stock = AsyncMock()
        mock_stock.id = "test-id"
        mock_stock.symbol = "AAPL"
        mock_stock.name = "Apple Inc."
        mock_stock.description = None
        mock_stock.sector = None
        
        service_with_mocks.stock_repository.get_by_symbol.return_value = mock_stock
        service_with_mocks.stock_repository.update.return_value = AsyncMock()
        
        success = await service_with_mocks.enrich_stock_data("AAPL")
        
        assert success is True
        service_with_mocks.stock_repository.update.assert_called_once()
        service_with_mocks.db.commit.assert_called_once()