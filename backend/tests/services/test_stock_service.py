"""
Tests for StockService.

Unit tests for stock service business logic.
"""

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.stock_service import StockService
from app.schemas.stock import StockCreate, StockUpdate, StockPriceUpdate, StockSearch
from app.api.v1.deps import CommonQueryParams
from app.db.models.stock import Stock


class TestStockService:
    """Test class for StockService."""
    
    @pytest.fixture
    def stock_service(self, async_session: AsyncSession) -> StockService:
        """Create StockService instance."""
        return StockService(async_session)
    
    async def test_create_stock_success(self, stock_service: StockService):
        """Test successful stock creation."""
        stock_data = StockCreate(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            current_price=Decimal("150.50")
        )
        
        result = await stock_service.create_stock(stock_data)
        
        assert result.symbol == "AAPL"
        assert result.name == "Apple Inc."
        assert result.exchange == "NASDAQ"
        assert result.sector == "Technology"
        assert result.current_price == Decimal("150.50")
        assert result.is_active is True
    
    async def test_create_stock_duplicate_symbol(self, stock_service: StockService):
        """Test creating stock with duplicate symbol fails."""
        stock_data = StockCreate(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ"
        )
        
        # Create first stock
        await stock_service.create_stock(stock_data)
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await stock_service.create_stock(stock_data)
    
    async def test_get_stock_by_symbol(self, stock_service: StockService):
        """Test getting stock by symbol."""
        # Create stock first
        stock_data = StockCreate(
            symbol="GOOGL",
            name="Alphabet Inc.",
            exchange="NASDAQ"
        )
        created = await stock_service.create_stock(stock_data)
        
        # Get by symbol
        result = await stock_service.get_stock_by_symbol("GOOGL")
        
        assert result is not None
        assert result.id == created.id
        assert result.symbol == "GOOGL"
    
    async def test_get_stock_by_symbol_case_insensitive(self, stock_service: StockService):
        """Test getting stock by symbol is case insensitive."""
        # Create stock
        stock_data = StockCreate(
            symbol="MSFT",
            name="Microsoft Corporation",
            exchange="NASDAQ"
        )
        created = await stock_service.create_stock(stock_data)
        
        # Get by lowercase symbol
        result = await stock_service.get_stock_by_symbol("msft")
        
        assert result is not None
        assert result.symbol == "MSFT"
    
    async def test_update_stock(self, stock_service: StockService):
        """Test updating stock."""
        # Create stock first
        stock_data = StockCreate(
            symbol="AMZN",
            name="Amazon.com Inc.",
            exchange="NASDAQ"
        )
        created = await stock_service.create_stock(stock_data)
        
        # Update stock
        update_data = StockUpdate(
            name="Amazon.com, Inc.",
            sector="E-commerce",
            market_cap=Decimal("1500000000000")
        )
        
        result = await stock_service.update_stock(created.id, update_data)
        
        assert result is not None
        assert result.name == "Amazon.com, Inc."
        assert result.sector == "E-commerce"
        assert result.market_cap == Decimal("1500000000000")
        assert result.symbol == "AMZN"  # Unchanged
    
    async def test_update_stock_price(self, stock_service: StockService):
        """Test updating stock price data."""
        # Create stock first
        stock_data = StockCreate(
            symbol="NFLX",
            name="Netflix Inc.",
            exchange="NASDAQ",
            current_price=Decimal("400.00")
        )
        await stock_service.create_stock(stock_data)
        
        # Update price
        price_data = StockPriceUpdate(
            current_price=Decimal("420.50"),
            previous_close=Decimal("415.00"),
            day_high=Decimal("425.00"),
            day_low=Decimal("410.00"),
            volume=2500000
        )
        
        result = await stock_service.update_stock_price("NFLX", price_data)
        
        assert result is not None
        assert result.current_price == Decimal("420.50")
        assert result.previous_close == Decimal("415.00")
        assert result.day_high == Decimal("425.00")
        assert result.day_low == Decimal("410.00")
        assert result.volume == 2500000
        assert result.price_change == Decimal("5.50")
        assert result.is_up is True
    
    async def test_delete_stock_soft_delete(self, stock_service: StockService):
        """Test soft deleting a stock."""
        # Create stock first
        stock_data = StockCreate(
            symbol="META",
            name="Meta Platforms Inc.",
            exchange="NASDAQ"
        )
        created = await stock_service.create_stock(stock_data)
        
        # Delete stock
        deleted = await stock_service.delete_stock(created.id)
        
        assert deleted is True
        
        # Verify stock still exists but is inactive
        result = await stock_service.get_stock_by_id(created.id)
        assert result is not None
        assert result.is_active is False
    
    async def test_list_stocks_pagination(self, stock_service: StockService):
        """Test listing stocks with pagination."""
        # Create multiple stocks
        stocks = [
            StockCreate(symbol=f"STOCK{i}", name=f"Stock {i}", exchange="NYSE")
            for i in range(5)
        ]
        
        for stock in stocks:
            await stock_service.create_stock(stock)
        
        # Test pagination
        params = CommonQueryParams(page=1, limit=3)
        result = await stock_service.list_stocks(params)
        
        assert len(result.stocks) == 3
        assert result.total == 5
        assert result.page == 1
        assert result.pages == 2
        assert result.has_next is True
        assert result.has_prev is False
    
    async def test_list_stocks_filtering(self, stock_service: StockService):
        """Test listing stocks with filtering."""
        # Create stocks with different attributes
        stocks = [
            StockCreate(
                symbol="TECH1",
                name="Tech Company 1",
                exchange="NASDAQ",
                sector="Technology",
                current_price=Decimal("100.00")
            ),
            StockCreate(
                symbol="TECH2",
                name="Tech Company 2",
                exchange="NASDAQ",
                sector="Technology",
                current_price=Decimal("200.00")
            ),
            StockCreate(
                symbol="BANK1",
                name="Bank Company 1",
                exchange="NYSE",
                sector="Finance",
                current_price=Decimal("50.00")
            ),
        ]
        
        for stock in stocks:
            await stock_service.create_stock(stock)
        
        # Filter by exchange
        filters = StockSearch(exchange="NASDAQ")
        params = CommonQueryParams()
        result = await stock_service.list_stocks(params, filters)
        
        assert len(result.stocks) == 2
        assert all(stock.exchange == "NASDAQ" for stock in result.stocks)
        
        # Filter by sector
        filters = StockSearch(sector="Technology")
        result = await stock_service.list_stocks(params, filters)
        
        assert len(result.stocks) == 2
        assert all(stock.sector == "Technology" for stock in result.stocks)
        
        # Filter by price range
        filters = StockSearch(min_price=Decimal("75.00"), max_price=Decimal("150.00"))
        result = await stock_service.list_stocks(params, filters)
        
        assert len(result.stocks) == 1
        assert result.stocks[0].symbol == "TECH1"
    
    async def test_search_stocks(self, stock_service: StockService):
        """Test stock search functionality."""
        # Create stocks
        stocks = [
            StockCreate(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ"),
            StockCreate(symbol="MSFT", name="Microsoft Corporation", exchange="NASDAQ"),
            StockCreate(symbol="GOOGL", name="Alphabet Inc.", exchange="NASDAQ"),
        ]
        
        for stock in stocks:
            await stock_service.create_stock(stock)
        
        # Search by symbol
        search_params = StockSearch(query="AAPL")
        params = CommonQueryParams()
        result = await stock_service.search_stocks(search_params, params)
        
        assert len(result.stocks) == 1
        assert result.stocks[0].symbol == "AAPL"
        
        # Search by name
        search_params = StockSearch(query="Microsoft")
        result = await stock_service.search_stocks(search_params, params)
        
        assert len(result.stocks) == 1
        assert result.stocks[0].symbol == "MSFT"
        
        # Search with partial match
        search_params = StockSearch(query="Inc")
        result = await stock_service.search_stocks(search_params, params)
        
        assert len(result.stocks) == 2  # Apple Inc. and Alphabet Inc.
    
    async def test_get_stocks_by_exchange(self, stock_service: StockService):
        """Test getting stocks by exchange."""
        # Create stocks
        stocks = [
            StockCreate(symbol="NYSE1", name="NYSE Stock 1", exchange="NYSE"),
            StockCreate(symbol="NYSE2", name="NYSE Stock 2", exchange="NYSE"),
            StockCreate(symbol="NASDAQ1", name="NASDAQ Stock 1", exchange="NASDAQ"),
        ]
        
        for stock in stocks:
            await stock_service.create_stock(stock)
        
        result = await stock_service.get_stocks_by_exchange("NYSE")
        
        assert len(result) == 2
        assert all(stock.exchange == "NYSE" for stock in result)
    
    async def test_get_stocks_by_sector(self, stock_service: StockService):
        """Test getting stocks by sector."""
        # Create stocks
        stocks = [
            StockCreate(symbol="TECH1", name="Tech 1", exchange="NASDAQ", sector="Technology"),
            StockCreate(symbol="TECH2", name="Tech 2", exchange="NASDAQ", sector="Technology"),
            StockCreate(symbol="FINANCE1", name="Finance 1", exchange="NYSE", sector="Finance"),
        ]
        
        for stock in stocks:
            await stock_service.create_stock(stock)
        
        result = await stock_service.get_stocks_by_sector("Technology")
        
        assert len(result) == 2
        assert all(stock.sector == "Technology" for stock in result)
    
    async def test_get_active_stocks_count(self, stock_service: StockService):
        """Test getting count of active stocks."""
        # Create stocks
        stocks = [
            StockCreate(symbol="ACTIVE1", name="Active 1", exchange="NYSE", is_active=True),
            StockCreate(symbol="ACTIVE2", name="Active 2", exchange="NYSE", is_active=True),
            StockCreate(symbol="INACTIVE1", name="Inactive 1", exchange="NYSE", is_active=False),
        ]
        
        for stock in stocks:
            await stock_service.create_stock(stock)
        
        count = await stock_service.get_active_stocks_count()
        
        assert count == 2
    
    async def test_bulk_create_stocks(self, stock_service: StockService):
        """Test bulk stock creation."""
        from app.schemas.stock import StockBulkCreate
        
        bulk_data = StockBulkCreate(
            stocks=[
                StockCreate(symbol="BULK1", name="Bulk Stock 1", exchange="NYSE"),
                StockCreate(symbol="BULK2", name="Bulk Stock 2", exchange="NASDAQ"),
                StockCreate(symbol="BULK3", name="Bulk Stock 3", exchange="NYSE"),
            ]
        )
        
        result = await stock_service.bulk_create_stocks(bulk_data)
        
        assert result.created == 3
        assert result.updated == 0
        assert len(result.errors) == 0
        assert len(result.stocks) == 3
    
    async def test_bulk_create_with_existing(self, stock_service: StockService):
        """Test bulk creation with some existing stocks."""
        from app.schemas.stock import StockBulkCreate
        
        # Create one stock first
        existing_stock = StockCreate(symbol="EXISTING", name="Existing Stock", exchange="NYSE")
        await stock_service.create_stock(existing_stock)
        
        # Bulk create with one existing and one new
        bulk_data = StockBulkCreate(
            stocks=[
                StockCreate(symbol="EXISTING", name="Updated Existing Stock", exchange="NASDAQ"),
                StockCreate(symbol="NEW1", name="New Stock 1", exchange="NYSE"),
            ]
        )
        
        result = await stock_service.bulk_create_stocks(bulk_data)
        
        assert result.created == 1
        assert result.updated == 1
        assert len(result.stocks) == 2
    
    async def test_computed_properties(self, stock_service: StockService):
        """Test computed properties in stock response."""
        # Create stock with price data
        stock_data = StockCreate(
            symbol="PROPS",
            name="Properties Test",
            exchange="NYSE",
            current_price=Decimal("105.50"),
            previous_close=Decimal("100.00")
        )
        
        result = await stock_service.create_stock(stock_data)
        
        assert result.price_change == Decimal("5.50")
        assert result.price_change_percent == Decimal("5.50")  # 5.5%
        assert result.is_up is True
    
    async def test_symbol_uppercase_conversion(self, stock_service: StockService):
        """Test that symbols are converted to uppercase."""
        stock_data = StockCreate(
            symbol="lowercase",
            name="Lowercase Symbol Test",
            exchange="NYSE"
        )
        
        result = await stock_service.create_stock(stock_data)
        
        assert result.symbol == "LOWERCASE"
    
    async def test_validation_error_handling(self, stock_service: StockService):
        """Test handling of validation errors."""
        # This would test edge cases and error conditions
        # For now, we rely on Pydantic validation at the schema level
        pass