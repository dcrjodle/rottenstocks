"""
Tests for SocialPost model.

Tests social post creation, validation, computed properties, and sentiment analysis.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.models.social_post import SocialPost, Platform, SentimentType
from app.db.models.stock import Stock


class TestSocialPostModel:
    """Test SocialPost model functionality."""
    
    def test_social_post_creation(self):
        """Test basic social post creation."""
        post = SocialPost(
            stock_id="stock123",
            platform=Platform.REDDIT,
            platform_post_id="reddit_post_123",
            url="https://reddit.com/r/stocks/comments/abc123",
            author_username="StockTrader2023",
            title="Great earnings from AAPL",
            content="Apple just reported amazing earnings. This stock is going to the moon! 🚀",
            score=147,
            upvotes=152,
            downvotes=5,
            comment_count=23,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert post.stock_id == "stock123"
        assert post.platform == Platform.REDDIT
        assert post.platform_post_id == "reddit_post_123"
        assert post.url == "https://reddit.com/r/stocks/comments/abc123"
        assert post.author_username == "StockTrader2023"
        assert post.title == "Great earnings from AAPL"
        assert "Apple just reported" in post.content
        assert post.score == 147
        assert post.upvotes == 152
        assert post.downvotes == 5
        assert post.comment_count == 23
        
        # Test defaults
        assert post.mentions_count == 1  # Default
        assert post.has_financial_data is False  # Default
        assert post.contains_prediction is False  # Default
    
    def test_twitter_post_creation(self):
        """Test Twitter post creation."""
        post = SocialPost(
            stock_id="stock456",
            platform=Platform.TWITTER,
            platform_post_id="twitter_post_456",
            author_username="TechAnalyst",
            content="$GOOGL showing strong momentum. AI developments looking promising! #AI #Tech",
            score=89,
            comment_count=12,
            share_count=34,
            hashtags='["AI", "Tech"]',
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert post.platform == Platform.TWITTER
        assert post.hashtags == '["AI", "Tech"]'
        assert post.share_count == 34
        assert post.title is None  # Twitter posts don't have titles
    
    def test_engagement_score_property(self):
        """Test engagement_score computed property."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="test1",
            content="Test content",
            score=50,
            comment_count=10,
            share_count=5,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Engagement = score + (comments * 2) + (shares * 3)
        # = 50 + (10 * 2) + (5 * 3) = 50 + 20 + 15 = 85
        assert post.engagement_score == 85
        
        # Test with missing values
        post2 = SocialPost(
            stock_id="stock2",
            platform=Platform.TWITTER,
            platform_post_id="test2",
            content="Test content 2",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Should be 0 when no engagement metrics
        assert post2.engagement_score == 0
        
        # Test with only some metrics
        post3 = SocialPost(
            stock_id="stock3",
            platform=Platform.TWITTER,
            platform_post_id="test3",
            content="Test content 3",
            comment_count=8,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Engagement = 0 + (8 * 2) + 0 = 16
        assert post3.engagement_score == 16
    
    def test_sentiment_properties(self):
        """Test sentiment-related computed properties."""
        # Positive sentiment
        positive_post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="positive1",
            content="Great stock performance!",
            sentiment_type=SentimentType.POSITIVE,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert positive_post.is_positive_sentiment is True
        assert positive_post.is_negative_sentiment is False
        
        # Very positive sentiment
        very_positive_post = SocialPost(
            stock_id="stock2",
            platform=Platform.TWITTER,
            platform_post_id="verypositive1",
            content="Amazing earnings!",
            sentiment_type=SentimentType.VERY_POSITIVE,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert very_positive_post.is_positive_sentiment is True
        assert very_positive_post.is_negative_sentiment is False
        
        # Negative sentiment
        negative_post = SocialPost(
            stock_id="stock3",
            platform=Platform.REDDIT,
            platform_post_id="negative1",
            content="Poor performance lately",
            sentiment_type=SentimentType.NEGATIVE,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert negative_post.is_positive_sentiment is False
        assert negative_post.is_negative_sentiment is True
        
        # Very negative sentiment
        very_negative_post = SocialPost(
            stock_id="stock4",
            platform=Platform.TWITTER,
            platform_post_id="verynegative1",
            content="Terrible earnings miss",
            sentiment_type=SentimentType.VERY_NEGATIVE,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert very_negative_post.is_positive_sentiment is False
        assert very_negative_post.is_negative_sentiment is True
        
        # Neutral sentiment
        neutral_post = SocialPost(
            stock_id="stock5",
            platform=Platform.REDDIT,
            platform_post_id="neutral1",
            content="Stock is holding steady",
            sentiment_type=SentimentType.NEUTRAL,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert neutral_post.is_positive_sentiment is False
        assert neutral_post.is_negative_sentiment is False
    
    def test_sentiment_display_property(self):
        """Test sentiment_display computed property."""
        sentiments = [
            (SentimentType.VERY_POSITIVE, "Very Positive"),
            (SentimentType.POSITIVE, "Positive"),
            (SentimentType.NEUTRAL, "Neutral"),
            (SentimentType.NEGATIVE, "Negative"),
            (SentimentType.VERY_NEGATIVE, "Very Negative"),
        ]
        
        for sentiment_type, expected_display in sentiments:
            post = SocialPost(
                stock_id="stock1",
                platform=Platform.REDDIT,
                platform_post_id=f"test_{sentiment_type.value}",
                content="Test content",
                sentiment_type=sentiment_type,
                posted_at=datetime.now(timezone.utc),
                collected_at=datetime.now(timezone.utc)
            )
            assert post.sentiment_display == expected_display
        
        # Test with no sentiment
        post_no_sentiment = SocialPost(
            stock_id="stock2",
            platform=Platform.TWITTER,
            platform_post_id="no_sentiment",
            content="Test content",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        assert post_no_sentiment.sentiment_display == "Unknown"
    
    def test_platform_display_property(self):
        """Test platform_display computed property."""
        platforms = [
            (Platform.REDDIT, "Reddit"),
            (Platform.TWITTER, "Twitter"),
            (Platform.STOCKTWITS, "Stocktwits"),
            (Platform.DISCORD, "Discord"),
            (Platform.OTHER, "Other"),
        ]
        
        for platform, expected_display in platforms:
            post = SocialPost(
                stock_id="stock1",
                platform=platform,
                platform_post_id=f"test_{platform.value}",
                content="Test content",
                posted_at=datetime.now(timezone.utc),
                collected_at=datetime.now(timezone.utc)
            )
            assert post.platform_display == expected_display
    
    def test_update_sentiment(self):
        """Test updating sentiment analysis results."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="sentiment_test",
            content="This stock looks interesting",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Initially no sentiment
        assert post.sentiment_type is None
        assert post.sentiment_score is None
        assert post.sentiment_confidence is None
        assert post.analyzed_at is None
        
        # Update with positive sentiment
        before_analysis = datetime.now(timezone.utc)
        post.update_sentiment(
            sentiment_score=Decimal("0.75"),
            confidence=Decimal("0.88")
        )
        after_analysis = datetime.now(timezone.utc)
        
        assert post.sentiment_score == Decimal("0.75")
        assert post.sentiment_confidence == Decimal("0.88")
        assert post.sentiment_type == SentimentType.POSITIVE  # 0.75 is in positive range
        assert post.analyzed_at is not None
        assert before_analysis <= post.analyzed_at <= after_analysis
    
    def test_update_sentiment_categorization(self):
        """Test sentiment score categorization."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="categorization_test",
            content="Test content",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Test different score ranges
        test_cases = [
            (Decimal("0.95"), SentimentType.VERY_POSITIVE),
            (Decimal("0.8"), SentimentType.VERY_POSITIVE),
            (Decimal("0.75"), SentimentType.POSITIVE),
            (Decimal("0.6"), SentimentType.POSITIVE),
            (Decimal("0.55"), SentimentType.NEUTRAL),
            (Decimal("0.4"), SentimentType.NEUTRAL),
            (Decimal("0.35"), SentimentType.NEGATIVE),
            (Decimal("0.2"), SentimentType.NEGATIVE),
            (Decimal("0.15"), SentimentType.VERY_NEGATIVE),
            (Decimal("0.0"), SentimentType.VERY_NEGATIVE),
        ]
        
        for score, expected_type in test_cases:
            post.update_sentiment(
                sentiment_score=score,
                confidence=Decimal("0.9")
            )
            assert post.sentiment_type == expected_type, f"Score {score} should be {expected_type}, got {post.sentiment_type}"
    
    def test_update_sentiment_bounds_checking(self):
        """Test that update_sentiment enforces bounds."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="bounds_test",
            content="Test content",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Test upper bounds
        post.update_sentiment(
            sentiment_score=Decimal("1.5"),
            confidence=Decimal("1.2")
        )
        assert post.sentiment_score == Decimal("1.00")
        assert post.sentiment_confidence == Decimal("1.00")
        
        # Test lower bounds
        post.update_sentiment(
            sentiment_score=Decimal("-0.5"),
            confidence=Decimal("-0.3")
        )
        assert post.sentiment_score == Decimal("0.00")
        assert post.sentiment_confidence == Decimal("0.00")
    
    def test_update_engagement(self):
        """Test updating engagement metrics."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="engagement_test",
            content="Test content",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Update all engagement metrics
        post.update_engagement(
            score=85,
            upvotes=92,
            downvotes=7,
            comment_count=15,
            share_count=8
        )
        
        assert post.score == 85
        assert post.upvotes == 92
        assert post.downvotes == 7
        assert post.comment_count == 15
        assert post.share_count == 8
    
    def test_update_engagement_partial(self):
        """Test partial engagement metric updates."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="partial_engagement_test",
            content="Test content",
            score=50,
            comment_count=10,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Update only some metrics
        post.update_engagement(
            score=65,
            comment_count=18
        )
        
        assert post.score == 65
        assert post.comment_count == 18
        # Other metrics should remain unchanged (None or original values)
        assert post.upvotes is None
        assert post.downvotes is None
        assert post.share_count is None
    
    def test_social_post_repr(self):
        """Test string representation of social post."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="repr_test",
            content="Test content for repr",
            sentiment_type=SentimentType.POSITIVE,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        # Mock the stock relationship for repr test
        post.stock = Stock(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
        
        repr_str = repr(post)
        
        assert "SocialPost" in repr_str
        assert "reddit" in repr_str
        assert "AAPL" in repr_str
        assert "positive" in repr_str
    
    def test_content_analysis_flags(self):
        """Test content analysis boolean flags."""
        post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="analysis_test",
            content="AAPL earnings came in at $1.52 EPS, expecting target price of $200",
            mentions_count=2,
            has_financial_data=True,
            contains_prediction=True,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert post.mentions_count == 2
        assert post.has_financial_data is True
        assert post.contains_prediction is True
    
    def test_platform_specific_fields(self):
        """Test platform-specific fields."""
        # Reddit post
        reddit_post = SocialPost(
            stock_id="stock1",
            platform=Platform.REDDIT,
            platform_post_id="reddit_specific",
            content="Test Reddit post",
            subreddit="wallstreetbets",
            upvotes=234,
            downvotes=12,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert reddit_post.subreddit == "wallstreetbets"
        assert reddit_post.upvotes == 234
        assert reddit_post.downvotes == 12
        assert reddit_post.hashtags is None
        
        # Twitter post
        twitter_post = SocialPost(
            stock_id="stock2",
            platform=Platform.TWITTER,
            platform_post_id="twitter_specific",
            content="Test Twitter post with #hashtags",
            hashtags='["stocks", "investing", "finance"]',
            share_count=45,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        
        assert twitter_post.hashtags == '["stocks", "investing", "finance"]'
        assert twitter_post.share_count == 45
        assert twitter_post.subreddit is None
        assert twitter_post.upvotes is None
        assert twitter_post.downvotes is None
    
    @pytest.mark.asyncio
    async def test_unique_platform_post_constraint(self, async_session: AsyncSession):
        """Test unique constraint on platform + platform_post_id."""
        # Create stocks first
        stock1 = Stock(
            symbol="UNIQUE1",
            name="Unique Corp 1",
            exchange="NYSE"
        )
        stock2 = Stock(
            symbol="UNIQUE2", 
            name="Unique Corp 2",
            exchange="NYSE"
        )
        async_session.add_all([stock1, stock2])
        await async_session.flush()
        
        # Create first post
        post1 = SocialPost(
            stock_id=stock1.id,
            platform=Platform.REDDIT,
            platform_post_id="unique_test_123",
            content="First post",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        async_session.add(post1)
        await async_session.commit()
        
        # Try to create another post with same platform and platform_post_id
        post2 = SocialPost(
            stock_id=stock2.id,  # Different stock
            platform=Platform.REDDIT,  # Same platform
            platform_post_id="unique_test_123",  # Same platform post ID
            content="Second post",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc)
        )
        async_session.add(post2)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_social_post_persistence(self, async_session: AsyncSession):
        """Test saving and retrieving social post from database."""
        # Create stock first
        stock = Stock(
            symbol="PERSIST",
            name="Persistence Corp",
            exchange="NYSE"
        )
        async_session.add(stock)
        await async_session.flush()
        
        post = SocialPost(
            stock_id=stock.id,
            platform=Platform.REDDIT,
            platform_post_id="persistence_test_456",
            url="https://reddit.com/r/stocks/comments/persistence_test",
            author_username="PersistentTrader",
            author_id="user_12345",
            author_follower_count=1250,
            title="Comprehensive analysis of market trends",
            content="After analyzing the recent earnings reports and market conditions, I believe we're seeing a shift in investor sentiment towards technology stocks. The fundamentals look strong across the board.",
            content_excerpt="After analyzing the recent earnings reports...",
            score=189,
            upvotes=203,
            downvotes=14,
            comment_count=47,
            share_count=23,
            sentiment_type=SentimentType.POSITIVE,
            sentiment_score=Decimal("0.78"),
            sentiment_confidence=Decimal("0.84"),
            mentions_count=3,
            has_financial_data=True,
            contains_prediction=True,
            subreddit="stocks",
            hashtags='["analysis", "tech", "earnings"]',
            posted_at=datetime.now(timezone.utc) - timedelta(hours=2),
            collected_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            analyzed_at=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        
        # Save to database
        async_session.add(post)
        await async_session.commit()
        
        # Refresh to get updated timestamps
        await async_session.refresh(post)
        
        # Verify all fields were saved correctly
        assert post.id is not None
        assert post.stock_id == stock.id
        assert post.platform == Platform.REDDIT
        assert post.platform_post_id == "persistence_test_456"
        assert post.url == "https://reddit.com/r/stocks/comments/persistence_test"
        assert post.author_username == "PersistentTrader"
        assert post.author_id == "user_12345"
        assert post.author_follower_count == 1250
        assert post.title == "Comprehensive analysis of market trends"
        assert "After analyzing" in post.content
        assert post.content_excerpt == "After analyzing the recent earnings reports..."
        assert post.score == 189
        assert post.upvotes == 203
        assert post.downvotes == 14
        assert post.comment_count == 47
        assert post.share_count == 23
        assert post.sentiment_type == SentimentType.POSITIVE
        assert post.sentiment_score == Decimal("0.78")
        assert post.sentiment_confidence == Decimal("0.84")
        assert post.mentions_count == 3
        assert post.has_financial_data is True
        assert post.contains_prediction is True
        assert post.subreddit == "stocks"
        assert post.hashtags == '["analysis", "tech", "earnings"]'
        assert post.posted_at is not None
        assert post.collected_at is not None
        assert post.analyzed_at is not None
        
        # Should have timestamps
        assert post.created_at is not None
        assert post.updated_at is not None
        
        # Test computed properties
        assert post.is_positive_sentiment is True
        assert post.is_negative_sentiment is False
        assert post.sentiment_display == "Positive"
        assert post.platform_display == "Reddit"
        # Engagement score = 189 + (47 * 2) + (23 * 3) = 189 + 94 + 69 = 352
        assert post.engagement_score == 352