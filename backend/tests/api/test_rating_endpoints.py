"""
Tests for rating API endpoints.

Comprehensive test coverage for all rating CRUD operations and business logic.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.stock import Stock
from app.db.models.expert import Expert
from app.db.models.rating import Rating, RatingType, RecommendationType


class TestRatingEndpoints:
    """Test class for rating endpoints."""
    
    async def create_test_stock(self, async_client: AsyncClient) -> dict:
        """Helper to create a test stock."""
        stock_data = {
            "symbol": "TEST",
            "name": "Test Company",
            "exchange": "NYSE",
            "current_price": 100.00
        }
        response = await async_client.post("/api/v1/stocks/", json=stock_data)
        return response.json()
    
    async def create_test_expert(self, async_session: AsyncSession) -> Expert:
        """Helper to create a test expert."""
        expert = Expert(
            name="John Analyst",
            email="john@analyst.com",
            institution="Test Bank",
            is_verified=True
        )
        async_session.add(expert)
        await async_session.commit()
        return expert
    
    async def test_create_expert_rating_success(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test successful expert rating creation."""
        # Create stock and expert
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        rating_data = {
            "stock_id": stock["id"],
            "expert_id": expert.id,
            "rating_type": "expert",
            "score": 4.5,
            "recommendation": "buy",
            "confidence": 0.85,
            "price_target": 120.00,
            "price_at_rating": 100.00,
            "summary": "Strong buy recommendation based on growth prospects",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        response = await async_client.post("/api/v1/ratings/", json=rating_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["stock_id"] == stock["id"]
        assert data["expert_id"] == expert.id
        assert data["rating_type"] == "expert"
        assert data["score"] == 4.5
        assert data["recommendation"] == "buy"
        assert data["confidence"] == 0.85
        assert data["is_bullish"] is True
        assert data["is_expert_rating"] is True
        assert data["score_percentage"] == 90  # 4.5/5 * 100
    
    async def test_create_popular_rating_success(self, async_client: AsyncClient, override_get_db):
        """Test successful popular rating creation."""
        # Create stock
        stock = await self.create_test_stock(async_client)
        
        rating_data = {
            "stock_id": stock["id"],
            "expert_id": None,
            "rating_type": "popular",
            "score": 3.2,
            "recommendation": "hold",
            "confidence": 0.65,
            "summary": "Mixed sentiment from social media",
            "rating_date": datetime.now(timezone.utc).isoformat(),
            "sample_size": 1500,
            "sentiment_sources": "Reddit, Twitter"
        }
        
        response = await async_client.post("/api/v1/ratings/", json=rating_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["stock_id"] == stock["id"]
        assert data["expert_id"] is None
        assert data["rating_type"] == "popular"
        assert data["is_popular_rating"] is True
        assert data["sample_size"] == 1500
        assert data["sentiment_sources"] == "Reddit, Twitter"
    
    async def test_create_rating_invalid_stock(self, async_client: AsyncClient, override_get_db):
        """Test creating rating with non-existent stock."""
        rating_data = {
            "stock_id": 99999,
            "expert_id": None,
            "rating_type": "popular",
            "score": 3.0,
            "recommendation": "hold",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        response = await async_client.post("/api/v1/ratings/", json=rating_data)
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]
    
    async def test_create_rating_duplicate(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test creating duplicate rating fails."""
        # Create stock and expert
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        rating_date = datetime.now(timezone.utc)
        rating_data = {
            "stock_id": stock["id"],
            "expert_id": expert.id,
            "rating_type": "expert",
            "score": 4.0,
            "recommendation": "buy",
            "rating_date": rating_date.isoformat()
        }
        
        # Create first rating
        response1 = await async_client.post("/api/v1/ratings/", json=rating_data)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = await async_client.post("/api/v1/ratings/", json=rating_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]
    
    async def test_get_rating_by_id_success(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test getting rating by ID."""
        # Create stock, expert, and rating
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        rating_data = {
            "stock_id": stock["id"],
            "expert_id": expert.id,
            "rating_type": "expert",
            "score": 3.5,
            "recommendation": "hold",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        create_response = await async_client.post("/api/v1/ratings/", json=rating_data)
        rating_id = create_response.json()["id"]
        
        # Get rating by ID
        response = await async_client.get(f"/api/v1/ratings/{rating_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rating_id
        assert data["score"] == 3.5
        assert data["recommendation"] == "hold"
    
    async def test_update_rating_success(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test successful rating update."""
        # Create stock, expert, and rating
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        rating_data = {
            "stock_id": stock["id"],
            "expert_id": expert.id,
            "rating_type": "expert",
            "score": 3.0,
            "recommendation": "hold",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        create_response = await async_client.post("/api/v1/ratings/", json=rating_data)
        rating_id = create_response.json()["id"]
        
        # Update rating
        update_data = {
            "score": 4.0,
            "recommendation": "buy",
            "confidence": 0.9,
            "summary": "Updated analysis shows strong growth potential"
        }
        
        response = await async_client.put(f"/api/v1/ratings/{rating_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 4.0
        assert data["recommendation"] == "buy"
        assert data["confidence"] == 0.9
        assert data["summary"] == "Updated analysis shows strong growth potential"
        assert data["is_bullish"] is True
    
    async def test_delete_rating_success(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test successful rating deletion."""
        # Create stock, expert, and rating
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        rating_data = {
            "stock_id": stock["id"],
            "expert_id": expert.id,
            "rating_type": "expert",
            "score": 3.0,
            "recommendation": "hold",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        create_response = await async_client.post("/api/v1/ratings/", json=rating_data)
        rating_id = create_response.json()["id"]
        
        # Delete rating
        response = await async_client.delete(f"/api/v1/ratings/{rating_id}")
        
        assert response.status_code == 204
        
        # Verify rating is deleted
        get_response = await async_client.get(f"/api/v1/ratings/{rating_id}")
        assert get_response.status_code == 404
    
    async def test_list_ratings_pagination(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test rating listing with pagination."""
        # Create stock and expert
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        # Create multiple ratings
        base_date = datetime.now(timezone.utc)
        for i in range(5):
            rating_data = {
                "stock_id": stock["id"],
                "expert_id": expert.id,
                "rating_type": "expert",
                "score": 3.0 + i * 0.2,
                "recommendation": "hold",
                "rating_date": (base_date + timedelta(hours=i)).isoformat()
            }
            await async_client.post("/api/v1/ratings/", json=rating_data)
        
        # Test pagination
        response = await async_client.get("/api/v1/ratings/?page=1&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["ratings"]) == 3
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["pages"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is False
    
    async def test_list_ratings_filtering(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test rating listing with filtering."""
        # Create stocks and experts
        stock1 = await self.create_test_stock(async_client)
        
        stock2_data = {"symbol": "TEST2", "name": "Test Company 2", "exchange": "NASDAQ"}
        stock2_response = await async_client.post("/api/v1/stocks/", json=stock2_data)
        stock2 = stock2_response.json()
        
        expert = await self.create_test_expert(async_session)
        
        # Create ratings with different attributes
        ratings = [
            {
                "stock_id": stock1["id"],
                "expert_id": expert.id,
                "rating_type": "expert",
                "score": 4.0,
                "recommendation": "buy",
                "rating_date": datetime.now(timezone.utc).isoformat()
            },
            {
                "stock_id": stock2["id"],
                "expert_id": expert.id,
                "rating_type": "expert",
                "score": 2.0,
                "recommendation": "sell",
                "rating_date": datetime.now(timezone.utc).isoformat()
            },
            {
                "stock_id": stock1["id"],
                "expert_id": None,
                "rating_type": "popular",
                "score": 3.5,
                "recommendation": "hold",
                "rating_date": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        for rating in ratings:
            await async_client.post("/api/v1/ratings/", json=rating)
        
        # Filter by stock
        response = await async_client.get(f"/api/v1/ratings/?stock_id={stock1['id']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["ratings"]) == 2
        assert all(r["stock_id"] == stock1["id"] for r in data["ratings"])
        
        # Filter by rating type
        response = await async_client.get("/api/v1/ratings/?rating_type=expert")
        assert response.status_code == 200
        data = response.json()
        assert len(data["ratings"]) == 2
        assert all(r["rating_type"] == "expert" for r in data["ratings"])
        
        # Filter by recommendation
        response = await async_client.get("/api/v1/ratings/?recommendation=buy")
        assert response.status_code == 200
        data = response.json()
        assert len(data["ratings"]) == 1
        assert data["ratings"][0]["recommendation"] == "buy"
        
        # Filter by score range
        response = await async_client.get("/api/v1/ratings/?min_score=3.0&max_score=4.0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["ratings"]) == 2
        for rating in data["ratings"]:
            assert 3.0 <= rating["score"] <= 4.0
    
    async def test_get_stock_ratings(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test getting all ratings for a specific stock."""
        # Create stocks and expert
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        # Create other stock to ensure filtering works
        other_stock_data = {"symbol": "OTHER", "name": "Other Company", "exchange": "NYSE"}
        other_stock_response = await async_client.post("/api/v1/stocks/", json=other_stock_data)
        other_stock = other_stock_response.json()
        
        # Create ratings for target stock
        target_ratings = [
            {
                "stock_id": stock["id"],
                "expert_id": expert.id,
                "rating_type": "expert",
                "score": 4.0,
                "recommendation": "buy",
                "rating_date": datetime.now(timezone.utc).isoformat()
            },
            {
                "stock_id": stock["id"],
                "expert_id": None,
                "rating_type": "popular",
                "score": 3.5,
                "recommendation": "hold",
                "rating_date": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        # Create rating for other stock
        other_rating = {
            "stock_id": other_stock["id"],
            "expert_id": expert.id,
            "rating_type": "expert",
            "score": 2.0,
            "recommendation": "sell",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        for rating in target_ratings:
            await async_client.post("/api/v1/ratings/", json=rating)
        await async_client.post("/api/v1/ratings/", json=other_rating)
        
        # Get ratings for target stock
        response = await async_client.get(f"/api/v1/ratings/stock/{stock['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(r["stock_id"] == stock["id"] for r in data)
    
    async def test_get_expert_ratings(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test getting all ratings by a specific expert."""
        # Create stocks and experts
        stock1 = await self.create_test_stock(async_client)
        
        stock2_data = {"symbol": "TEST2", "name": "Test Company 2", "exchange": "NYSE"}
        stock2_response = await async_client.post("/api/v1/stocks/", json=stock2_data)
        stock2 = stock2_response.json()
        
        expert1 = await self.create_test_expert(async_session)
        
        expert2 = Expert(
            name="Jane Analyst",
            email="jane@analyst.com",
            institution="Another Bank"
        )
        async_session.add(expert2)
        await async_session.commit()
        
        # Create ratings by target expert
        target_ratings = [
            {
                "stock_id": stock1["id"],
                "expert_id": expert1.id,
                "rating_type": "expert",
                "score": 4.0,
                "recommendation": "buy",
                "rating_date": datetime.now(timezone.utc).isoformat()
            },
            {
                "stock_id": stock2["id"],
                "expert_id": expert1.id,
                "rating_type": "expert",
                "score": 3.0,
                "recommendation": "hold",
                "rating_date": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        # Create rating by other expert
        other_rating = {
            "stock_id": stock1["id"],
            "expert_id": expert2.id,
            "rating_type": "expert",
            "score": 2.0,
            "recommendation": "sell",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        for rating in target_ratings:
            await async_client.post("/api/v1/ratings/", json=rating)
        await async_client.post("/api/v1/ratings/", json=other_rating)
        
        # Get ratings by target expert
        response = await async_client.get(f"/api/v1/ratings/expert/{expert1.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(r["expert_id"] == expert1.id for r in data)
    
    async def test_get_stock_rating_aggregation(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test getting aggregated rating data for a stock."""
        # Create stock and expert
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        # Create multiple ratings
        ratings = [
            {
                "stock_id": stock["id"],
                "expert_id": expert.id,
                "rating_type": "expert",
                "score": 4.5,
                "recommendation": "buy",
                "rating_date": datetime.now(timezone.utc).isoformat()
            },
            {
                "stock_id": stock["id"],
                "expert_id": expert.id,
                "rating_type": "expert",
                "score": 4.0,
                "recommendation": "buy",
                "rating_date": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            },
            {
                "stock_id": stock["id"],
                "expert_id": None,
                "rating_type": "popular",
                "score": 3.5,
                "recommendation": "hold",
                "rating_date": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        for rating in ratings:
            await async_client.post("/api/v1/ratings/", json=rating)
        
        # Get aggregation
        response = await async_client.get(f"/api/v1/ratings/stock/{stock['id']}/aggregation")
        
        assert response.status_code == 200
        data = response.json()
        assert data["stock_id"] == stock["id"]
        assert data["total_ratings"] == 3
        assert "expert_ratings" in data
        assert "popular_ratings" in data
        assert "overall_recommendation" in data
        assert "overall_score" in data
        
        # Check expert ratings stats
        expert_stats = data["expert_ratings"]
        assert expert_stats["count"] == 2
        assert expert_stats["average_score"] is not None
        
        # Check popular ratings stats
        popular_stats = data["popular_ratings"]
        assert popular_stats["count"] == 1
    
    async def test_get_stock_rating_history(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test getting historical rating data for a stock."""
        # Create stock and expert
        stock = await self.create_test_stock(async_client)
        expert = await self.create_test_expert(async_session)
        
        # Create ratings over time
        base_date = datetime.now(timezone.utc) - timedelta(days=5)
        for i in range(3):
            rating_data = {
                "stock_id": stock["id"],
                "expert_id": expert.id,
                "rating_type": "expert",
                "score": 3.0 + i * 0.5,
                "recommendation": "hold",
                "rating_date": (base_date + timedelta(days=i)).isoformat()
            }
            await async_client.post("/api/v1/ratings/", json=rating_data)
        
        # Get history
        response = await async_client.get(
            f"/api/v1/ratings/stock/{stock['id']}/history"
            f"?rating_type=expert&period=daily&days=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["stock_id"] == stock["id"]
        assert data["rating_type"] == "expert"
        assert data["period"] == "daily"
        assert len(data["data_points"]) >= 1  # Should have at least one data point
    
    async def test_bulk_create_ratings(self, async_client: AsyncClient, async_session: AsyncSession, override_get_db):
        """Test bulk rating creation."""
        # Create stocks and expert
        stock1 = await self.create_test_stock(async_client)
        
        stock2_data = {"symbol": "BULK2", "name": "Bulk Stock 2", "exchange": "NYSE"}
        stock2_response = await async_client.post("/api/v1/stocks/", json=stock2_data)
        stock2 = stock2_response.json()
        
        expert = await self.create_test_expert(async_session)
        
        bulk_data = {
            "ratings": [
                {
                    "stock_id": stock1["id"],
                    "expert_id": expert.id,
                    "rating_type": "expert",
                    "score": 4.0,
                    "recommendation": "buy",
                    "rating_date": datetime.now(timezone.utc).isoformat()
                },
                {
                    "stock_id": stock2["id"],
                    "expert_id": expert.id,
                    "rating_type": "expert",
                    "score": 3.0,
                    "recommendation": "hold",
                    "rating_date": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        
        response = await async_client.post("/api/v1/ratings/bulk", json=bulk_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2
        assert data["updated"] == 0
        assert len(data["errors"]) == 0
        assert len(data["ratings"]) == 2
    
    async def test_validation_errors(self, async_client: AsyncClient, override_get_db):
        """Test various validation errors."""
        stock = await self.create_test_stock(async_client)
        
        # Invalid score (out of range)
        invalid_rating = {
            "stock_id": stock["id"],
            "expert_id": None,
            "rating_type": "popular",
            "score": 6.0,  # Invalid: max is 5.0
            "recommendation": "buy",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        response = await async_client.post("/api/v1/ratings/", json=invalid_rating)
        assert response.status_code == 422  # Validation error
        
        # Expert rating without expert_id
        invalid_rating = {
            "stock_id": stock["id"],
            "expert_id": None,
            "rating_type": "expert",  # Expert rating needs expert_id
            "score": 4.0,
            "recommendation": "buy",
            "rating_date": datetime.now(timezone.utc).isoformat()
        }
        
        response = await async_client.post("/api/v1/ratings/", json=invalid_rating)
        assert response.status_code == 422  # Validation error