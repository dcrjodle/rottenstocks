"""
Reddit API client implementation using AsyncPRAW.

Provides async Reddit API access with rate limiting, error handling,
and integration with the existing external API infrastructure.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, AsyncGenerator
from urllib.parse import urljoin

import asyncpraw
from asyncpraw.exceptions import RedditAPIException, ClientException
from structlog import get_logger

from app.core.config import get_settings
from app.external_apis.base.rate_limiter import RateLimiter
from app.external_apis.base.exceptions import (
    AuthenticationError,
    ExternalAPIError,
    RateLimitExceededError,
    ValidationError,
)
from app.external_apis.reddit.schemas import (
    RedditPost,
    RedditComment,
    RedditUser,
    SubredditInfo,
    RedditSearchResult,
)

logger = get_logger(__name__)
settings = get_settings()


class RedditClient:
    """
    Async Reddit API client with rate limiting and error handling.
    
    Integrates AsyncPRAW with the existing external API infrastructure
    for collecting financial discussions from Reddit.
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize Reddit client.
        
        Args:
            rate_limiter: Optional rate limiter instance
        """
        self.rate_limiter = rate_limiter
        self._reddit: Optional[asyncpraw.Reddit] = None
        self._authenticated = False
        
        # Stock symbol regex pattern
        self.stock_symbol_pattern = re.compile(
            r'\b([A-Z]{1,5})\b',  # 1-5 uppercase letters
            re.IGNORECASE
        )
        
        # Common false positives to filter out
        self.false_positive_symbols = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD',
            'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS',
            'HOW', 'ITS', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID',
            'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE', 'WAY', 'WIN', 'YES',
            'BAD', 'BIG', 'BOX', 'EAT', 'END', 'FAR', 'FEW', 'GOT', 'HOT', 'JOB',
            'LOT', 'LOW', 'MAN', 'MAY', 'OFF', 'OWN', 'PAY', 'RUN', 'SET', 'TRY',
            'CEO', 'CTO', 'CFO', 'USA', 'USD', 'API', 'IPO', 'ETF', 'ESG', 'SEC',
            'IRS', 'GDP', 'CPI', 'PDF', 'FAQ', 'AMA', 'TIL', 'ELI', 'IMO', 'LOL',
            'OMG', 'WTF', 'BRB', 'FYI', 'ASAP', 'YOLO', 'HODL', 'MOON', 'LAMBO'
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def authenticate(self) -> None:
        """
        Authenticate with Reddit API.
        
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            self._reddit = asyncpraw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
                # Read-only mode - no username/password needed
            )
            
            # Test authentication by getting user info
            user = await self._reddit.user.me()
            if user is None:
                # We're in read-only mode, which is fine
                logger.info("Reddit client authenticated in read-only mode")
            else:
                logger.info(f"Reddit client authenticated as user: {user.name}")
                
            self._authenticated = True
            
        except Exception as e:
            logger.error(f"Reddit authentication failed: {e}")
            raise AuthenticationError(
                f"Failed to authenticate with Reddit: {e}",
                provider="reddit"
            )

    async def close(self) -> None:
        """Close Reddit client."""
        if self._reddit:
            await self._reddit.close()
            self._reddit = None
            self._authenticated = False

    async def _check_rate_limit(self) -> None:
        """Check rate limit before making requests."""
        if self.rate_limiter:
            try:
                await self.rate_limiter.wait_if_needed()
            except Exception as e:
                logger.error(f"Rate limiting error: {e}")
                raise RateLimitExceededError(
                    f"Rate limit exceeded: {e}",
                    provider="reddit"
                )

    def _extract_stock_symbols(self, text: str) -> List[str]:
        """
        Extract potential stock symbols from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of potential stock symbols
        """
        if not text:
            return []
        
        # Find all potential symbols
        matches = self.stock_symbol_pattern.findall(text.upper())
        
        # Filter out common false positives
        symbols = [
            symbol for symbol in matches 
            if symbol not in self.false_positive_symbols
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_symbols = []
        for symbol in symbols:
            if symbol not in seen:
                seen.add(symbol)
                unique_symbols.append(symbol)
        
        return unique_symbols

    def _convert_post(self, reddit_post: asyncpraw.models.Submission) -> RedditPost:
        """
        Convert Reddit post to our schema.
        
        Args:
            reddit_post: AsyncPRAW submission object
            
        Returns:
            RedditPost schema object
        """
        # Extract stock symbols from title and text
        full_text = f"{reddit_post.title} {reddit_post.selftext}"
        extracted_symbols = self._extract_stock_symbols(full_text)
        
        return RedditPost(
            id=reddit_post.id,
            title=reddit_post.title,
            selftext=reddit_post.selftext or "",
            author=reddit_post.author.name if reddit_post.author else None,
            subreddit=reddit_post.subreddit.display_name,
            score=reddit_post.score,
            upvote_ratio=reddit_post.upvote_ratio,
            num_comments=reddit_post.num_comments,
            created_utc=datetime.utcfromtimestamp(reddit_post.created_utc),
            url=reddit_post.url,
            permalink=urljoin("https://reddit.com", reddit_post.permalink),
            flair_text=reddit_post.link_flair_text,
            is_original_content=reddit_post.is_original_content or False,
            is_self=reddit_post.is_self,
            is_video=reddit_post.is_video or False,
            is_pinned=reddit_post.pinned or False,
            is_locked=reddit_post.locked or False,
            is_archived=reddit_post.archived or False,
            mentions_stocks=bool(extracted_symbols),
            extracted_symbols=extracted_symbols,
        )

    def _convert_comment(self, reddit_comment: asyncpraw.models.Comment) -> RedditComment:
        """
        Convert Reddit comment to our schema.
        
        Args:
            reddit_comment: AsyncPRAW comment object
            
        Returns:
            RedditComment schema object
        """
        # Extract stock symbols from comment text
        extracted_symbols = self._extract_stock_symbols(reddit_comment.body)
        
        return RedditComment(
            id=reddit_comment.id,
            body=reddit_comment.body,
            author=reddit_comment.author.name if reddit_comment.author else None,
            score=reddit_comment.score,
            created_utc=datetime.utcfromtimestamp(reddit_comment.created_utc),
            permalink=urljoin("https://reddit.com", reddit_comment.permalink),
            parent_id=reddit_comment.parent_id,
            depth=reddit_comment.depth or 0,
            is_edited=reddit_comment.edited is not False,
            is_distinguished=reddit_comment.distinguished is not None,
            mentions_stocks=bool(extracted_symbols),
            extracted_symbols=extracted_symbols,
        )

    def _convert_user(self, reddit_user: asyncpraw.models.Redditor) -> RedditUser:
        """
        Convert Reddit user to our schema.
        
        Args:
            reddit_user: AsyncPRAW redditor object
            
        Returns:
            RedditUser schema object
        """
        # Calculate account age
        account_age_days = None
        if hasattr(reddit_user, 'created_utc') and reddit_user.created_utc:
            created_date = datetime.utcfromtimestamp(reddit_user.created_utc)
            account_age_days = (datetime.utcnow() - created_date).days
        
        return RedditUser(
            username=reddit_user.name,
            karma_comment=getattr(reddit_user, 'comment_karma', 0),
            karma_link=getattr(reddit_user, 'link_karma', 0),
            account_age_days=account_age_days,
            is_verified=getattr(reddit_user, 'is_verified', False),
            is_premium=getattr(reddit_user, 'is_premium', False),
        )

    def _convert_subreddit(self, reddit_subreddit: asyncpraw.models.Subreddit) -> SubredditInfo:
        """
        Convert Reddit subreddit to our schema.
        
        Args:
            reddit_subreddit: AsyncPRAW subreddit object
            
        Returns:
            SubredditInfo schema object
        """
        # Calculate finance relevance score
        finance_keywords = {
            'stock', 'trading', 'invest', 'finance', 'money', 'market',
            'economy', 'business', 'wall', 'street', 'security'
        }
        
        description = reddit_subreddit.public_description or ""
        description_lower = description.lower()
        subreddit_name_lower = reddit_subreddit.display_name.lower()
        
        # Check for finance keywords in name and description
        finance_matches = sum(1 for keyword in finance_keywords 
                            if keyword in description_lower or keyword in subreddit_name_lower)
        finance_relevance = min(finance_matches / len(finance_keywords), 1.0)
        
        return SubredditInfo(
            name=reddit_subreddit.display_name,
            display_name=reddit_subreddit.display_name_prefixed,
            description=description,
            subscribers=reddit_subreddit.subscribers or 0,
            active_users=reddit_subreddit.active_user_count or 0,
            created_utc=datetime.utcfromtimestamp(reddit_subreddit.created_utc),
            is_over_18=reddit_subreddit.over18 or False,
            is_quarantined=reddit_subreddit.quarantine or False,
            is_private=reddit_subreddit.subreddit_type == "private",
            finance_relevance_score=finance_relevance,
        )

    async def get_subreddit_info(self, subreddit_name: str) -> SubredditInfo:
        """
        Get subreddit information.
        
        Args:
            subreddit_name: Name of the subreddit
            
        Returns:
            SubredditInfo object
            
        Raises:
            ExternalAPIError: If subreddit cannot be accessed
        """
        if not self._authenticated:
            await self.authenticate()
        
        await self._check_rate_limit()
        
        try:
            subreddit = await self._reddit.subreddit(subreddit_name)
            await subreddit.load()  # Load subreddit data
            return self._convert_subreddit(subreddit)
            
        except RedditAPIException as e:
            logger.error(f"Reddit API error getting subreddit {subreddit_name}: {e}")
            raise ExternalAPIError(
                f"Failed to get subreddit info: {e}",
                provider="reddit"
            )
        except Exception as e:
            logger.error(f"Error getting subreddit {subreddit_name}: {e}")
            raise ExternalAPIError(
                f"Failed to get subreddit info: {e}",
                provider="reddit"
            )

    async def get_posts(
        self,
        subreddit_name: str,
        sort: str = "hot",
        limit: int = 100,
        time_filter: str = "day",
        min_score: int = 5
    ) -> RedditSearchResult:
        """
        Get posts from a subreddit.
        
        Args:
            subreddit_name: Name of the subreddit
            sort: Sort method ('hot', 'new', 'top', 'rising')
            limit: Maximum number of posts to retrieve
            time_filter: Time filter for 'top' sort ('hour', 'day', 'week', 'month', 'year', 'all')
            min_score: Minimum score for posts
            
        Returns:
            RedditSearchResult with posts
            
        Raises:
            ExternalAPIError: If posts cannot be retrieved
        """
        if not self._authenticated:
            await self.authenticate()
        
        await self._check_rate_limit()
        
        try:
            subreddit = await self._reddit.subreddit(subreddit_name)
            await subreddit.load()  # Load subreddit data
            
            # Get subreddit info
            subreddit_info = self._convert_subreddit(subreddit)
            
            # Get posts based on sort method
            if sort == "hot":
                posts_iter = subreddit.hot(limit=limit)
            elif sort == "new":
                posts_iter = subreddit.new(limit=limit)
            elif sort == "top":
                posts_iter = subreddit.top(time_filter=time_filter, limit=limit)
            elif sort == "rising":
                posts_iter = subreddit.rising(limit=limit)
            else:
                raise ValidationError(f"Invalid sort method: {sort}", provider="reddit")
            
            # Collect posts
            posts = []
            async for post in posts_iter:
                # Skip posts below minimum score
                if post.score < min_score:
                    continue
                
                # Skip pinned posts unless specifically requested
                if post.pinned and sort != "top":
                    continue
                
                converted_post = self._convert_post(post)
                posts.append(converted_post)
            
            return RedditSearchResult(
                posts=posts,
                subreddit_info=subreddit_info,
                collection_method=sort,
                query_parameters={
                    "subreddit": subreddit_name,
                    "sort": sort,
                    "limit": limit,
                    "time_filter": time_filter,
                    "min_score": min_score,
                }
            )
            
        except RedditAPIException as e:
            logger.error(f"Reddit API error getting posts from {subreddit_name}: {e}")
            raise ExternalAPIError(
                f"Failed to get posts: {e}",
                provider="reddit"
            )
        except Exception as e:
            logger.error(f"Error getting posts from {subreddit_name}: {e}")
            raise ExternalAPIError(
                f"Failed to get posts: {e}",
                provider="reddit"
            )

    async def get_post_comments(
        self,
        post_id: str,
        limit: int = 50,
        sort: str = "top",
        min_score: int = 1
    ) -> List[RedditComment]:
        """
        Get comments for a specific post.
        
        Args:
            post_id: Reddit post ID
            limit: Maximum number of comments to retrieve
            sort: Sort method ('top', 'new', 'best', 'controversial')
            min_score: Minimum score for comments
            
        Returns:
            List of RedditComment objects
            
        Raises:
            ExternalAPIError: If comments cannot be retrieved
        """
        if not self._authenticated:
            await self.authenticate()
        
        await self._check_rate_limit()
        
        try:
            submission = await self._reddit.submission(id=post_id)
            
            # Set comment sort
            submission.comment_sort = sort
            
            # Expand comment tree
            await submission.comments.replace_more(limit=32)
            
            # Collect comments
            comments = []
            for comment in submission.comments.list():
                if hasattr(comment, 'body') and comment.score >= min_score:
                    converted_comment = self._convert_comment(comment)
                    comments.append(converted_comment)
                    
                    if len(comments) >= limit:
                        break
            
            return comments
            
        except RedditAPIException as e:
            logger.error(f"Reddit API error getting comments for post {post_id}: {e}")
            raise ExternalAPIError(
                f"Failed to get comments: {e}",
                provider="reddit"
            )
        except Exception as e:
            logger.error(f"Error getting comments for post {post_id}: {e}")
            raise ExternalAPIError(
                f"Failed to get comments: {e}",
                provider="reddit"
            )

    async def search_posts(
        self,
        query: str,
        subreddit_name: Optional[str] = None,
        sort: str = "relevance",
        time_filter: str = "week",
        limit: int = 100,
        min_score: int = 5
    ) -> RedditSearchResult:
        """
        Search for posts by query.
        
        Args:
            query: Search query
            subreddit_name: Optional subreddit to limit search to
            sort: Sort method ('relevance', 'hot', 'top', 'new', 'comments')
            time_filter: Time filter ('hour', 'day', 'week', 'month', 'year', 'all')
            limit: Maximum number of posts to retrieve
            min_score: Minimum score for posts
            
        Returns:
            RedditSearchResult with matching posts
            
        Raises:
            ExternalAPIError: If search fails
        """
        if not self._authenticated:
            await self.authenticate()
        
        await self._check_rate_limit()
        
        try:
            if subreddit_name:
                subreddit = await self._reddit.subreddit(subreddit_name)
                await subreddit.load()  # Load subreddit data
                search_results = subreddit.search(
                    query=query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit
                )
                subreddit_info = self._convert_subreddit(subreddit)
            else:
                search_results = self._reddit.subreddit("all").search(
                    query=query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit
                )
                subreddit_info = None
            
            # Collect posts
            posts = []
            async for post in search_results:
                if post.score >= min_score:
                    converted_post = self._convert_post(post)
                    posts.append(converted_post)
            
            return RedditSearchResult(
                posts=posts,
                subreddit_info=subreddit_info,
                collection_method=f"search_{sort}",
                query_parameters={
                    "query": query,
                    "subreddit": subreddit_name,
                    "sort": sort,
                    "time_filter": time_filter,
                    "limit": limit,
                    "min_score": min_score,
                }
            )
            
        except RedditAPIException as e:
            logger.error(f"Reddit API error searching for '{query}': {e}")
            raise ExternalAPIError(
                f"Failed to search posts: {e}",
                provider="reddit"
            )
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            raise ExternalAPIError(
                f"Failed to search posts: {e}",
                provider="reddit"
            )

    async def get_finance_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit_per_subreddit: int = 50,
        min_score: int = 10,
        sort: str = "hot"
    ) -> RedditSearchResult:
        """
        Get finance-related posts from multiple subreddits.
        
        Args:
            subreddits: List of subreddit names (uses default finance subreddits if None)
            limit_per_subreddit: Maximum posts per subreddit
            min_score: Minimum score for posts
            sort: Sort method
            
        Returns:
            Combined RedditSearchResult with finance posts
            
        Raises:
            ExternalAPIError: If collection fails
        """
        if subreddits is None:
            subreddits = settings.REDDIT_SUBREDDITS
        
        all_posts = []
        all_subreddit_info = []
        
        for subreddit_name in subreddits:
            try:
                result = await self.get_posts(
                    subreddit_name=subreddit_name,
                    sort=sort,
                    limit=limit_per_subreddit,
                    min_score=min_score
                )
                
                # Filter for finance-related posts
                finance_posts = [post for post in result.posts if post.is_finance_related]
                all_posts.extend(finance_posts)
                
                if result.subreddit_info:
                    all_subreddit_info.append(result.subreddit_info)
                
                logger.info(
                    f"Collected {len(finance_posts)} finance posts from r/{subreddit_name}"
                )
                
            except Exception as e:
                logger.warning(f"Failed to get posts from r/{subreddit_name}: {e}")
                continue
        
        # Sort all posts by score
        all_posts.sort(key=lambda x: x.score, reverse=True)
        
        return RedditSearchResult(
            posts=all_posts,
            collection_method=f"multi_subreddit_{sort}",
            query_parameters={
                "subreddits": subreddits,
                "limit_per_subreddit": limit_per_subreddit,
                "min_score": min_score,
                "sort": sort,
            }
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Reddit API.
        
        Returns:
            Health check results
        """
        try:
            if not self._authenticated:
                await self.authenticate()
            
            # Try to get a simple subreddit
            subreddit = await self._reddit.subreddit("python")
            await subreddit.load()
            
            return {
                "provider": "reddit",
                "status": "healthy",
                "authenticated": self._authenticated,
                "base_url": "https://www.reddit.com",
                "rate_limit_configured": self.rate_limiter is not None,
            }
            
        except Exception as e:
            return {
                "provider": "reddit",
                "status": "unhealthy",
                "error": str(e),
                "authenticated": self._authenticated,
                "base_url": "https://www.reddit.com",
            }