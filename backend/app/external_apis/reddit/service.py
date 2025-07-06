"""
Reddit service layer for financial data collection.

High-level service for collecting and processing Reddit data
for financial sentiment analysis and stock discussions.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from structlog import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import get_settings
from app.external_apis.base.rate_limiter import RateLimiter
from app.external_apis.reddit.client import RedditClient
from app.external_apis.reddit.schemas import (
    RedditPost,
    RedditComment,
    RedditSearchResult,
    SubredditInfo,
)
from app.db.models.social_post import SocialPost, Platform
from app.db.models.stock import Stock

logger = get_logger(__name__)
settings = get_settings()


class RedditService:
    """
    High-level Reddit service for financial data collection.
    
    Provides methods for collecting, filtering, and processing Reddit content
    for financial sentiment analysis and stock discussion tracking.
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize Reddit service.
        
        Args:
            db_session: Optional database session for persistence
        """
        self.db_session = db_session
        import redis.asyncio as redis
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.rate_limiter = RateLimiter(
            redis_client=redis_client,
            provider="reddit",
            requests_per_minute=settings.REDDIT_RATE_LIMIT_PER_MINUTE
        )
        self.client = RedditClient(rate_limiter=self.rate_limiter)
        
        # Stock symbol validation cache
        self._valid_symbols_cache: Set[str] = set()
        self._cache_updated: Optional[datetime] = None
        self._cache_duration = timedelta(hours=24)  # Refresh daily

    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()

    async def _refresh_stock_symbols_cache(self) -> None:
        """Refresh the cache of valid stock symbols from database."""
        if (self._cache_updated is None or 
            datetime.utcnow() - self._cache_updated > self._cache_duration):
            
            if self.db_session:
                try:
                    # Get all valid stock symbols from database
                    result = await self.db_session.execute(
                        text("SELECT symbol FROM stocks WHERE is_active = true")
                    )
                    symbols = {row[0] for row in result.fetchall()}
                    
                    self._valid_symbols_cache = symbols
                    self._cache_updated = datetime.utcnow()
                    
                    logger.info(f"Refreshed stock symbols cache with {len(symbols)} symbols")
                    
                except Exception as e:
                    logger.warning(f"Failed to refresh stock symbols cache: {e}")

    def _validate_stock_symbols(self, symbols: List[str]) -> List[str]:
        """
        Validate stock symbols against known stocks.
        
        Args:
            symbols: List of potential stock symbols
            
        Returns:
            List of validated stock symbols
        """
        if not self._valid_symbols_cache:
            # If cache is empty, return all symbols (fallback behavior)
            return symbols
        
        return [symbol for symbol in symbols if symbol in self._valid_symbols_cache]

    async def get_finance_discussions(
        self,
        subreddits: Optional[List[str]] = None,
        limit_per_subreddit: int = 50,
        min_score: int = 10,
        min_quality_score: float = 0.3,
        time_filter: str = "day"
    ) -> RedditSearchResult:
        """
        Get high-quality finance discussions from Reddit.
        
        Args:
            subreddits: List of subreddit names (uses default if None)
            limit_per_subreddit: Maximum posts per subreddit
            min_score: Minimum post score
            min_quality_score: Minimum quality score (0-1)
            time_filter: Time filter for posts
            
        Returns:
            RedditSearchResult with filtered finance discussions
        """
        await self._refresh_stock_symbols_cache()
        
        if subreddits is None:
            subreddits = settings.REDDIT_SUBREDDITS
        
        logger.info(f"Collecting finance discussions from {len(subreddits)} subreddits")
        
        # Collect posts from all subreddits
        result = await self.client.get_finance_posts(
            subreddits=subreddits,
            limit_per_subreddit=limit_per_subreddit,
            min_score=min_score,
            sort="hot"
        )
        
        # Filter posts by quality score
        high_quality_posts = [
            post for post in result.posts 
            if post.quality_score >= min_quality_score
        ]
        
        # Validate and filter stock symbols
        for post in high_quality_posts:
            validated_symbols = self._validate_stock_symbols(post.extracted_symbols)
            post.extracted_symbols = validated_symbols
            post.mentions_stocks = bool(validated_symbols)
        
        # Filter out posts with no valid stock symbols if we have a cache
        if self._valid_symbols_cache:
            stock_related_posts = [
                post for post in high_quality_posts 
                if post.mentions_stocks
            ]
        else:
            stock_related_posts = high_quality_posts
        
        logger.info(
            f"Filtered {len(result.posts)} posts to {len(stock_related_posts)} "
            f"high-quality stock discussions"
        )
        
        return RedditSearchResult(
            posts=stock_related_posts,
            collection_method="finance_discussions",
            query_parameters={
                "subreddits": subreddits,
                "limit_per_subreddit": limit_per_subreddit,
                "min_score": min_score,
                "min_quality_score": min_quality_score,
                "time_filter": time_filter,
            }
        )

    async def get_stock_discussions(
        self,
        symbol: str,
        subreddits: Optional[List[str]] = None,
        limit: int = 100,
        time_filter: str = "week",
        min_score: int = 5
    ) -> RedditSearchResult:
        """
        Get discussions about a specific stock symbol.
        
        Args:
            symbol: Stock symbol to search for
            subreddits: List of subreddit names (uses default if None)
            limit: Maximum number of posts to retrieve
            time_filter: Time filter for search
            min_score: Minimum post score
            
        Returns:
            RedditSearchResult with stock-specific discussions
        """
        if subreddits is None:
            subreddits = settings.REDDIT_SUBREDDITS
        
        logger.info(f"Searching for {symbol} discussions in {len(subreddits)} subreddits")
        
        all_posts = []
        all_comments = []
        
        # Search each subreddit for the symbol
        for subreddit_name in subreddits:
            try:
                # Search for posts containing the symbol
                search_queries = [
                    f"${symbol}",  # Common format: $TSLA
                    f"{symbol}",   # Direct symbol: TSLA
                    f"ticker:{symbol}",  # Ticker format
                ]
                
                for query in search_queries:
                    result = await self.client.search_posts(
                        query=query,
                        subreddit_name=subreddit_name,
                        sort="hot",
                        time_filter=time_filter,
                        limit=limit // len(search_queries),
                        min_score=min_score
                    )
                    
                    # Filter posts that actually mention the symbol
                    relevant_posts = [
                        post for post in result.posts
                        if symbol in post.extracted_symbols
                    ]
                    
                    all_posts.extend(relevant_posts)
                    
                    # Get comments for top posts
                    for post in relevant_posts[:5]:  # Top 5 posts per query
                        try:
                            comments = await self.client.get_post_comments(
                                post_id=post.id,
                                limit=20,
                                min_score=3
                            )
                            
                            # Filter comments that mention the symbol
                            relevant_comments = [
                                comment for comment in comments
                                if symbol in comment.extracted_symbols
                            ]
                            
                            all_comments.extend(relevant_comments)
                            
                        except Exception as e:
                            logger.warning(f"Failed to get comments for post {post.id}: {e}")
                            continue
                
            except Exception as e:
                logger.warning(f"Failed to search r/{subreddit_name} for {symbol}: {e}")
                continue
        
        # Remove duplicates and sort by score
        unique_posts = {post.id: post for post in all_posts}
        sorted_posts = sorted(unique_posts.values(), key=lambda x: x.score, reverse=True)
        
        unique_comments = {comment.id: comment for comment in all_comments}
        sorted_comments = sorted(unique_comments.values(), key=lambda x: x.score, reverse=True)
        
        logger.info(
            f"Found {len(sorted_posts)} posts and {len(sorted_comments)} comments "
            f"discussing {symbol}"
        )
        
        return RedditSearchResult(
            posts=sorted_posts,
            comments=sorted_comments,
            collection_method="stock_discussions",
            query_parameters={
                "symbol": symbol,
                "subreddits": subreddits,
                "limit": limit,
                "time_filter": time_filter,
                "min_score": min_score,
            }
        )

    async def get_trending_stocks(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 200,
        time_filter: str = "day",
        min_mentions: int = 3
    ) -> Dict[str, Dict]:
        """
        Get trending stock symbols based on Reddit discussions.
        
        Args:
            subreddits: List of subreddit names (uses default if None)
            limit: Maximum posts to analyze
            time_filter: Time filter for posts
            min_mentions: Minimum mentions to be considered trending
            
        Returns:
            Dictionary with stock symbols and their trend data
        """
        if subreddits is None:
            subreddits = settings.REDDIT_SUBREDDITS
        
        logger.info(f"Analyzing trending stocks from {len(subreddits)} subreddits")
        
        # Get recent finance discussions
        result = await self.get_finance_discussions(
            subreddits=subreddits,
            limit_per_subreddit=limit // len(subreddits),
            min_score=10,
            time_filter=time_filter
        )
        
        # Count symbol mentions with metadata
        symbol_data = defaultdict(lambda: {
            'mention_count': 0,
            'total_score': 0,
            'posts': [],
            'avg_score': 0.0,
            'avg_quality': 0.0,
            'subreddits': set(),
            'first_seen': None,
            'last_seen': None,
        })
        
        for post in result.posts:
            for symbol in post.extracted_symbols:
                data = symbol_data[symbol]
                data['mention_count'] += 1
                data['total_score'] += post.score
                data['posts'].append(post)
                data['subreddits'].add(post.subreddit)
                
                # Track timing
                if data['first_seen'] is None or post.created_utc < data['first_seen']:
                    data['first_seen'] = post.created_utc
                if data['last_seen'] is None or post.created_utc > data['last_seen']:
                    data['last_seen'] = post.created_utc
        
        # Calculate averages and filter
        trending_stocks = {}
        for symbol, data in symbol_data.items():
            if data['mention_count'] >= min_mentions:
                data['avg_score'] = data['total_score'] / data['mention_count']
                data['avg_quality'] = sum(post.quality_score for post in data['posts']) / len(data['posts'])
                data['subreddits'] = list(data['subreddits'])  # Convert set to list
                
                # Calculate trend score
                trend_score = (
                    data['mention_count'] * 0.4 +  # Frequency
                    min(data['avg_score'] / 100, 1.0) * 0.3 +  # Average upvotes
                    data['avg_quality'] * 0.2 +  # Quality
                    min(len(data['subreddits']) / 5, 1.0) * 0.1  # Subreddit diversity
                )
                
                data['trend_score'] = trend_score
                trending_stocks[symbol] = data
        
        # Sort by trend score
        trending_stocks = dict(sorted(
            trending_stocks.items(),
            key=lambda x: x[1]['trend_score'],
            reverse=True
        ))
        
        logger.info(f"Found {len(trending_stocks)} trending stocks")
        
        return trending_stocks

    async def get_subreddit_sentiment(
        self,
        subreddit_name: str,
        limit: int = 100,
        time_filter: str = "day"
    ) -> Dict[str, any]:
        """
        Get overall sentiment analysis for a subreddit.
        
        Args:
            subreddit_name: Name of the subreddit
            limit: Maximum posts to analyze
            time_filter: Time filter for posts
            
        Returns:
            Dictionary with sentiment analysis results
        """
        logger.info(f"Analyzing sentiment for r/{subreddit_name}")
        
        # Get posts from the subreddit
        result = await self.client.get_posts(
            subreddit_name=subreddit_name,
            sort="hot",
            limit=limit,
            time_filter=time_filter,
            min_score=5
        )
        
        if not result.posts:
            return {
                "subreddit": subreddit_name,
                "sentiment": "neutral",
                "confidence": 0.0,
                "posts_analyzed": 0,
                "error": "No posts found"
            }
        
        # Calculate basic sentiment metrics
        total_posts = len(result.posts)
        finance_posts = sum(1 for post in result.posts if post.is_finance_related)
        avg_score = sum(post.score for post in result.posts) / total_posts
        avg_quality = sum(post.quality_score for post in result.posts) / total_posts
        
        # Count stock mentions
        all_symbols = []
        for post in result.posts:
            all_symbols.extend(post.extracted_symbols)
        
        unique_symbols = len(set(all_symbols))
        total_mentions = len(all_symbols)
        
        # Basic sentiment classification based on scores and engagement
        if avg_score > 50 and avg_quality > 0.6:
            sentiment = "positive"
            confidence = min(avg_quality, 1.0)
        elif avg_score < 10 or avg_quality < 0.3:
            sentiment = "negative"
            confidence = min(1.0 - avg_quality, 1.0)
        else:
            sentiment = "neutral"
            confidence = 0.5
        
        return {
            "subreddit": subreddit_name,
            "sentiment": sentiment,
            "confidence": confidence,
            "posts_analyzed": total_posts,
            "finance_posts": finance_posts,
            "finance_ratio": finance_posts / total_posts,
            "avg_score": avg_score,
            "avg_quality": avg_quality,
            "unique_symbols": unique_symbols,
            "total_mentions": total_mentions,
            "top_symbols": list(set(all_symbols))[:10],
            "analysis_time": datetime.utcnow().isoformat(),
            "subreddit_info": result.subreddit_info.dict() if result.subreddit_info else None,
        }

    async def save_posts_to_database(
        self,
        posts: List[RedditPost],
        comments: Optional[List[RedditComment]] = None
    ) -> Tuple[int, int]:
        """
        Save Reddit posts and comments to database.
        
        Args:
            posts: List of RedditPost objects to save
            comments: Optional list of RedditComment objects to save
            
        Returns:
            Tuple of (posts_saved, comments_saved)
        """
        if not self.db_session:
            raise ValueError("Database session not available")
        
        posts_saved = 0
        comments_saved = 0
        
        try:
            # Save posts
            for post in posts:
                try:
                    social_post = SocialPost(
                        external_id=post.id,
                        platform=Platform.REDDIT,
                        content=post.full_text,
                        author=post.author,
                        url=post.permalink,
                        created_at=post.created_utc,
                        score=post.score,
                        metadata={
                            "subreddit": post.subreddit,
                            "num_comments": post.num_comments,
                            "upvote_ratio": post.upvote_ratio,
                            "flair": post.flair_text,
                            "extracted_symbols": post.extracted_symbols,
                            "quality_score": post.quality_score,
                        }
                    )
                    
                    self.db_session.add(social_post)
                    posts_saved += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to save post {post.id}: {e}")
                    continue
            
            # Save comments
            if comments:
                for comment in comments:
                    try:
                        social_post = SocialPost(
                            external_id=comment.id,
                            platform=Platform.REDDIT,
                            content=comment.body,
                            author=comment.author,
                            url=comment.permalink,
                            created_at=comment.created_utc,
                            score=comment.score,
                            metadata={
                                "parent_id": comment.parent_id,
                                "depth": comment.depth,
                                "extracted_symbols": comment.extracted_symbols,
                                "quality_score": comment.quality_score,
                            }
                        )
                        
                        self.db_session.add(social_post)
                        comments_saved += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to save comment {comment.id}: {e}")
                        continue
            
            await self.db_session.commit()
            
            logger.info(f"Saved {posts_saved} posts and {comments_saved} comments to database")
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to save posts to database: {e}")
            raise
        
        return posts_saved, comments_saved

    async def health_check(self) -> Dict[str, any]:
        """
        Perform health check on Reddit service.
        
        Returns:
            Health check results
        """
        client_health = await self.client.health_check()
        
        return {
            "service": "reddit",
            "status": client_health["status"],
            "client_health": client_health,
            "rate_limiter": self.rate_limiter is not None,
            "database_session": self.db_session is not None,
            "cache_status": {
                "symbols_cached": len(self._valid_symbols_cache),
                "cache_updated": self._cache_updated.isoformat() if self._cache_updated else None,
            },
            "configured_subreddits": settings.REDDIT_SUBREDDITS,
        }