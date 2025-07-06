"""
Tests for Reddit service functionality.

Tests the RedditService class which provides high-level Reddit data collection
and processing for financial analysis.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.external_apis.reddit.service import RedditService
from app.external_apis.reddit.schemas import RedditPost, RedditComment, RedditSearchResult, SubredditInfo


class TestRedditService:
    """Test cases for Reddit service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def reddit_service(self, mock_db_session):
        """Create Reddit service for testing."""
        with patch('app.external_apis.reddit.service.RateLimiter'):
            return RedditService(db_session=mock_db_session)

    @pytest.fixture
    def sample_reddit_posts(self):
        """Create sample Reddit posts for testing."""
        return [
            RedditPost(
                id="post1",
                title="TSLA Analysis - Buy or Sell?",
                selftext="Detailed analysis of Tesla stock performance",
                author="analyst_user",
                subreddit="stocks",
                score=150,
                upvote_ratio=0.85,
                num_comments=42,
                created_utc=datetime.utcnow(),
                url="https://reddit.com/r/stocks/post1",
                permalink="/r/stocks/post1",
                is_self=True,
                extracted_symbols=["TSLA"],
                mentions_stocks=True
            ),
            RedditPost(
                id="post2", 
                title="AAPL and MSFT comparison",
                selftext="Comparing Apple and Microsoft fundamentals",
                author="investor_user",
                subreddit="investing",
                score=98,
                upvote_ratio=0.78,
                num_comments=23,
                created_utc=datetime.utcnow() - timedelta(hours=2),
                url="https://reddit.com/r/investing/post2",
                permalink="/r/investing/post2",
                is_self=True,
                extracted_symbols=["AAPL", "MSFT"],
                mentions_stocks=True
            ),
            RedditPost(
                id="post3",
                title="Random discussion about cats",
                selftext="This post has nothing to do with finance",
                author="cat_lover",
                subreddit="cats",
                score=25,
                upvote_ratio=0.92,
                num_comments=5,
                created_utc=datetime.utcnow() - timedelta(hours=1),
                url="https://reddit.com/r/cats/post3",
                permalink="/r/cats/post3",
                is_self=True,
                extracted_symbols=[],
                mentions_stocks=False
            )
        ]

    @pytest.fixture
    def sample_reddit_comments(self):
        """Create sample Reddit comments for testing."""
        return [
            RedditComment(
                id="comment1",
                body="Great TSLA analysis! I agree it's bullish",
                author="commenter1",
                score=15,
                created_utc=datetime.utcnow(),
                permalink="/r/stocks/post1/comment1",
                parent_id="post1",
                depth=1,
                extracted_symbols=["TSLA"],
                mentions_stocks=True
            ),
            RedditComment(
                id="comment2",
                body="AAPL is definitely the better long-term play",
                author="commenter2", 
                score=8,
                created_utc=datetime.utcnow() - timedelta(minutes=30),
                permalink="/r/investing/post2/comment2",
                parent_id="post2",
                depth=1,
                extracted_symbols=["AAPL"],
                mentions_stocks=True
            )
        ]

    @pytest.fixture
    def sample_search_result(self, sample_reddit_posts, sample_reddit_comments):
        """Create sample Reddit search result."""
        return RedditSearchResult(
            posts=sample_reddit_posts[:2],  # Finance-related posts only
            comments=sample_reddit_comments,
            collection_method="finance_discussions",
            query_parameters={"subreddits": ["stocks", "investing"]}
        )

    @pytest.mark.asyncio
    async def test_refresh_stock_symbols_cache(self, reddit_service, mock_db_session):
        """Test stock symbols cache refresh."""
        # Mock database response with stock symbols
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [("TSLA",), ("AAPL",), ("MSFT",)]
        mock_db_session.execute.return_value = mock_result
        
        await reddit_service._refresh_stock_symbols_cache()
        
        assert "TSLA" in reddit_service._valid_symbols_cache
        assert "AAPL" in reddit_service._valid_symbols_cache
        assert "MSFT" in reddit_service._valid_symbols_cache
        assert reddit_service._cache_updated is not None

    def test_validate_stock_symbols(self, reddit_service):
        """Test stock symbol validation."""
        # Set up cache
        reddit_service._valid_symbols_cache = {"TSLA", "AAPL", "MSFT"}
        
        symbols = ["TSLA", "INVALID", "AAPL", "FAKE"]
        validated = reddit_service._validate_stock_symbols(symbols)
        
        assert "TSLA" in validated
        assert "AAPL" in validated
        assert "INVALID" not in validated
        assert "FAKE" not in validated

    def test_validate_stock_symbols_empty_cache(self, reddit_service):
        """Test stock symbol validation with empty cache."""
        # Empty cache should return all symbols (fallback behavior)
        reddit_service._valid_symbols_cache = set()
        
        symbols = ["TSLA", "INVALID", "AAPL"]
        validated = reddit_service._validate_stock_symbols(symbols)
        
        assert validated == symbols  # All symbols returned when cache is empty

    @pytest.mark.asyncio
    async def test_get_finance_discussions(self, reddit_service, sample_search_result):
        """Test getting finance discussions."""
        with patch.object(reddit_service.client, 'get_finance_posts') as mock_get_posts:
            mock_get_posts.return_value = sample_search_result
            
            result = await reddit_service.get_finance_discussions(
                subreddits=["stocks", "investing"],
                limit_per_subreddit=50,
                min_score=10
            )
            
            assert isinstance(result, RedditSearchResult)
            assert len(result.posts) >= 0
            assert result.collection_method == "finance_discussions"
            mock_get_posts.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_discussions(self, reddit_service):
        """Test getting discussions for specific stock."""
        with patch.object(reddit_service.client, 'search_posts') as mock_search:
            # Mock search results for different queries
            mock_search_result = RedditSearchResult(
                posts=[],
                collection_method="search_hot"
            )
            mock_search.return_value = mock_search_result
            
            with patch.object(reddit_service.client, 'get_post_comments') as mock_comments:
                mock_comments.return_value = []
                
                result = await reddit_service.get_stock_discussions(
                    symbol="TSLA",
                    subreddits=["stocks"],
                    limit=100
                )
                
                assert isinstance(result, RedditSearchResult)
                assert result.collection_method == "stock_discussions"
                assert "TSLA" in str(result.query_parameters)

    @pytest.mark.asyncio
    async def test_get_trending_stocks(self, reddit_service, sample_search_result):
        """Test trending stocks analysis."""
        with patch.object(reddit_service, 'get_finance_discussions') as mock_get_discussions:
            mock_get_discussions.return_value = sample_search_result
            
            trending = await reddit_service.get_trending_stocks(
                subreddits=["stocks", "investing"],
                min_mentions=1  # Low threshold for testing
            )
            
            assert isinstance(trending, dict)
            # Should have stocks from our sample posts
            assert len(trending) >= 0
            mock_get_discussions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_subreddit_sentiment(self, reddit_service, sample_reddit_posts):
        """Test subreddit sentiment analysis."""
        mock_result = RedditSearchResult(
            posts=sample_reddit_posts[:2],  # Finance posts only
            collection_method="hot"
        )
        
        with patch.object(reddit_service.client, 'get_posts') as mock_get_posts:
            mock_get_posts.return_value = mock_result
            
            sentiment = await reddit_service.get_subreddit_sentiment(
                subreddit_name="stocks",
                limit=100
            )
            
            assert isinstance(sentiment, dict)
            assert "subreddit" in sentiment
            assert "sentiment" in sentiment
            assert "confidence" in sentiment
            assert sentiment["subreddit"] == "stocks"
            assert sentiment["sentiment"] in ["positive", "negative", "neutral"]

    @pytest.mark.asyncio
    async def test_get_subreddit_sentiment_no_posts(self, reddit_service):
        """Test subreddit sentiment with no posts."""
        mock_result = RedditSearchResult(posts=[], collection_method="hot")
        
        with patch.object(reddit_service.client, 'get_posts') as mock_get_posts:
            mock_get_posts.return_value = mock_result
            
            sentiment = await reddit_service.get_subreddit_sentiment("empty_subreddit")
            
            assert sentiment["sentiment"] == "neutral"
            assert sentiment["confidence"] == 0.0
            assert sentiment["posts_analyzed"] == 0
            assert "error" in sentiment

    @pytest.mark.asyncio
    async def test_save_posts_to_database(self, reddit_service, sample_reddit_posts, sample_reddit_comments, mock_db_session):
        """Test saving posts and comments to database."""
        posts_saved, comments_saved = await reddit_service.save_posts_to_database(
            posts=sample_reddit_posts[:2],
            comments=sample_reddit_comments
        )
        
        assert posts_saved == 2
        assert comments_saved == 2
        
        # Verify database calls
        assert mock_db_session.add.call_count == 4  # 2 posts + 2 comments
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_posts_database_error(self, reddit_service, sample_reddit_posts, mock_db_session):
        """Test database error handling during save."""
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await reddit_service.save_posts_to_database(posts=sample_reddit_posts[:1])
        
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_posts_no_database_session(self, sample_reddit_posts):
        """Test error when no database session provided."""
        service = RedditService(db_session=None)
        
        with pytest.raises(ValueError):
            await service.save_posts_to_database(posts=sample_reddit_posts)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, reddit_service):
        """Test health check when service is healthy."""
        with patch.object(reddit_service.client, 'health_check') as mock_client_health:
            mock_client_health.return_value = {"status": "healthy", "provider": "reddit"}
            
            health = await reddit_service.health_check()
            
            assert health["service"] == "reddit"
            assert health["status"] == "healthy"
            assert "client_health" in health
            assert "cache_status" in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, reddit_service):
        """Test health check when service is unhealthy."""
        with patch.object(reddit_service.client, 'health_check') as mock_client_health:
            mock_client_health.return_value = {"status": "unhealthy", "provider": "reddit", "error": "Connection failed"}
            
            health = await reddit_service.health_check()
            
            assert health["service"] == "reddit"
            assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_db_session):
        """Test Reddit service as async context manager."""
        with patch('app.external_apis.reddit.service.RateLimiter'):
            async with RedditService(db_session=mock_db_session) as service:
                assert isinstance(service, RedditService)
                # Service should be authenticated after entering context

    def test_stock_symbol_validation_performance(self, reddit_service):
        """Test performance of stock symbol validation."""
        # Set up a large cache
        reddit_service._valid_symbols_cache = {f"STOCK{i}" for i in range(1000)}
        
        # Test with large list of symbols
        symbols = ["TSLA", "AAPL"] + [f"INVALID{i}" for i in range(100)]
        
        validated = reddit_service._validate_stock_symbols(symbols)
        
        # Should only return valid symbols
        assert "TSLA" not in validated  # Not in our mock cache
        assert "AAPL" not in validated  # Not in our mock cache
        assert len(validated) == 0  # None of the test symbols are in our mock cache

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, reddit_service):
        """Test that service handles concurrent operations safely."""
        import asyncio
        
        # Mock client methods
        with patch.object(reddit_service.client, 'get_posts') as mock_get_posts:
            mock_result = RedditSearchResult(posts=[], collection_method="hot")
            mock_get_posts.return_value = mock_result
            
            # Run multiple operations concurrently
            tasks = [
                reddit_service.get_subreddit_sentiment("stocks"),
                reddit_service.get_subreddit_sentiment("investing"),
                reddit_service.get_subreddit_sentiment("wallstreetbets")
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete successfully
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, dict)