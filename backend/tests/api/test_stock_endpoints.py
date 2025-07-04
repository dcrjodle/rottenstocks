"""
Tests for stock API endpoints.

Comprehensive test coverage for all stock CRUD operations and business logic.
"""

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.stock import Stock


class TestStockEndpoints:
    """Test class for stock endpoints."""
    
    async def test_create_stock_success(self, async_client: AsyncClient, override_get_db):
        """Test successful stock creation."""
        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": 3000000000000,
            "current_price": 150.50,
            "is_active": True
        }
        
        response = await async_client.post("/api/v1/stocks/", json=stock_data)
        
        if response.status_code != 201:
            print(f"Response: {response.status_code} - {response.text}")
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["name"] == "Apple Inc."
        assert data["exchange"] == "NASDAQ"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    async def test_create_stock_duplicate_symbol(self, async_client: AsyncClient, override_get_db):
        """Test creating stock with duplicate symbol fails."""
        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ"
        }
        
        # Create first stock
        response1 = await async_client.post("/api/v1/stocks/", json=stock_data)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = await async_client.post("/api/v1/stocks/", json=stock_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]
    
    async def test_create_stock_invalid_data(self, async_client: AsyncClient, override_get_db):
        """Test stock creation with invalid data."""
        invalid_data = {
            "symbol": "",  # Empty symbol
            "name": "Test Company",
            "exchange": "NYSE"
        }
        
        response = await async_client.post("/api/v1/stocks/", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    async def test_get_stock_by_id_success(self, async_client: AsyncClient, override_get_db):
        """Test getting stock by ID."""
        # Create stock first
        stock_data = {
            "symbol": "GOOGL",
            "name": "Alphabet Inc.",
            "exchange": "NASDAQ"
        }
        
        create_response = await async_client.post("/api/v1/stocks/", json=stock_data)
        stock_id = create_response.json()["id"]
        
        # Get stock by ID
        response = await async_client.get(f"/api/v1/stocks/{stock_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == stock_id
        assert data["symbol"] == "GOOGL"
        assert data["name"] == "Alphabet Inc."
    
    async def test_get_stock_by_id_not_found(self, async_client: AsyncClient, override_get_db):
        """Test getting non-existent stock by ID."""
        response = await async_client.get("/api/v1/stocks/99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    async def test_get_stock_by_symbol_success(self, async_client: AsyncClient, override_get_db):
        """Test getting stock by symbol."""
        # Create stock first
        stock_data = {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "exchange": "NASDAQ"
        }
        
        await async_client.post("/api/v1/stocks/", json=stock_data)
        
        # Get stock by symbol
        response = await async_client.get("/api/v1/stocks/symbol/MSFT")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "MSFT"
        assert data["name"] == "Microsoft Corporation"
    
    async def test_get_stock_by_symbol_case_insensitive(self, async_client: AsyncClient, override_get_db):
        """Test getting stock by symbol is case insensitive."""
        # Create stock first
        stock_data = {
            "symbol": "TSLA",
            "name": "Tesla Inc.",
            "exchange": "NASDAQ"
        }
        
        await async_client.post("/api/v1/stocks/", json=stock_data)
        
        # Get stock by lowercase symbol
        response = await async_client.get("/api/v1/stocks/symbol/tsla")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "TSLA"
    
    async def test_update_stock_success(self, async_client: AsyncClient, override_get_db):
        """Test successful stock update."""
        # Create stock first
        stock_data = {
            "symbol": "AMZN",
            "name": "Amazon.com Inc.",
            "exchange": "NASDAQ"
        }
        
        create_response = await async_client.post("/api/v1/stocks/", json=stock_data)
        stock_id = create_response.json()["id"]
        
        # Update stock
        update_data = {
            "name": "Amazon.com, Inc.",
            "sector": "E-commerce",
            "market_cap": 1500000000000
        }
        
        response = await async_client.put(f"/api/v1/stocks/{stock_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Amazon.com, Inc."
        assert data["sector"] == "E-commerce"
        assert data["market_cap"] == 1500000000000
        assert data["symbol"] == "AMZN"  # Unchanged
    
    async def test_update_stock_price(self, async_client: AsyncClient, override_get_db):
        """Test updating stock price data."""
        # Create stock first
        stock_data = {
            "symbol": "NFLX",
            "name": "Netflix Inc.",
            "exchange": "NASDAQ",
            "current_price": 400.00
        }
        
        await async_client.post("/api/v1/stocks/", json=stock_data)
        
        # Update price
        price_data = {
            "current_price": 420.50,
            "previous_close": 415.00,
            "day_high": 425.00,
            "day_low": 410.00,
            "volume": 2500000
        }
        
        response = await async_client.patch("/api/v1/stocks/symbol/NFLX/price", json=price_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_price"] == 420.50
        assert data["previous_close"] == 415.00
        assert data["day_high"] == 425.00
        assert data["day_low"] == 410.00
        assert data["volume"] == 2500000
        assert data["price_change"] == 5.50  # Computed property
        assert data["is_up"] is True  # Computed property
    
    async def test_delete_stock_success(self, async_client: AsyncClient, override_get_db):
        """Test successful stock deletion (soft delete)."""
        # Create stock first
        stock_data = {
            "symbol": "META",
            "name": "Meta Platforms Inc.",
            "exchange": "NASDAQ"
        }
        
        create_response = await async_client.post("/api/v1/stocks/", json=stock_data)
        stock_id = create_response.json()["id"]
        
        # Delete stock
        response = await async_client.delete(f"/api/v1/stocks/{stock_id}")
        
        assert response.status_code == 204
        
        # Verify stock is soft deleted (is_active = False)
        get_response = await async_client.get(f"/api/v1/stocks/{stock_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False
    
    async def test_list_stocks_pagination(self, async_client: AsyncClient, override_get_db):
        """Test stock listing with pagination."""
        # Create multiple stocks
        stocks = [
            {"symbol": "STOCK1", "name": "Stock 1", "exchange": "NYSE"},
            {"symbol": "STOCK2", "name": "Stock 2", "exchange": "NYSE"},
            {"symbol": "STOCK3", "name": "Stock 3", "exchange": "NASDAQ"},
            {"symbol": "STOCK4", "name": "Stock 4", "exchange": "NASDAQ"},
            {"symbol": "STOCK5", "name": "Stock 5", "exchange": "NYSE"},
        ]
        
        for stock in stocks:
            await async_client.post("/api/v1/stocks/", json=stock)
        
        # Test first page
        response = await async_client.get("/api/v1/stocks/?page=1&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 3
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["limit"] == 3
        assert data["pages"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is False
        
        # Test second page
        response = await async_client.get("/api/v1/stocks/?page=2&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 2
        assert data["page"] == 2
        assert data["has_next"] is False
        assert data["has_prev"] is True
    
    async def test_list_stocks_filtering(self, async_client: AsyncClient, override_get_db):
        """Test stock listing with filtering."""
        # Create stocks with different attributes
        stocks = [
            {
                "symbol": "TECH1", 
                "name": "Tech Company 1", 
                "exchange": "NASDAQ",
                "sector": "Technology",
                "current_price": 100.00
            },
            {
                "symbol": "TECH2", 
                "name": "Tech Company 2", 
                "exchange": "NASDAQ",
                "sector": "Technology",
                "current_price": 200.00
            },
            {
                "symbol": "BANK1", 
                "name": "Bank Company 1", 
                "exchange": "NYSE",
                "sector": "Finance",
                "current_price": 50.00
            },
        ]
        
        for stock in stocks:
            await async_client.post("/api/v1/stocks/", json=stock)
        
        # Filter by exchange
        response = await async_client.get("/api/v1/stocks/?exchange=NASDAQ")
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 2
        assert all(stock["exchange"] == "NASDAQ" for stock in data["stocks"])
        
        # Filter by sector
        response = await async_client.get("/api/v1/stocks/?sector=Technology")
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 2
        assert all(stock["sector"] == "Technology" for stock in data["stocks"])
        
        # Filter by price range
        response = await async_client.get("/api/v1/stocks/?min_price=75&max_price=150")
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 1
        assert data["stocks"][0]["symbol"] == "TECH1"
    
    async def test_search_stocks(self, async_client: AsyncClient, override_get_db):
        """Test stock search functionality."""
        # Create stocks
        stocks = [
            {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        ]
        
        for stock in stocks:
            await async_client.post("/api/v1/stocks/", json=stock)
        
        # Search by symbol
        response = await async_client.get("/api/v1/stocks/search?q=AAPL")
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 1
        assert data["stocks"][0]["symbol"] == "AAPL"
        
        # Search by name
        response = await async_client.get("/api/v1/stocks/search?q=Microsoft")
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 1
        assert data["stocks"][0]["symbol"] == "MSFT"
        
        # Search with partial match
        response = await async_client.get("/api/v1/stocks/search?q=Inc")
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 2  # Apple Inc. and Alphabet Inc.
    
    async def test_get_stocks_by_exchange(self, async_client: AsyncClient, override_get_db):
        """Test getting stocks by exchange."""
        # Create stocks
        stocks = [
            {"symbol": "NYSE1", "name": "NYSE Stock 1", "exchange": "NYSE"},
            {"symbol": "NYSE2", "name": "NYSE Stock 2", "exchange": "NYSE"},
            {"symbol": "NASDAQ1", "name": "NASDAQ Stock 1", "exchange": "NASDAQ"},
        ]
        
        for stock in stocks:
            await async_client.post("/api/v1/stocks/", json=stock)
        
        response = await async_client.get("/api/v1/stocks/exchange/NYSE")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(stock["exchange"] == "NYSE" for stock in data)
    
    async def test_get_stocks_by_sector(self, async_client: AsyncClient, override_get_db):
        """Test getting stocks by sector."""
        # Create stocks
        stocks = [
            {"symbol": "TECH1", "name": "Tech 1", "exchange": "NASDAQ", "sector": "Technology"},
            {"symbol": "TECH2", "name": "Tech 2", "exchange": "NASDAQ", "sector": "Technology"},
            {"symbol": "FINANCE1", "name": "Finance 1", "exchange": "NYSE", "sector": "Finance"},
        ]
        
        for stock in stocks:
            await async_client.post("/api/v1/stocks/", json=stock)
        
        response = await async_client.get("/api/v1/stocks/sector/Technology")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(stock["sector"] == "Technology" for stock in data)
    
    async def test_get_active_stocks_count(self, async_client: AsyncClient, override_get_db):
        """Test getting count of active stocks."""
        # Create stocks
        stocks = [
            {"symbol": "ACTIVE1", "name": "Active 1", "exchange": "NYSE", "is_active": True},
            {"symbol": "ACTIVE2", "name": "Active 2", "exchange": "NYSE", "is_active": True},
            {"symbol": "INACTIVE1", "name": "Inactive 1", "exchange": "NYSE", "is_active": False},
        ]
        
        for stock in stocks:
            await async_client.post("/api/v1/stocks/", json=stock)
        
        response = await async_client.get("/api/v1/stocks/stats/count")
        
        assert response.status_code == 200
        data = response.json()
        assert data["active_stocks"] == 2
    
    async def test_bulk_create_stocks(self, async_client: AsyncClient, override_get_db):
        """Test bulk stock creation."""
        bulk_data = {
            "stocks": [
                {"symbol": "BULK1", "name": "Bulk Stock 1", "exchange": "NYSE"},
                {"symbol": "BULK2", "name": "Bulk Stock 2", "exchange": "NASDAQ"},
                {"symbol": "BULK3", "name": "Bulk Stock 3", "exchange": "NYSE"},
            ]
        }
        
        response = await async_client.post("/api/v1/stocks/bulk", json=bulk_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 3
        assert data["updated"] == 0
        assert len(data["errors"]) == 0
        assert len(data["stocks"]) == 3
    
    async def test_bulk_create_with_duplicates(self, async_client: AsyncClient, override_get_db):
        """Test bulk creation with some existing stocks."""
        # Create one stock first
        existing_stock = {"symbol": "EXISTING", "name": "Existing Stock", "exchange": "NYSE"}
        await async_client.post("/api/v1/stocks/", json=existing_stock)
        
        # Bulk create with one existing and one new
        bulk_data = {
            "stocks": [
                {"symbol": "EXISTING", "name": "Updated Existing Stock", "exchange": "NASDAQ"},
                {"symbol": "NEW1", "name": "New Stock 1", "exchange": "NYSE"},
            ]
        }
        
        response = await async_client.post("/api/v1/stocks/bulk", json=bulk_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert data["updated"] == 1
        assert len(data["stocks"]) == 2
    
    async def test_sorting_functionality(self, async_client: AsyncClient, override_get_db):
        """Test sorting stocks by different fields."""
        # Create stocks with different names and prices
        stocks = [
            {"symbol": "C", "name": "C Company", "exchange": "NYSE", "current_price": 30.00},
            {"symbol": "A", "name": "A Company", "exchange": "NYSE", "current_price": 10.00},
            {"symbol": "B", "name": "B Company", "exchange": "NYSE", "current_price": 20.00},
        ]
        
        for stock in stocks:
            await async_client.post("/api/v1/stocks/", json=stock)
        
        # Sort by symbol ascending (default)
        response = await async_client.get("/api/v1/stocks/?sort_by=symbol&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        symbols = [stock["symbol"] for stock in data["stocks"]]
        assert symbols == ["A", "B", "C"]
        
        # Sort by price descending
        response = await async_client.get("/api/v1/stocks/?sort_by=current_price&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        prices = [stock["current_price"] for stock in data["stocks"]]
        assert prices == [30.00, 20.00, 10.00]