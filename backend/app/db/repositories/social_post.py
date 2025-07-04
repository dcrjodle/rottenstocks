"""
Social Post repository for database operations.

This module provides social post-specific database operations including
CRUD operations, sentiment analysis, and social media metrics.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.social_post import SocialPost, Platform, SentimentType
from ..exceptions import NotFoundError, ValidationError, DatabaseErrorHandler
from .base import BaseRepository

logger = logging.getLogger(__name__)


class SocialPostRepository(BaseRepository[SocialPost]):
    """Repository for social post-related database operations."""
    
    def get_model_class(self) -> type[SocialPost]:
        """Get the SocialPost model class."""
        return SocialPost
    
    def get_unique_fields(self) -> List[str]:
        """Get unique fields for SocialPost model."""
        return ["platform_post_id"]
    
    # Social post-specific queries
    
    async def get_by_stock(
        self, 
        stock_id: str,
        platform: Optional[Platform] = None,
        limit: Optional[int] = None
    ) -> List[SocialPost]:
        """
        Get social posts for a specific stock.
        
        Args:
            stock_id: Stock ID
            platform: Filter by platform (optional)
            limit: Maximum number of posts to return
        
        Returns:
            List of social posts for the stock
        """
        filters = {"stock_id": stock_id}
        if platform:
            filters["platform"] = platform
        
        return await self.filter(
            filters=filters,
            limit=limit,
            order_by="-posted_at",
            options=[selectinload(SocialPost.stock)]
        )
    
    async def get_by_platform(
        self, 
        platform: Platform,
        limit: Optional[int] = None
    ) -> List[SocialPost]:
        """
        Get posts by platform.
        
        Args:
            platform: Social media platform
            limit: Maximum number of posts to return
        
        Returns:
            List of posts from the platform
        """
        return await self.filter(
            filters={"platform": platform},
            limit=limit,
            order_by="-posted_at",
            options=[selectinload(SocialPost.stock)]
        )
    
    async def get_by_sentiment(
        self,
        sentiment_type: SentimentType,
        limit: Optional[int] = None
    ) -> List[SocialPost]:
        """
        Get posts by sentiment type.
        
        Args:
            sentiment_type: Sentiment type
            limit: Maximum number of posts to return
        
        Returns:
            List of posts with the sentiment
        """
        return await self.filter(
            filters={"sentiment_type": sentiment_type},
            limit=limit,
            order_by="-posted_at",
            options=[selectinload(SocialPost.stock)]
        )
    
    async def get_recent_posts(
        self, 
        days: int = 7,
        platform: Optional[Platform] = None,
        limit: Optional[int] = None
    ) -> List[SocialPost]:
        """
        Get recent posts within specified days.
        
        Args:
            days: Number of days to look back
            platform: Filter by platform (optional)
            limit: Maximum number of posts to return
        
        Returns:
            List of recent posts
        """
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        filters = {"posted_at": {"gte": threshold_date}}
        if platform:
            filters["platform"] = platform
        
        return await self.filter(
            filters=filters,
            limit=limit,
            order_by="-posted_at",
            options=[selectinload(SocialPost.stock)]
        )
    
    async def get_popular_posts(
        self,
        platform: Optional[Platform] = None,
        days: Optional[int] = None,
        limit: int = 20
    ) -> List[SocialPost]:
        """
        Get popular posts based on engagement metrics.
        
        Args:
            platform: Filter by platform (optional)
            days: Only consider posts from last N days (optional)
            limit: Number of posts to return
        
        Returns:
            List of popular posts ordered by engagement
        """
        async with DatabaseErrorHandler("Getting popular posts"):
            filters = []
            
            if platform:
                filters.append(SocialPost.platform == platform)
            
            if days:
                threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
                filters.append(SocialPost.posted_at >= threshold_date)
            
            # Order by engagement score (combination of upvotes, score, comments, shares)
            stmt = (
                select(SocialPost)
                .where(and_(*filters) if filters else True)
                .order_by(
                    (
                        func.coalesce(SocialPost.score, 0) +
                        func.coalesce(SocialPost.upvotes, 0) +
                        func.coalesce(SocialPost.comment_count, 0) +
                        func.coalesce(SocialPost.share_count, 0)
                    ).desc()
                )
                .limit(limit)
                .options(selectinload(SocialPost.stock))
            )
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
    
    async def search_posts(
        self, 
        query: str,
        platform: Optional[Platform] = None,
        limit: int = 50
    ) -> List[SocialPost]:
        """
        Search posts by content.
        
        Args:
            query: Search query
            platform: Filter by platform (optional)
            limit: Maximum number of results
        
        Returns:
            List of matching posts
        """
        async with DatabaseErrorHandler("Searching posts"):
            filters = [SocialPost.content.ilike(f"%{query}%")]
            
            if platform:
                filters.append(SocialPost.platform == platform)
            
            stmt = (
                select(SocialPost)
                .where(and_(*filters))
                .order_by(SocialPost.posted_at.desc())
                .limit(limit)
                .options(selectinload(SocialPost.stock))
            )
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_by_author(
        self,
        username: str,
        platform: Optional[Platform] = None,
        limit: Optional[int] = None
    ) -> List[SocialPost]:
        """
        Get posts by author username.
        
        Args:
            username: Author username
            platform: Filter by platform (optional)
            limit: Maximum number of posts to return
        
        Returns:
            List of posts by the author
        """
        filters = {"author_username": username}
        if platform:
            filters["platform"] = platform
        
        return await self.filter(
            filters=filters,
            limit=limit,
            order_by="-posted_at",
            options=[selectinload(SocialPost.stock)]
        )
    
    # Sentiment analysis operations
    
    async def get_sentiment_summary(
        self,
        stock_id: Optional[str] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get sentiment analysis summary.
        
        Args:
            stock_id: Filter by stock ID (optional)
            days: Only consider posts from last N days (optional)
        
        Returns:
            Sentiment summary dictionary
        """
        async with DatabaseErrorHandler("Getting sentiment summary"):
            filters = []
            
            if stock_id:
                filters.append(SocialPost.stock_id == stock_id)
            
            if days:
                threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
                filters.append(SocialPost.posted_at >= threshold_date)
            
            # Overall sentiment distribution
            sentiment_dist = await self.session.execute(
                select(
                    SocialPost.sentiment_type,
                    func.count(SocialPost.id).label("count")
                )
                .where(and_(*filters) if filters else True)
                .group_by(SocialPost.sentiment_type)
            )
            
            sentiment_counts = {
                row.sentiment_type.value if row.sentiment_type else "unknown": row.count
                for row in sentiment_dist.fetchall()
            }
            
            # Average sentiment score
            avg_sentiment = await self.session.execute(
                select(func.avg(SocialPost.sentiment_score))
                .where(
                    and_(
                        SocialPost.sentiment_score.isnot(None),
                        *filters
                    ) if filters else SocialPost.sentiment_score.isnot(None)
                )
            )
            
            avg_score = avg_sentiment.scalar()
            
            # Platform breakdown
            platform_breakdown = await self.session.execute(
                select(
                    SocialPost.platform,
                    func.count(SocialPost.id).label("count"),
                    func.avg(SocialPost.sentiment_score).label("avg_sentiment")
                )
                .where(and_(*filters) if filters else True)
                .group_by(SocialPost.platform)
            )
            
            platforms = {
                row.platform.value: {
                    "count": row.count,
                    "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else 0
                }
                for row in platform_breakdown.fetchall()
            }
            
            return {
                "total_posts": sum(sentiment_counts.values()),
                "sentiment_distribution": sentiment_counts,
                "avg_sentiment_score": float(avg_score) if avg_score else 0,
                "platform_breakdown": platforms
            }
    
    async def get_trending_stocks(
        self,
        days: int = 1,
        min_posts: int = 5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending stocks based on social media activity.
        
        Args:
            days: Number of days to look back
            min_posts: Minimum number of posts required
            limit: Number of stocks to return
        
        Returns:
            List of trending stocks with metrics
        """
        async with DatabaseErrorHandler("Getting trending stocks"):
            from ..models.stock import Stock
            
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            stmt = (
                select(
                    Stock,
                    func.count(SocialPost.id).label("post_count"),
                    func.avg(SocialPost.sentiment_score).label("avg_sentiment"),
                    func.sum(
                        func.coalesce(SocialPost.score, 0) +
                        func.coalesce(SocialPost.upvotes, 0) +
                        func.coalesce(SocialPost.comment_count, 0)
                    ).label("total_engagement")
                )
                .join(SocialPost)
                .where(SocialPost.posted_at >= threshold_date)
                .group_by(Stock.id)
                .having(func.count(SocialPost.id) >= min_posts)
                .order_by(func.count(SocialPost.id).desc())
                .limit(limit)
            )
            
            result = await self.session.execute(stmt)
            
            return [
                {
                    "stock": row.Stock,
                    "post_count": row.post_count,
                    "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else 0,
                    "total_engagement": int(row.total_engagement) if row.total_engagement else 0
                }
                for row in result.fetchall()
            ]
    
    # Post management operations
    
    async def create_post(
        self,
        stock_id: str,
        platform: Platform,
        platform_post_id: str,
        content: str,
        author_username: str,
        posted_at: datetime,
        **kwargs
    ) -> SocialPost:
        """
        Create a new social media post.
        
        Args:
            stock_id: Stock ID
            platform: Social media platform
            platform_post_id: Platform-specific post ID
            content: Post content
            author_username: Author username
            posted_at: When the post was made
            **kwargs: Additional post data
        
        Returns:
            Created post instance
        """
        data = {
            "stock_id": stock_id,
            "platform": platform,
            "platform_post_id": platform_post_id,
            "content": content,
            "author_username": author_username,
            "posted_at": posted_at,
            "collected_at": datetime.now(timezone.utc),
            **kwargs
        }
        
        # Validate data
        data = self.validate_create_data(data)
        
        return await self.create(**data)
    
    async def update_sentiment(
        self,
        post_id: str,
        sentiment_score: Decimal,
        confidence: Decimal,
        analyzed_at: Optional[datetime] = None
    ) -> Optional[SocialPost]:
        """
        Update sentiment analysis for a post.
        
        Args:
            post_id: Post ID
            sentiment_score: Sentiment score (0.0 to 1.0)
            confidence: Analysis confidence (0.0 to 1.0)
            analyzed_at: When analysis was performed (optional)
        
        Returns:
            Updated post instance or None if not found
        """
        async with DatabaseErrorHandler(f"Updating sentiment for post {post_id}"):
            post = await self.get_by_id(post_id)
            if not post:
                return None
            
            post.update_sentiment(
                sentiment_score=sentiment_score,
                confidence=confidence,
                analyzed_at=analyzed_at
            )
            
            await self.session.flush()
            await self.session.refresh(post)
            
            logger.info(f"Updated sentiment for post {post_id}")
            return post
    
    async def update_engagement(
        self,
        post_id: str,
        score: Optional[int] = None,
        upvotes: Optional[int] = None,
        downvotes: Optional[int] = None,
        comment_count: Optional[int] = None,
        share_count: Optional[int] = None
    ) -> Optional[SocialPost]:
        """
        Update engagement metrics for a post.
        
        Args:
            post_id: Post ID
            score: Post score
            upvotes: Number of upvotes
            downvotes: Number of downvotes
            comment_count: Number of comments
            share_count: Number of shares
        
        Returns:
            Updated post instance or None if not found
        """
        async with DatabaseErrorHandler(f"Updating engagement for post {post_id}"):
            post = await self.get_by_id(post_id)
            if not post:
                return None
            
            post.update_engagement(
                score=score,
                upvotes=upvotes,
                downvotes=downvotes,
                comment_count=comment_count,
                share_count=share_count
            )
            
            await self.session.flush()
            await self.session.refresh(post)
            
            logger.info(f"Updated engagement for post {post_id}")
            return post
    
    async def upsert_post(
        self,
        platform_post_id: str,
        **kwargs
    ) -> SocialPost:
        """
        Insert or update social media post.
        
        Args:
            platform_post_id: Platform-specific post ID
            **kwargs: Post data
        
        Returns:
            Post instance
        """
        data = {
            "platform_post_id": platform_post_id,
            **kwargs
        }
        
        return await self.upsert(
            constraint_fields=["platform_post_id"],
            **data
        )
    
    # Analytics operations
    
    async def get_engagement_stats(
        self,
        stock_id: Optional[str] = None,
        platform: Optional[Platform] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get engagement statistics.
        
        Args:
            stock_id: Filter by stock ID (optional)
            platform: Filter by platform (optional)
            days: Only consider posts from last N days (optional)
        
        Returns:
            Engagement statistics dictionary
        """
        async with DatabaseErrorHandler("Getting engagement stats"):
            filters = []
            
            if stock_id:
                filters.append(SocialPost.stock_id == stock_id)
            if platform:
                filters.append(SocialPost.platform == platform)
            if days:
                threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
                filters.append(SocialPost.posted_at >= threshold_date)
            
            stats = await self.session.execute(
                select(
                    func.count(SocialPost.id).label("total_posts"),
                    func.sum(func.coalesce(SocialPost.score, 0)).label("total_score"),
                    func.sum(func.coalesce(SocialPost.upvotes, 0)).label("total_upvotes"),
                    func.sum(func.coalesce(SocialPost.downvotes, 0)).label("total_downvotes"),
                    func.sum(func.coalesce(SocialPost.comment_count, 0)).label("total_comments"),
                    func.sum(func.coalesce(SocialPost.share_count, 0)).label("total_shares"),
                    func.avg(SocialPost.score).label("avg_score"),
                    func.avg(SocialPost.upvotes).label("avg_upvotes"),
                    func.avg(SocialPost.comment_count).label("avg_comments")
                )
                .where(and_(*filters) if filters else True)
            )
            
            result = stats.fetchone()
            
            return {
                "total_posts": result.total_posts or 0,
                "total_score": int(result.total_score) if result.total_score else 0,
                "total_upvotes": int(result.total_upvotes) if result.total_upvotes else 0,
                "total_downvotes": int(result.total_downvotes) if result.total_downvotes else 0,
                "total_comments": int(result.total_comments) if result.total_comments else 0,
                "total_shares": int(result.total_shares) if result.total_shares else 0,
                "avg_score": float(result.avg_score) if result.avg_score else 0,
                "avg_upvotes": float(result.avg_upvotes) if result.avg_upvotes else 0,
                "avg_comments": float(result.avg_comments) if result.avg_comments else 0
            }
    
    async def get_posts_needing_analysis(self, limit: int = 100) -> List[SocialPost]:
        """
        Get posts that need sentiment analysis.
        
        Args:
            limit: Maximum number of posts to return
        
        Returns:
            List of posts without sentiment analysis
        """
        return await self.filter(
            filters={"sentiment_score": None},
            limit=limit,
            order_by="collected_at"
        )
    
    # Validation
    
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate social post creation data."""
        # Validate required fields
        required_fields = ["stock_id", "platform", "platform_post_id", "content", "author_username"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate content length
        content = data.get("content", "")
        if len(content) > 10000:  # Reasonable limit for social media posts
            raise ValidationError("Post content too long (max 10000 characters)")
        
        # Validate engagement metrics
        numeric_fields = ["score", "upvotes", "downvotes", "comment_count", "share_count", "author_follower_count"]
        for field in numeric_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, int) or value < 0:
                    raise ValidationError(f"{field} must be a non-negative integer")
        
        # Validate sentiment fields
        sentiment_fields = ["sentiment_score", "confidence"]
        for field in sentiment_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, (int, float, Decimal)):
                    raise ValidationError(f"{field} must be a number")
                if not (0 <= float(value) <= 1):
                    raise ValidationError(f"{field} must be between 0 and 1")
        
        return data
    
    def validate_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate social post update data."""
        # Don't allow core field updates
        immutable_fields = ["stock_id", "platform", "platform_post_id", "posted_at"]
        for field in immutable_fields:
            if field in data:
                raise ValidationError(f"Field {field} cannot be updated")
        
        # Validate engagement metrics
        numeric_fields = ["score", "upvotes", "downvotes", "comment_count", "share_count", "author_follower_count"]
        for field in numeric_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, int) or value < 0:
                    raise ValidationError(f"{field} must be a non-negative integer")
        
        return data