"""
Reddit background synchronization tasks.

Provides scheduled tasks for collecting Reddit posts, comments, and sentiment data
from finance-related subreddits for stock analysis.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from structlog import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_managed_session
from app.external_apis.reddit.service import RedditService
from app.external_apis.reddit.schemas import RedditSearchResult
from app.db.models.social_post import SocialPost, Platform
from app.tasks.models import TaskStats

logger = get_logger(__name__)
settings = get_settings()


class RedditSyncTaskManager:
    """
    Manages Reddit synchronization tasks and statistics.
    
    Coordinates the collection of Reddit data for financial analysis
    and tracks sync performance and statistics.
    """

    def __init__(self):
        """Initialize Reddit sync task manager."""
        self.sync_stats = {
            "last_sync": None,
            "total_posts_collected": 0,
            "total_comments_collected": 0,
            "finance_posts_collected": 0,
            "unique_symbols_found": 0,
            "sync_duration_seconds": 0.0,
            "errors_count": 0,
            "last_error": None,
            "subreddits_synced": 0,
            "trending_stocks": {},
            "sync_history": [],
        }

    async def sync_finance_discussions(
        self,
        limit_per_subreddit: int = 50,
        min_score: int = 10,
        min_quality_score: float = 0.3
    ) -> Dict[str, Any]:
        """
        Sync finance discussions from configured subreddits.
        
        Args:
            limit_per_subreddit: Maximum posts per subreddit
            min_score: Minimum post score
            min_quality_score: Minimum quality score (0-1)
            
        Returns:
            Sync results dictionary
        """
        start_time = datetime.utcnow()
        
        try:
            async with get_managed_session() as db_session:
                async with RedditService(db_session=db_session) as reddit_service:
                    logger.info("Starting Reddit finance discussions sync")
                    
                    # Get finance discussions
                    result = await reddit_service.get_finance_discussions(
                        subreddits=settings.REDDIT_SUBREDDITS,
                        limit_per_subreddit=limit_per_subreddit,
                        min_score=min_score,
                        min_quality_score=min_quality_score
                    )
                    
                    # Get comments for top posts
                    all_comments = []
                    top_posts = sorted(result.posts, key=lambda x: x.score, reverse=True)[:20]
                    
                    for post in top_posts:
                        try:
                            comments = await reddit_service.client.get_post_comments(
                                post_id=post.id,
                                limit=10,
                                min_score=5
                            )
                            all_comments.extend(comments)
                        except Exception as e:
                            logger.warning(f"Failed to get comments for post {post.id}: {e}")
                            continue
                    
                    # Save to database
                    posts_saved, comments_saved = await reddit_service.save_posts_to_database(
                        posts=result.posts,
                        comments=all_comments
                    )
                    
                    # Calculate statistics
                    unique_symbols = set()
                    for post in result.posts:
                        unique_symbols.update(post.extracted_symbols)
                    
                    # Update sync stats
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    sync_result = {
                        "success": True,
                        "timestamp": start_time.isoformat(),
                        "duration_seconds": duration,
                        "posts_collected": len(result.posts),
                        "comments_collected": len(all_comments),
                        "posts_saved": posts_saved,
                        "comments_saved": comments_saved,
                        "finance_posts": result.finance_related_posts,
                        "unique_symbols": len(unique_symbols),
                        "symbols_found": list(unique_symbols),
                        "subreddits_processed": len(settings.REDDIT_SUBREDDITS),
                        "quality_score_avg": sum(post.quality_score for post in result.posts) / len(result.posts) if result.posts else 0.0,
                        "error": None,
                    }
                    
                    # Update internal stats
                    self._update_sync_stats(sync_result)
                    
                    logger.info(
                        "Reddit finance discussions sync completed",
                        posts_collected=len(result.posts),
                        comments_collected=len(all_comments),
                        unique_symbols=len(unique_symbols),
                        duration=duration
                    )
                    
                    return sync_result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            sync_result = {
                "success": False,
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "posts_collected": 0,
                "comments_collected": 0,
                "posts_saved": 0,
                "comments_saved": 0,
                "finance_posts": 0,
                "unique_symbols": 0,
                "symbols_found": [],
                "subreddits_processed": 0,
                "quality_score_avg": 0.0,
                "error": error_msg,
            }
            
            self._update_sync_stats(sync_result)
            
            logger.error(f"Reddit finance discussions sync failed: {e}")
            raise

    async def sync_trending_stocks(self, min_mentions: int = 3) -> Dict[str, Any]:
        """
        Sync trending stocks analysis from Reddit.
        
        Args:
            min_mentions: Minimum mentions to be considered trending
            
        Returns:
            Trending stocks results
        """
        start_time = datetime.utcnow()
        
        try:
            async with get_managed_session() as db_session:
                async with RedditService(db_session=db_session) as reddit_service:
                    logger.info("Starting Reddit trending stocks analysis")
                    
                    # Get trending stocks
                    trending_stocks = await reddit_service.get_trending_stocks(
                        subreddits=settings.REDDIT_SUBREDDITS,
                        limit=200,
                        time_filter="day",
                        min_mentions=min_mentions
                    )
                    
                    # Update internal trending stocks cache
                    self.sync_stats["trending_stocks"] = trending_stocks
                    
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    result = {
                        "success": True,
                        "timestamp": start_time.isoformat(),
                        "duration_seconds": duration,
                        "trending_stocks_count": len(trending_stocks),
                        "top_trending": list(trending_stocks.keys())[:10],
                        "trending_stocks": trending_stocks,
                        "error": None,
                    }
                    
                    logger.info(
                        "Reddit trending stocks analysis completed",
                        trending_count=len(trending_stocks),
                        duration=duration
                    )
                    
                    return result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            result = {
                "success": False,
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "trending_stocks_count": 0,
                "top_trending": [],
                "trending_stocks": {},
                "error": error_msg,
            }
            
            logger.error(f"Reddit trending stocks analysis failed: {e}")
            raise

    async def sync_stock_discussions(
        self,
        symbol: str,
        limit: int = 100,
        time_filter: str = "week"
    ) -> Dict[str, Any]:
        """
        Sync discussions for a specific stock symbol.
        
        Args:
            symbol: Stock symbol to search for
            limit: Maximum posts to collect
            time_filter: Time filter for search
            
        Returns:
            Stock discussions sync results
        """
        start_time = datetime.utcnow()
        
        try:
            async with get_managed_session() as db_session:
                async with RedditService(db_session=db_session) as reddit_service:
                    logger.info(f"Starting Reddit sync for {symbol}")
                    
                    # Get stock discussions
                    result = await reddit_service.get_stock_discussions(
                        symbol=symbol,
                        subreddits=settings.REDDIT_SUBREDDITS,
                        limit=limit,
                        time_filter=time_filter,
                        min_score=5
                    )
                    
                    # Save to database
                    posts_saved, comments_saved = await reddit_service.save_posts_to_database(
                        posts=result.posts,
                        comments=result.comments
                    )
                    
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    sync_result = {
                        "success": True,
                        "symbol": symbol,
                        "timestamp": start_time.isoformat(),
                        "duration_seconds": duration,
                        "posts_collected": len(result.posts),
                        "comments_collected": len(result.comments),
                        "posts_saved": posts_saved,
                        "comments_saved": comments_saved,
                        "avg_score": sum(post.score for post in result.posts) / len(result.posts) if result.posts else 0.0,
                        "total_engagement": sum(post.num_comments for post in result.posts),
                        "error": None,
                    }
                    
                    logger.info(
                        f"Reddit sync for {symbol} completed",
                        posts_collected=len(result.posts),
                        comments_collected=len(result.comments),
                        duration=duration
                    )
                    
                    return sync_result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            sync_result = {
                "success": False,
                "symbol": symbol,
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "posts_collected": 0,
                "comments_collected": 0,
                "posts_saved": 0,
                "comments_saved": 0,
                "avg_score": 0.0,
                "total_engagement": 0,
                "error": error_msg,
            }
            
            logger.error(f"Reddit sync for {symbol} failed: {e}")
            raise

    def _update_sync_stats(self, sync_result: Dict[str, Any]) -> None:
        """Update internal sync statistics."""
        if sync_result["success"]:
            self.sync_stats["last_sync"] = sync_result["timestamp"]
            self.sync_stats["total_posts_collected"] += sync_result.get("posts_collected", 0)
            self.sync_stats["total_comments_collected"] += sync_result.get("comments_collected", 0)
            self.sync_stats["finance_posts_collected"] += sync_result.get("finance_posts", 0)
            self.sync_stats["unique_symbols_found"] = max(
                self.sync_stats["unique_symbols_found"],
                sync_result.get("unique_symbols", 0)
            )
            self.sync_stats["sync_duration_seconds"] = sync_result["duration_seconds"]
            self.sync_stats["subreddits_synced"] = sync_result.get("subreddits_processed", 0)
        else:
            self.sync_stats["errors_count"] += 1
            self.sync_stats["last_error"] = sync_result.get("error")
        
        # Keep last 10 sync results
        self.sync_stats["sync_history"].append(sync_result)
        if len(self.sync_stats["sync_history"]) > 10:
            self.sync_stats["sync_history"] = self.sync_stats["sync_history"][-10:]

    async def get_sync_stats(self) -> Dict[str, Any]:
        """
        Get Reddit sync statistics.
        
        Returns:
            Dictionary with sync statistics
        """
        return {
            **self.sync_stats,
            "configured_subreddits": settings.REDDIT_SUBREDDITS,
            "rate_limit_per_minute": settings.REDDIT_RATE_LIMIT_PER_MINUTE,
            "last_24h_posts": await self._get_recent_posts_count(hours=24),
            "last_7d_posts": await self._get_recent_posts_count(hours=24 * 7),
        }

    async def _get_recent_posts_count(self, hours: int = 24) -> int:
        """Get count of Reddit posts collected in recent hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            async with get_managed_session() as db_session:
                result = await db_session.execute(
                    text("""
                    SELECT COUNT(*) 
                    FROM social_posts 
                    WHERE platform = :platform 
                    AND created_at >= :cutoff_time
                    """),
                    {"platform": Platform.REDDIT.name, "cutoff_time": cutoff_time}
                )
                return result.scalar() or 0
                
        except Exception as e:
            logger.warning(f"Failed to get recent posts count: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Reddit sync system.
        
        Returns:
            Health check results
        """
        issues = []
        recommendations = []
        
        # Check if we have recent syncs
        if self.sync_stats["last_sync"]:
            last_sync = datetime.fromisoformat(self.sync_stats["last_sync"])
            hours_since_sync = (datetime.utcnow() - last_sync).total_seconds() / 3600
            
            if hours_since_sync > 6:  # More than 6 hours
                issues.append(f"Last sync was {hours_since_sync:.1f} hours ago")
                recommendations.append("Check Reddit sync schedule and connectivity")
        else:
            issues.append("No successful syncs recorded")
            recommendations.append("Verify Reddit API credentials and run initial sync")
        
        # Check error rate
        if self.sync_stats["errors_count"] > 0:
            total_syncs = len(self.sync_stats["sync_history"])
            if total_syncs > 0:
                error_rate = self.sync_stats["errors_count"] / total_syncs
                if error_rate > 0.2:  # More than 20% error rate
                    issues.append(f"High error rate: {error_rate:.1%}")
                    recommendations.append("Check Reddit API status and rate limits")
        
        # Check trending stocks data freshness
        if not self.sync_stats["trending_stocks"]:
            issues.append("No trending stocks data available")
            recommendations.append("Run trending stocks analysis")
        
        return {
            "service": "reddit_sync",
            "healthy": len(issues) == 0,
            "issues": issues,
            "recommendations": recommendations,
            "stats": self.sync_stats,
            "configured_subreddits": len(settings.REDDIT_SUBREDDITS),
            "rate_limit_configured": settings.REDDIT_RATE_LIMIT_PER_MINUTE,
        }


# Global task manager instance
_reddit_task_manager = None


def get_reddit_task_manager() -> RedditSyncTaskManager:
    """Get or create Reddit task manager."""
    global _reddit_task_manager
    if _reddit_task_manager is None:
        _reddit_task_manager = RedditSyncTaskManager()
    return _reddit_task_manager


# Scheduled task functions
async def scheduled_reddit_finance_sync():
    """Scheduled task for Reddit finance discussions sync."""
    task_manager = get_reddit_task_manager()
    
    try:
        result = await task_manager.sync_finance_discussions(
            limit_per_subreddit=50,
            min_score=10,
            min_quality_score=0.3
        )
        
        logger.info("Scheduled Reddit finance sync completed", **result)
        return result
        
    except Exception as e:
        logger.error(f"Scheduled Reddit finance sync failed: {e}")
        raise


async def scheduled_reddit_trending_analysis():
    """Scheduled task for Reddit trending stocks analysis."""
    task_manager = get_reddit_task_manager()
    
    try:
        result = await task_manager.sync_trending_stocks(min_mentions=3)
        
        logger.info("Scheduled Reddit trending analysis completed", **result)
        return result
        
    except Exception as e:
        logger.error(f"Scheduled Reddit trending analysis failed: {e}")
        raise


async def scheduled_reddit_stock_sync(symbol: str):
    """
    Scheduled task for syncing specific stock discussions.
    
    Args:
        symbol: Stock symbol to sync
    """
    task_manager = get_reddit_task_manager()
    
    try:
        result = await task_manager.sync_stock_discussions(
            symbol=symbol,
            limit=100,
            time_filter="week"
        )
        
        logger.info(f"Scheduled Reddit stock sync for {symbol} completed", **result)
        return result
        
    except Exception as e:
        logger.error(f"Scheduled Reddit stock sync for {symbol} failed: {e}")
        raise