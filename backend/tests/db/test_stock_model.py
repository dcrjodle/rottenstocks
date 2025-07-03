"""
Tests for Stock model.

Tests stock creation, validation, computed properties, and relationships.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.models.stock import Stock


class TestStockModel:
    """Test Stock model functionality."""
    
    def test_stock_creation(self):
        """Test basic stock creation."""
        stock = Stock(
            symbol="AAPL",
            name="Apple Inc.",
            description="Technology company",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            current_price=Decimal("150.00"),
            previous_close=Decimal("148.50"),
        )
        
        assert stock.symbol == "AAPL"
        assert stock.name == "Apple Inc."
        assert stock.exchange == "NASDAQ"
        assert stock.sector == "Technology"
        assert stock.industry == "Consumer Electronics"
        assert stock.current_price == Decimal("150.00")
        assert stock.previous_close == Decimal("148.50")
        assert stock.is_active is True  # Default value
    
    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Should be able to create with minimal required fields
        stock = Stock(
            symbol="GOOGL",
            name="Alphabet Inc.",
            exchange="NASDAQ"
        )
        
        assert stock.symbol == "GOOGL"
        assert stock.name == "Alphabet Inc."
        assert stock.exchange == "NASDAQ"
        
        # Optional fields should be None or have defaults
        assert stock.description is None
        assert stock.sector is None
        assert stock.industry is None
        assert stock.current_price is None
        assert stock.is_active is True
    
    def test_price_change_property(self):
        """Test price change calculated property."""
        stock = Stock(
            symbol="TSLA",
            name="Tesla Inc.",
            exchange="NASDAQ",
            current_price=Decimal("250.00"),
            previous_close=Decimal("245.00")
        )
        
        price_change = stock.price_change
        assert price_change == Decimal("5.00")
        
        # Test with negative change
        stock.current_price = Decimal("240.00")
        price_change = stock.price_change
        assert price_change == Decimal("-5.00")
    
    def test_price_change_property_missing_prices(self):
        """Test price change when prices are missing."""
        stock = Stock(
            symbol="MSFT",
            name="Microsoft Corp.",
            exchange="NASDAQ"
        )
        
        # No prices set
        assert stock.price_change is None
        
        # Only current price set
        stock.current_price = Decimal("300.00")
        assert stock.price_change is None
        
        # Only previous close set
        stock.current_price = None
        stock.previous_close = Decimal("295.00")
        assert stock.price_change is None
    
    def test_price_change_percent_property(self):
        """Test price change percentage calculated property."""
        stock = Stock(
            symbol="AMZN",
            name="Amazon Inc.",
            exchange="NASDAQ",
            current_price=Decimal("110.00"),
            previous_close=Decimal("100.00")
        )
        
        percent_change = stock.price_change_percent
        assert percent_change == Decimal("10.0")  # 10% increase
        
        # Test with decrease
        stock.current_price = Decimal("90.00")
        percent_change = stock.price_change_percent
        assert percent_change == Decimal("-10.0")  # 10% decrease
    
    def test_price_change_percent_zero_previous_close(self):
        """Test price change percentage with zero previous close."""
        stock = Stock(
            symbol="TEST",
            name="Test Corp.",
            exchange="NYSE",
            current_price=Decimal("50.00"),
            previous_close=Decimal("0.00")
        )
        
        # Should return None to avoid division by zero
        assert stock.price_change_percent is None
    
    def test_is_up_property(self):
        """Test is_up calculated property."""
        stock = Stock(
            symbol="META",
            name="Meta Platforms",
            exchange="NASDAQ",
            current_price=Decimal("300.00"),
            previous_close=Decimal("295.00")
        )
        
        assert stock.is_up is True
        
        # Test with down price
        stock.current_price = Decimal("290.00")
        assert stock.is_up is False
        
        # Test with no change
        stock.current_price = Decimal("295.00")
        assert stock.is_up is False
        
        # Test with missing prices
        stock.current_price = None
        assert stock.is_up is None
    
    def test_update_price_data(self):
        """Test updating stock price data."""
        stock = Stock(
            symbol="NVDA",
            name="NVIDIA Corp.",
            exchange="NASDAQ"
        )
        
        # Update with all data
        stock.update_price_data(
            current_price=Decimal("450.00"),
            previous_close=Decimal("440.00"),
            day_high=Decimal("455.00"),
            day_low=Decimal("445.00"),
            volume=25000000
        )
        
        assert stock.current_price == Decimal("450.00")
        assert stock.previous_close == Decimal("440.00")
        assert stock.day_high == Decimal("455.00")
        assert stock.day_low == Decimal("445.00")
        assert stock.volume == 25000000
        
        # last_updated should be set (we can't test exact time due to timing)
        assert stock.last_updated is not None
    
    def test_update_price_data_partial(self):
        """Test updating stock price data with partial information."""
        stock = Stock(
            symbol="AMD",
            name="Advanced Micro Devices",
            exchange="NASDAQ",
            previous_close=Decimal("100.00"),
            day_high=Decimal("105.00")
        )
        
        # Update only current price
        stock.update_price_data(current_price=Decimal("102.00"))
        
        assert stock.current_price == Decimal("102.00")
        # Other fields should remain unchanged
        assert stock.previous_close == Decimal("100.00")
        assert stock.day_high == Decimal("105.00")
    
    def test_stock_repr(self):
        """Test string representation of stock."""
        stock = Stock(
            symbol="IBM",
            name="International Business Machines",
            exchange="NYSE",
            current_price=Decimal("140.50")
        )
        
        repr_str = repr(stock)
        
        assert "Stock" in repr_str
        assert "IBM" in repr_str
        assert "International Business Machines" in repr_str
        assert "140.50" in repr_str
    
    def test_decimal_precision(self):
        """Test that decimal fields maintain precision."""
        stock = Stock(
            symbol="PREC",
            name="Precision Corp.",
            exchange="NYSE",
            current_price=Decimal("123.4567"),
            market_cap=Decimal("1234567890.12")
        )
        
        # Decimals should maintain precision
        assert stock.current_price == Decimal("123.4567")
        assert stock.market_cap == Decimal("1234567890.12")
    
    def test_large_numbers(self):
        """Test handling of large market cap values."""
        stock = Stock(
            symbol="LARGE",
            name="Large Corp.",
            exchange="NYSE",
            market_cap=Decimal("3000000000000.00")  # 3 trillion
        )
        
        assert stock.market_cap == Decimal("3000000000000.00")
    
    def test_boolean_defaults(self):
        """Test boolean field defaults."""
        stock = Stock(
            symbol="BOOL",
            name="Boolean Corp.",
            exchange="NYSE"
        )
        
        assert stock.is_active is True
    
    def test_stock_validation_edge_cases(self):
        """Test edge cases in stock validation."""
        # Very long symbol (should work up to limit)
        stock = Stock(
            symbol="VERYLONGSYM",  # 10 characters (within limit)
            name="Very Long Symbol Corp.",
            exchange="NYSE"
        )
        assert stock.symbol == "VERYLONGSYM"
        
        # Very long name (should work up to limit)
        long_name = "A" * 255  # 255 characters (within limit)
        stock = Stock(
            symbol="LONG",
            name=long_name,
            exchange="NYSE"
        )
        assert stock.name == long_name
    
    @pytest.mark.asyncio
    async def test_stock_database_constraints(self, async_session: AsyncSession):
        """Test database constraints and unique indexes."""
        # Create first stock
        stock1 = Stock(
            symbol="UNIQ",
            name="Unique Corp.",
            exchange="NYSE"
        )
        async_session.add(stock1)
        await async_session.commit()
        
        # Try to create another stock with same symbol (should fail)
        stock2 = Stock(
            symbol="UNIQ",  # Same symbol
            name="Another Corp.",
            exchange="NASDAQ"
        )
        async_session.add(stock2)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_stock_persistence(self, async_session: AsyncSession):
        """Test saving and retrieving stock from database."""
        stock = Stock(
            symbol="PERS",
            name="Persistence Corp.",
            description="A company for testing persistence",
            exchange="NYSE",
            sector="Technology",
            industry="Software",
            market_cap=Decimal("50000000000.00"),
            current_price=Decimal("125.75"),
            previous_close=Decimal("123.50"),
            day_high=Decimal("127.00"),
            day_low=Decimal("122.25"),
            volume=15000000
        )
        
        # Save to database
        async_session.add(stock)
        await async_session.commit()
        
        # Refresh to get updated timestamps
        await async_session.refresh(stock)
        
        # Verify all fields were saved correctly
        assert stock.id is not None
        assert stock.symbol == "PERS"
        assert stock.name == "Persistence Corp."
        assert stock.description == "A company for testing persistence"
        assert stock.exchange == "NYSE"
        assert stock.sector == "Technology"
        assert stock.industry == "Software"
        assert stock.market_cap == Decimal("50000000000.00")
        assert stock.current_price == Decimal("125.75")
        assert stock.previous_close == Decimal("123.50")
        assert stock.day_high == Decimal("127.00")
        assert stock.day_low == Decimal("122.25")
        assert stock.volume == 15000000
        assert stock.is_active is True
        
        # Should have timestamps
        assert stock.created_at is not None
        assert stock.updated_at is not None