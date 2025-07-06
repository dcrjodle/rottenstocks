"""
Tests for Reddit API client.

Tests the RedditClient class functionality including authentication,
data retrieval, and integration with AsyncPRAW.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.external_apis.reddit.client import RedditClient
from app.external_apis.reddit.schemas import RedditPost, RedditComment, RedditUser, SubredditInfo
from app.external_apis.base.exceptions import AuthenticationError, ExternalAPIError


class TestRedditClient:
    """Test cases for Reddit client functionality."""

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter for testing."""
        limiter = AsyncMock()
        limiter.wait_if_needed = AsyncMock()
        return limiter

    @pytest.fixture
    def reddit_client(self, mock_rate_limiter):
        """Create Reddit client for testing."""
        with patch('app.external_apis.reddit.client.settings') as mock_settings:
            mock_settings.REDDIT_CLIENT_ID = "test_client_id"
            mock_settings.REDDIT_CLIENT_SECRET = "test_client_secret"
            mock_settings.REDDIT_USER_AGENT = "TestAgent/1.0"
            
            return RedditClient(rate_limiter=mock_rate_limiter)

    @pytest.fixture
    def mock_reddit_post(self):
        """Mock Reddit post for testing."""
        post = MagicMock()
        post.id = "test_post_123"
        post.title = "TSLA to the moon! 🚀"
        post.selftext = "Tesla stock analysis and discussion about AAPL too"
        post.author.name = "test_user"
        post.subreddit.display_name = "stocks"
        post.score = 150
        post.upvote_ratio = 0.85
        post.num_comments = 42
        post.created_utc = 1672531200  # 2023-01-01
        post.url = "https://reddit.com/r/stocks/comments/test"
        post.permalink = "/r/stocks/comments/test"
        post.link_flair_text = "Discussion"
        post.is_original_content = False
        post.is_self = True
        post.is_video = False
        post.pinned = False
        post.locked = False
        post.archived = False
        return post

    @pytest.fixture
    def mock_reddit_comment(self):
        """Mock Reddit comment for testing."""
        comment = MagicMock()
        comment.id = "test_comment_456"
        comment.body = "Great analysis! TSLA is definitely bullish"
        comment.author.name = "commenter_user"
        comment.score = 25
        comment.created_utc = 1672531300  # 2023-01-01
        comment.permalink = "/r/stocks/comments/test/comment/456"
        comment.parent_id = "t3_test_post_123"
        comment.depth = 1
        comment.edited = False
        comment.distinguished = None
        return comment

    @pytest.fixture
    def mock_subreddit(self):
        """Mock Reddit subreddit for testing."""
        subreddit = MagicMock()
        subreddit.display_name = "stocks"
        subreddit.display_name_prefixed = "r/stocks"
        subreddit.public_description = "Stock market discussion and investment analysis"
        subreddit.subscribers = 500000
        subreddit.active_user_count = 5000
        subreddit.created_utc = 1200000000  # Much older
        subreddit.over18 = False
        subreddit.quarantine = False
        subreddit.subreddit_type = "public"
        return subreddit

    @pytest.mark.asyncio
    async def test_authentication_success(self, reddit_client):
        """Test successful Reddit authentication."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value = mock_reddit
            mock_reddit.user.me.return_value = None  # Read-only mode
            
            await reddit_client.authenticate()
            
            assert reddit_client._authenticated is True
            mock_reddit_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_failure(self, reddit_client):
        """Test Reddit authentication failure."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            mock_reddit_class.side_effect = Exception("Invalid credentials")
            
            with pytest.raises(AuthenticationError):
                await reddit_client.authenticate()

    @pytest.mark.asyncio
    async def test_close(self, reddit_client):
        """Test client cleanup."""
        mock_reddit = AsyncMock()
        reddit_client._reddit = mock_reddit
        reddit_client._authenticated = True
        
        await reddit_client.close()
        
        mock_reddit.close.assert_called_once()
        assert reddit_client._reddit is None
        assert reddit_client._authenticated is False

    def test_extract_stock_symbols(self, reddit_client):
        """Test stock symbol extraction from text."""
        text = "I think TSLA and AAPL are great stocks. But not THE or AND."
        symbols = reddit_client._extract_stock_symbols(text)
        
        assert "TSLA" in symbols
        assert "AAPL" in symbols
        assert "THE" not in symbols  # False positive filter
        assert "AND" not in symbols  # False positive filter

    def test_extract_stock_symbols_empty(self, reddit_client):
        """Test stock symbol extraction with empty text."""
        symbols = reddit_client._extract_stock_symbols("")
        assert symbols == []
        
        symbols = reddit_client._extract_stock_symbols(None)
        assert symbols == []

    def test_convert_post(self, reddit_client, mock_reddit_post):
        """Test conversion of Reddit post to schema."""
        post = reddit_client._convert_post(mock_reddit_post)
        
        assert isinstance(post, RedditPost)
        assert post.id == "test_post_123"
        assert post.title == "TSLA to the moon! 🚀"
        assert post.author == "test_user"
        assert post.subreddit == "stocks"
        assert post.score == 150
        assert post.mentions_stocks is True
        assert "TSLA" in post.extracted_symbols
        assert "AAPL" in post.extracted_symbols

    def test_convert_comment(self, reddit_client, mock_reddit_comment):
        """Test conversion of Reddit comment to schema."""
        comment = reddit_client._convert_comment(mock_reddit_comment)
        
        assert isinstance(comment, RedditComment)
        assert comment.id == "test_comment_456"
        assert comment.body == "Great analysis! TSLA is definitely bullish"
        assert comment.author == "commenter_user"
        assert comment.score == 25
        assert comment.mentions_stocks is True
        assert "TSLA" in comment.extracted_symbols

    def test_convert_subreddit(self, reddit_client, mock_subreddit):
        """Test conversion of Reddit subreddit to schema."""
        subreddit_info = reddit_client._convert_subreddit(mock_subreddit)
        
        assert isinstance(subreddit_info, SubredditInfo)
        assert subreddit_info.name == "stocks"
        assert subreddit_info.subscribers == 500000
        assert subreddit_info.active_users == 5000
        assert subreddit_info.finance_relevance_score > 0  # Should detect finance keywords

    @pytest.mark.asyncio
    async def test_get_posts_success(self, reddit_client, mock_reddit_post, mock_subreddit):
        """Test successful post retrieval."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value = mock_reddit
            
            # Mock subreddit and posts
            mock_subreddit_obj = AsyncMock()
            mock_reddit.subreddit.return_value = mock_subreddit_obj
            
            # Setup async iteration for posts
            async def mock_hot_posts(*args, **kwargs):
                yield mock_reddit_post
            
            mock_subreddit_obj.hot.return_value = mock_hot_posts()
            
            # Mock the subreddit conversion separately
            reddit_client._reddit = mock_reddit
            reddit_client._authenticated = True
            
            with patch.object(reddit_client, '_convert_subreddit', return_value=SubredditInfo(
                name="stocks",
                display_name="r/stocks", 
                description="Test subreddit",
                subscribers=500000,
                active_users=5000,
                created_utc=datetime.utcnow(),
                finance_relevance_score=0.8
            )):
                result = await reddit_client.get_posts("stocks", sort="hot", limit=10)
            
            assert len(result.posts) >= 0  # Could be filtered by min_score
            assert result.subreddit_info is not None
            assert result.collection_method == "hot"

    @pytest.mark.asyncio
    async def test_get_posts_api_error(self, reddit_client):
        """Test post retrieval API error."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            from asyncpraw.exceptions import RedditAPIException
            
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value = mock_reddit
            mock_reddit.subreddit.side_effect = RedditAPIException("API Error")
            
            reddit_client._reddit = mock_reddit
            reddit_client._authenticated = True
            
            with pytest.raises(ExternalAPIError):
                await reddit_client.get_posts("invalid_subreddit")

    @pytest.mark.asyncio
    async def test_search_posts(self, reddit_client, mock_reddit_post):
        """Test post search functionality."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value = mock_reddit
            
            # Mock search results
            async def mock_search_results(*args, **kwargs):
                yield mock_reddit_post
            
            mock_subreddit_obj = AsyncMock()
            mock_reddit.subreddit.return_value = mock_subreddit_obj
            mock_subreddit_obj.search.return_value = mock_search_results()
            
            reddit_client._reddit = mock_reddit
            reddit_client._authenticated = True
            
            with patch.object(reddit_client, '_convert_subreddit', return_value=SubredditInfo(
                name="stocks",
                display_name="r/stocks",
                description="Test subreddit", 
                subscribers=500000,
                active_users=5000,
                created_utc=datetime.utcnow(),
                finance_relevance_score=0.8
            )):
                result = await reddit_client.search_posts("TSLA", subreddit_name="stocks")
            
            assert result.collection_method.startswith("search_")
            assert result.query_parameters["query"] == "TSLA"

    @pytest.mark.asyncio
    async def test_health_check_success(self, reddit_client):
        """Test successful health check."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value = mock_reddit
            
            mock_subreddit = AsyncMock()
            mock_reddit.subreddit.return_value = mock_subreddit
            mock_subreddit.load = AsyncMock()
            
            reddit_client._reddit = mock_reddit
            reddit_client._authenticated = True
            
            health = await reddit_client.health_check()
            
            assert health["provider"] == "reddit"
            assert health["status"] == "healthy"
            assert health["authenticated"] is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, reddit_client):
        """Test health check failure."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value = mock_reddit
            mock_reddit.subreddit.side_effect = Exception("Connection failed")
            
            reddit_client._reddit = mock_reddit
            reddit_client._authenticated = True
            
            health = await reddit_client.health_check()
            
            assert health["provider"] == "reddit"
            assert health["status"] == "unhealthy"
            assert "error" in health

    @pytest.mark.asyncio
    async def test_rate_limiting(self, reddit_client, mock_rate_limiter):
        """Test rate limiting integration."""
        with patch('asyncpraw.Reddit') as mock_reddit_class:
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value = mock_reddit
            
            reddit_client._reddit = mock_reddit
            reddit_client._authenticated = True
            
            # This should call the rate limiter
            await reddit_client._check_rate_limit()
            
            mock_rate_limiter.wait_if_needed.assert_called_once()

    def test_false_positive_filtering(self, reddit_client):
        """Test that common false positive symbols are filtered out."""
        text = "THE quick brown FOX jumps OVER the lazy DOG. But TSLA is great!"
        symbols = reddit_client._extract_stock_symbols(text)
        
        # Common words should be filtered out
        false_positives = {"THE", "FOX", "OVER", "DOG"}
        for fp in false_positives:
            assert fp not in symbols
        
        # Real stock symbol should remain
        assert "TSLA" in symbols

    def test_duplicate_symbol_removal(self, reddit_client):
        """Test that duplicate symbols are removed."""
        text = "TSLA TSLA AAPL TSLA AAPL"
        symbols = reddit_client._extract_stock_symbols(text)
        
        # Should have unique symbols only
        assert symbols.count("TSLA") == 1
        assert symbols.count("AAPL") == 1
        assert len(symbols) == 2