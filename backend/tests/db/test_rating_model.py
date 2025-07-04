"""
Tests for Rating model.

Tests rating creation, validation, computed properties, and relationships.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.models.rating import Rating, RatingType, RecommendationType
from app.db.models.stock import Stock
from app.db.models.expert import Expert


class TestRatingModel:
    """Test Rating model functionality."""
    
    def test_rating_creation(self):
        """Test basic rating creation."""
        rating = Rating(
            stock_id="stock123",
            expert_id="expert456",
            rating_type=RatingType.EXPERT,
            score=Decimal("4.2"),
            recommendation=RecommendationType.BUY,
            confidence=Decimal("0.85"),
            price_target=Decimal("150.00"),
            rating_date=datetime.now(timezone.utc)
        )
        
        assert rating.stock_id == "stock123"
        assert rating.expert_id == "expert456"
        assert rating.rating_type == RatingType.EXPERT
        assert rating.score == Decimal("4.2")
        assert rating.recommendation == RecommendationType.BUY
        assert rating.confidence == Decimal("0.85")
        assert rating.price_target == Decimal("150.00")
        assert rating.rating_date is not None
    
    def test_popular_rating_creation(self):
        """Test creating popular rating (no expert)."""
        rating = Rating(
            stock_id="stock123",
            expert_id=None,  # Popular ratings don't have experts
            rating_type=RatingType.POPULAR,
            score=Decimal("3.8"),
            recommendation=RecommendationType.HOLD,
            confidence=Decimal("0.72"),
            sample_size=1247,
            sentiment_sources="Reddit, Twitter, StockTwits",
            rating_date=datetime.now(timezone.utc)
        )
        
        assert rating.stock_id == "stock123"
        assert rating.expert_id is None
        assert rating.rating_type == RatingType.POPULAR
        assert rating.score == Decimal("3.8")
        assert rating.recommendation == RecommendationType.HOLD
        assert rating.sample_size == 1247
        assert rating.sentiment_sources == "Reddit, Twitter, StockTwits"
    
    def test_is_bullish_property(self):
        """Test is_bullish computed property."""
        # Strong buy rating
        rating1 = Rating(
            stock_id="stock1",
            rating_type=RatingType.EXPERT,
            score=Decimal("4.5"),
            recommendation=RecommendationType.STRONG_BUY,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating1.is_bullish is True
        
        # Buy rating
        rating2 = Rating(
            stock_id="stock2",
            rating_type=RatingType.EXPERT,
            score=Decimal("4.0"),
            recommendation=RecommendationType.BUY,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating2.is_bullish is True
        
        # Hold rating
        rating3 = Rating(
            stock_id="stock3",
            rating_type=RatingType.EXPERT,
            score=Decimal("3.0"),
            recommendation=RecommendationType.HOLD,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating3.is_bullish is False
        
        # Sell rating
        rating4 = Rating(
            stock_id="stock4",
            rating_type=RatingType.EXPERT,
            score=Decimal("2.0"),
            recommendation=RecommendationType.SELL,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating4.is_bullish is False
    
    def test_is_bearish_property(self):
        """Test is_bearish computed property."""
        # Strong sell rating
        rating1 = Rating(
            stock_id="stock1",
            rating_type=RatingType.EXPERT,
            score=Decimal("1.5"),
            recommendation=RecommendationType.STRONG_SELL,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating1.is_bearish is True
        
        # Sell rating
        rating2 = Rating(
            stock_id="stock2",
            rating_type=RatingType.EXPERT,
            score=Decimal("2.0"),
            recommendation=RecommendationType.SELL,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating2.is_bearish is True
        
        # Hold rating
        rating3 = Rating(
            stock_id="stock3",
            rating_type=RatingType.EXPERT,
            score=Decimal("3.0"),
            recommendation=RecommendationType.HOLD,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating3.is_bearish is False
        
        # Buy rating
        rating4 = Rating(
            stock_id="stock4",
            rating_type=RatingType.EXPERT,
            score=Decimal("4.0"),
            recommendation=RecommendationType.BUY,
            rating_date=datetime.now(timezone.utc)
        )
        assert rating4.is_bearish is False
    
    def test_rating_type_properties(self):
        """Test rating type identification properties."""
        # Expert rating
        expert_rating = Rating(
            stock_id="stock1",
            expert_id="expert1",
            rating_type=RatingType.EXPERT,
            score=Decimal("4.0"),
            recommendation=RecommendationType.BUY,
            rating_date=datetime.now(timezone.utc)
        )
        assert expert_rating.is_expert_rating is True
        assert expert_rating.is_popular_rating is False
        
        # Popular rating
        popular_rating = Rating(
            stock_id="stock2",
            rating_type=RatingType.POPULAR,
            score=Decimal("3.5"),
            recommendation=RecommendationType.HOLD,
            rating_date=datetime.now(timezone.utc)
        )
        assert popular_rating.is_expert_rating is False
        assert popular_rating.is_popular_rating is True
    
    def test_score_percentage_property(self):
        """Test score_percentage computed property."""
        rating = Rating(
            stock_id="stock1",
            rating_type=RatingType.EXPERT,
            score=Decimal("4.2"),
            recommendation=RecommendationType.BUY,
            rating_date=datetime.now(timezone.utc)
        )
        
        # 4.2 out of 5.0 = 84%
        assert rating.score_percentage == 84
        
        # Test with different scores
        rating.score = Decimal("5.0")
        assert rating.score_percentage == 100
        
        rating.score = Decimal("2.5")
        assert rating.score_percentage == 50
        
        rating.score = Decimal("0.0")
        assert rating.score_percentage == 0
    
    def test_recommendation_display_property(self):
        """Test recommendation_display computed property."""
        recommendations = [
            (RecommendationType.STRONG_BUY, "Strong Buy"),
            (RecommendationType.BUY, "Buy"),
            (RecommendationType.HOLD, "Hold"),
            (RecommendationType.SELL, "Sell"),
            (RecommendationType.STRONG_SELL, "Strong Sell"),
        ]
        
        for recommendation, expected_display in recommendations:
            rating = Rating(
                stock_id="stock1",
                rating_type=RatingType.EXPERT,
                score=Decimal("3.0"),
                recommendation=recommendation,
                rating_date=datetime.now(timezone.utc)
            )
            assert rating.recommendation_display == expected_display
    
    def test_update_rating(self):
        """Test updating rating information."""
        rating = Rating(
            stock_id="stock1",
            rating_type=RatingType.EXPERT,
            score=Decimal("3.5"),
            recommendation=RecommendationType.HOLD,
            confidence=Decimal("0.75"),
            rating_date=datetime.now(timezone.utc)
        )
        
        # Update rating
        rating.update_rating(
            score=Decimal("4.2"),
            recommendation=RecommendationType.BUY,
            confidence=Decimal("0.85"),
            price_target=Decimal("180.00"),
            summary="Upgraded based on strong earnings",
            analysis="Company showed excellent growth in key metrics"
        )
        
        assert rating.score == Decimal("4.2")
        assert rating.recommendation == RecommendationType.BUY
        assert rating.confidence == Decimal("0.85")
        assert rating.price_target == Decimal("180.00")
        assert rating.summary == "Upgraded based on strong earnings"
        assert rating.analysis == "Company showed excellent growth in key metrics"
        assert rating.last_updated is not None
    
    def test_update_rating_partial(self):
        """Test partial rating updates."""
        rating = Rating(
            stock_id="stock1",
            rating_type=RatingType.EXPERT,
            score=Decimal("3.5"),
            recommendation=RecommendationType.HOLD,
            confidence=Decimal("0.75"),
            summary="Original summary",
            rating_date=datetime.now(timezone.utc)
        )
        
        # Update only score and recommendation
        rating.update_rating(
            score=Decimal("4.0"),
            recommendation=RecommendationType.BUY
        )
        
        assert rating.score == Decimal("4.0")
        assert rating.recommendation == RecommendationType.BUY
        # These should remain unchanged
        assert rating.confidence == Decimal("0.75")
        assert rating.summary == "Original summary"
        assert rating.last_updated is not None
    
    def test_update_rating_score_bounds(self):
        """Test that update_rating enforces score bounds."""
        rating = Rating(
            stock_id="stock1",
            rating_type=RatingType.EXPERT,
            score=Decimal("3.0"),
            recommendation=RecommendationType.HOLD,
            rating_date=datetime.now(timezone.utc)
        )
        
        # Test upper bound
        rating.update_rating(score=Decimal("6.0"))
        assert rating.score == Decimal("5.00")
        
        # Test lower bound
        rating.update_rating(score=Decimal("-1.0"))
        assert rating.score == Decimal("0.00")
        
        # Test confidence bounds
        rating.update_rating(confidence=Decimal("1.5"))
        assert rating.confidence == Decimal("1.00")
        
        rating.update_rating(confidence=Decimal("-0.5"))
        assert rating.confidence == Decimal("0.00")
    
    def test_rating_repr(self):
        """Test string representation of rating."""
        # Expert rating
        rating = Rating(
            stock_id="stock1",
            expert_id="expert1",
            rating_type=RatingType.EXPERT,
            score=Decimal("4.2"),
            recommendation=RecommendationType.BUY,
            rating_date=datetime.now(timezone.utc)
        )
        
        # Mock the relationships for repr test
        rating.stock = Stock(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
        rating.expert = Expert(name="John Analyst")
        
        repr_str = repr(rating)
        
        assert "Rating" in repr_str
        assert "AAPL" in repr_str
        assert "John Analyst" in repr_str
        assert "4.2" in repr_str
        assert "buy" in repr_str
    
    def test_popular_rating_repr(self):
        """Test string representation of popular rating."""
        rating = Rating(
            stock_id="stock1",
            rating_type=RatingType.POPULAR,
            score=Decimal("3.8"),
            recommendation=RecommendationType.HOLD,
            rating_date=datetime.now(timezone.utc)
        )
        
        # Mock the stock relationship for repr test
        rating.stock = Stock(symbol="GOOGL", name="Alphabet Inc.", exchange="NASDAQ")
        rating.expert = None
        
        repr_str = repr(rating)
        
        assert "Rating" in repr_str
        assert "GOOGL" in repr_str
        assert "Popular" in repr_str
        assert "3.8" in repr_str
        assert "hold" in repr_str
    
    @pytest.mark.asyncio
    async def test_rating_with_relationships(self, async_session: AsyncSession):
        """Test rating with actual stock and expert relationships."""
        # Create stock
        stock = Stock(
            symbol="TEST",
            name="Test Corp.",
            exchange="NYSE"
        )
        async_session.add(stock)
        await async_session.flush()  # Get the ID
        
        # Create expert
        expert = Expert(
            name="Test Analyst",
            institution="Test Investment"
        )
        async_session.add(expert)
        await async_session.flush()  # Get the ID
        
        # Create rating
        rating = Rating(
            stock_id=stock.id,
            expert_id=expert.id,
            rating_type=RatingType.EXPERT,
            score=Decimal("4.1"),
            recommendation=RecommendationType.BUY,
            confidence=Decimal("0.88"),
            price_target=Decimal("125.00"),
            price_at_rating=Decimal("120.00"),
            summary="Strong buy based on fundamentals",
            analysis="Company shows excellent growth prospects",
            rating_date=datetime.now(timezone.utc)
        )
        async_session.add(rating)
        await async_session.commit()
        
        # Refresh to load relationships
        await async_session.refresh(rating)
        await async_session.refresh(stock)
        await async_session.refresh(expert)
        
        # Verify the rating was saved correctly
        assert rating.id is not None
        assert rating.stock_id == stock.id
        assert rating.expert_id == expert.id
        assert rating.score == Decimal("4.1")
        assert rating.recommendation == RecommendationType.BUY
        
        # Test relationships (note: these would be loaded in a real scenario)
        # For testing relationships, we'd need to configure eager loading
        # or use a different approach
        
        # Test computed properties
        assert rating.is_bullish is True
        assert rating.is_bearish is False
        assert rating.score_percentage == 82
        assert rating.recommendation_display == "Buy"
    
    @pytest.mark.asyncio
    async def test_rating_persistence(self, async_session: AsyncSession):
        """Test saving and retrieving rating from database."""
        # Create stock first
        stock = Stock(
            symbol="PERSIST",
            name="Persistence Corp.",
            exchange="NYSE"
        )
        async_session.add(stock)
        await async_session.flush()
        
        # Create expert first
        expert = Expert(
            name="Persistence Analyst",
            institution="Persistence Investment"
        )
        async_session.add(expert)
        await async_session.flush()
        
        rating = Rating(
            stock_id=stock.id,
            expert_id=expert.id,
            rating_type=RatingType.EXPERT,
            score=Decimal("4.3"),
            recommendation=RecommendationType.BUY,
            confidence=Decimal("0.92"),
            price_target=Decimal("200.00"),
            price_at_rating=Decimal("185.50"),
            summary="Strong fundamentals support higher valuation",
            analysis="Detailed analysis of company's competitive position and growth prospects indicates significant upside potential.",
            risks="Main risks include regulatory changes and increased competition",
            catalysts="Upcoming product launch and market expansion",
            rating_date=datetime.now(timezone.utc),
            expiry_date=datetime.now(timezone.utc) + timedelta(days=90)
        )
        
        # Save to database
        async_session.add(rating)
        await async_session.commit()
        
        # Refresh to get updated timestamps
        await async_session.refresh(rating)
        
        # Verify all fields were saved correctly
        assert rating.id is not None
        assert rating.stock_id == stock.id
        assert rating.expert_id == expert.id
        assert rating.rating_type == RatingType.EXPERT
        assert rating.score == Decimal("4.3")
        assert rating.recommendation == RecommendationType.BUY
        assert rating.confidence == Decimal("0.92")
        assert rating.price_target == Decimal("200.00")
        assert rating.price_at_rating == Decimal("185.50")
        assert rating.summary == "Strong fundamentals support higher valuation"
        assert "Detailed analysis" in rating.analysis
        assert "Main risks include" in rating.risks
        assert "Upcoming product launch" in rating.catalysts
        assert rating.rating_date is not None
        assert rating.expiry_date is not None
        
        # Should have timestamps
        assert rating.created_at is not None
        assert rating.updated_at is not None