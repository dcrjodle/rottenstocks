"""
Rating repository for database operations.

This module provides rating-specific database operations including
CRUD operations, rating analysis, and performance tracking.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.rating import Rating, RatingType, RecommendationType
from ..exceptions import NotFoundError, ValidationError, DatabaseErrorHandler
from .base import BaseRepository

logger = logging.getLogger(__name__)


class RatingRepository(BaseRepository[Rating]):
    """Repository for rating-related database operations."""
    
    def get_model_class(self) -> type[Rating]:
        """Get the Rating model class."""
        return Rating
    
    def get_unique_fields(self) -> List[str]:
        """Get unique fields for Rating model."""
        return ["stock_id", "expert_id", "rating_date"]
    
    # Rating-specific queries
    
    async def get_by_stock(
        self, 
        stock_id: str,
        rating_type: Optional[RatingType] = None,
        limit: Optional[int] = None
    ) -> List[Rating]:
        """
        Get ratings for a specific stock.
        
        Args:
            stock_id: Stock ID
            rating_type: Filter by rating type (optional)
            limit: Maximum number of ratings to return
        
        Returns:
            List of ratings for the stock
        """
        filters = {"stock_id": stock_id}
        if rating_type:
            filters["rating_type"] = rating_type
        
        return await self.filter(
            filters=filters,
            limit=limit,
            order_by="-rating_date",
            options=[selectinload(Rating.expert), selectinload(Rating.stock)]
        )
    
    async def get_by_expert(
        self, 
        expert_id: str,
        limit: Optional[int] = None
    ) -> List[Rating]:
        """
        Get ratings by a specific expert.
        
        Args:
            expert_id: Expert ID
            limit: Maximum number of ratings to return
        
        Returns:
            List of ratings by the expert
        """
        return await self.filter(
            filters={"expert_id": expert_id},
            limit=limit,
            order_by="-rating_date",
            options=[selectinload(Rating.stock)]
        )
    
    async def get_recent_ratings(
        self, 
        days: int = 30,
        rating_type: Optional[RatingType] = None,
        limit: Optional[int] = None
    ) -> List[Rating]:
        """
        Get recent ratings within specified days.
        
        Args:
            days: Number of days to look back
            rating_type: Filter by rating type (optional)
            limit: Maximum number of ratings to return
        
        Returns:
            List of recent ratings
        """
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        filters = {"rating_date": {"gte": threshold_date}}
        if rating_type:
            filters["rating_type"] = rating_type
        
        return await self.filter(
            filters=filters,
            limit=limit,
            order_by="-rating_date",
            options=[selectinload(Rating.expert), selectinload(Rating.stock)]
        )
    
    async def get_by_recommendation(
        self, 
        recommendation: RecommendationType,
        limit: Optional[int] = None
    ) -> List[Rating]:
        """
        Get ratings by recommendation type.
        
        Args:
            recommendation: Recommendation type
            limit: Maximum number of ratings to return
        
        Returns:
            List of ratings with the recommendation
        """
        return await self.filter(
            filters={"recommendation": recommendation},
            limit=limit,
            order_by="-rating_date",
            options=[selectinload(Rating.expert), selectinload(Rating.stock)]
        )
    
    async def get_by_score_range(
        self,
        min_score: Optional[Decimal] = None,
        max_score: Optional[Decimal] = None,
        limit: Optional[int] = None
    ) -> List[Rating]:
        """
        Get ratings within a score range.
        
        Args:
            min_score: Minimum score (inclusive)
            max_score: Maximum score (inclusive)
            limit: Maximum number of ratings to return
        
        Returns:
            List of ratings in the score range
        """
        filters = {}
        if min_score is not None:
            filters["score"] = {"gte": min_score}
        if max_score is not None:
            if "score" not in filters:
                filters["score"] = {}
            filters["score"]["lte"] = max_score
        
        return await self.filter(
            filters=filters,
            limit=limit,
            order_by="-score",
            options=[selectinload(Rating.expert), selectinload(Rating.stock)]
        )
    
    async def get_top_rated_stocks(
        self,
        rating_type: Optional[RatingType] = None,
        days: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top-rated stocks based on average ratings.
        
        Args:
            rating_type: Filter by rating type (optional)
            days: Only consider ratings from last N days (optional)
            limit: Number of stocks to return
        
        Returns:
            List of top-rated stocks with their average ratings
        """
        async with DatabaseErrorHandler("Getting top-rated stocks"):
            from ..models.stock import Stock
            
            # Build filters
            filters = []
            if rating_type:
                filters.append(Rating.rating_type == rating_type)
            if days:
                threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
                filters.append(Rating.rating_date >= threshold_date)
            
            stmt = (
                select(
                    Stock,
                    func.avg(Rating.score).label("avg_score"),
                    func.count(Rating.id).label("rating_count"),
                    func.avg(Rating.confidence).label("avg_confidence")
                )
                .join(Rating)
                .where(and_(*filters) if filters else True)
                .group_by(Stock.id)
                .order_by(func.avg(Rating.score).desc())
                .limit(limit)
            )
            
            result = await self.session.execute(stmt)
            
            return [
                {
                    "stock": row.Stock,
                    "avg_score": float(row.avg_score),
                    "rating_count": row.rating_count,
                    "avg_confidence": float(row.avg_confidence) if row.avg_confidence else 0
                }
                for row in result.fetchall()
            ]
    
    async def get_rating_distribution(
        self,
        rating_type: Optional[RatingType] = None
    ) -> Dict[str, int]:
        """
        Get distribution of ratings by score ranges.
        
        Args:
            rating_type: Filter by rating type (optional)
        
        Returns:
            Dictionary with score ranges and counts
        """
        async with DatabaseErrorHandler("Getting rating distribution"):
            filters = []
            if rating_type:
                filters.append(Rating.rating_type == rating_type)
            
            stmt = (
                select(
                    func.case(
                        (Rating.score >= 4.5, "Excellent (4.5-5.0)"),
                        (Rating.score >= 3.5, "Good (3.5-4.5)"),
                        (Rating.score >= 2.5, "Fair (2.5-3.5)"),
                        (Rating.score >= 1.5, "Poor (1.5-2.5)"),
                        else_="Very Poor (0.0-1.5)"
                    ).label("score_range"),
                    func.count(Rating.id).label("count")
                )
                .where(and_(*filters) if filters else True)
                .group_by("score_range")
            )
            
            result = await self.session.execute(stmt)
            
            return {row.score_range: row.count for row in result.fetchall()}
    
    # Rating analysis operations
    
    async def get_stock_rating_summary(self, stock_id: str) -> Dict[str, Any]:
        """
        Get comprehensive rating summary for a stock.
        
        Args:
            stock_id: Stock ID
        
        Returns:
            Rating summary dictionary
        """
        async with DatabaseErrorHandler(f"Getting rating summary for stock {stock_id}"):
            # Overall statistics
            overall_stats = await self.session.execute(
                select(
                    func.count(Rating.id).label("total_ratings"),
                    func.avg(Rating.score).label("avg_score"),
                    func.min(Rating.score).label("min_score"),
                    func.max(Rating.score).label("max_score"),
                    func.avg(Rating.confidence).label("avg_confidence")
                )
                .where(Rating.stock_id == stock_id)
            )
            
            overall = overall_stats.fetchone()
            
            # Expert vs Popular breakdown
            type_breakdown = await self.session.execute(
                select(
                    Rating.rating_type,
                    func.count(Rating.id).label("count"),
                    func.avg(Rating.score).label("avg_score")
                )
                .where(Rating.stock_id == stock_id)
                .group_by(Rating.rating_type)
            )
            
            types = {
                row.rating_type.value: {
                    "count": row.count,
                    "avg_score": float(row.avg_score)
                }
                for row in type_breakdown.fetchall()
            }
            
            # Recommendation breakdown
            rec_breakdown = await self.session.execute(
                select(
                    Rating.recommendation,
                    func.count(Rating.id).label("count")
                )
                .where(Rating.stock_id == stock_id)
                .group_by(Rating.recommendation)
            )
            
            recommendations = {rec.recommendation.value: rec.count for rec in rec_breakdown.fetchall()}
            
            # Recent trend (last 30 days)
            recent_threshold = datetime.now(timezone.utc) - timedelta(days=30)
            recent_stats = await self.session.execute(
                select(
                    func.count(Rating.id).label("recent_count"),
                    func.avg(Rating.score).label("recent_avg")
                )
                .where(
                    and_(
                        Rating.stock_id == stock_id,
                        Rating.rating_date >= recent_threshold
                    )
                )
            )
            
            recent = recent_stats.fetchone()
            
            return {
                "stock_id": stock_id,
                "total_ratings": overall.total_ratings or 0,
                "avg_score": float(overall.avg_score) if overall.avg_score else 0,
                "min_score": float(overall.min_score) if overall.min_score else 0,
                "max_score": float(overall.max_score) if overall.max_score else 0,
                "avg_confidence": float(overall.avg_confidence) if overall.avg_confidence else 0,
                "by_type": types,
                "by_recommendation": recommendations,
                "recent_30d": {
                    "count": recent.recent_count or 0,
                    "avg_score": float(recent.recent_avg) if recent.recent_avg else 0
                }
            }
    
    async def get_consensus_rating(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        Get consensus rating for a stock based on expert ratings.
        
        Args:
            stock_id: Stock ID
        
        Returns:
            Consensus rating dictionary or None if no expert ratings
        """
        async with DatabaseErrorHandler(f"Getting consensus rating for stock {stock_id}"):
            # Get expert ratings only
            expert_stats = await self.session.execute(
                select(
                    func.count(Rating.id).label("expert_count"),
                    func.avg(Rating.score).label("avg_score"),
                    func.avg(Rating.confidence).label("avg_confidence"),
                    func.avg(Rating.price_target).label("avg_price_target")
                )
                .where(
                    and_(
                        Rating.stock_id == stock_id,
                        Rating.rating_type == RatingType.EXPERT
                    )
                )
            )
            
            stats = expert_stats.fetchone()
            
            if not stats.expert_count:
                return None
            
            # Get recommendation consensus
            rec_consensus = await self.session.execute(
                select(
                    Rating.recommendation,
                    func.count(Rating.id).label("count")
                )
                .where(
                    and_(
                        Rating.stock_id == stock_id,
                        Rating.rating_type == RatingType.EXPERT
                    )
                )
                .group_by(Rating.recommendation)
                .order_by(func.count(Rating.id).desc())
            )
            
            rec_counts = list(rec_consensus.fetchall())
            consensus_recommendation = rec_counts[0].recommendation if rec_counts else None
            
            return {
                "stock_id": stock_id,
                "expert_count": stats.expert_count,
                "consensus_score": float(stats.avg_score),
                "consensus_recommendation": consensus_recommendation.value if consensus_recommendation else None,
                "avg_confidence": float(stats.avg_confidence) if stats.avg_confidence else 0,
                "avg_price_target": float(stats.avg_price_target) if stats.avg_price_target else None,
                "recommendation_breakdown": {rec.recommendation.value: rec.count for rec in rec_counts}
            }
    
    # Rating management operations
    
    async def create_rating(
        self,
        stock_id: str,
        expert_id: Optional[str],
        rating_type: RatingType,
        score: Decimal,
        recommendation: RecommendationType,
        **kwargs
    ) -> Rating:
        """
        Create a new rating.
        
        Args:
            stock_id: Stock ID
            expert_id: Expert ID (None for popular ratings)
            rating_type: Rating type
            score: Rating score (0.00 to 5.00)
            recommendation: Recommendation type
            **kwargs: Additional rating data
        
        Returns:
            Created rating instance
        """
        data = {
            "stock_id": stock_id,
            "expert_id": expert_id,
            "rating_type": rating_type,
            "score": score,
            "recommendation": recommendation,
            "rating_date": datetime.now(timezone.utc),
            **kwargs
        }
        
        # Validate data
        data = self.validate_create_data(data)
        
        return await self.create(**data)
    
    async def update_rating_score(
        self,
        rating_id: str,
        score: Decimal,
        confidence: Optional[Decimal] = None
    ) -> Optional[Rating]:
        """
        Update rating score and confidence.
        
        Args:
            rating_id: Rating ID
            score: New rating score
            confidence: New confidence level (optional)
        
        Returns:
            Updated rating instance or None if not found
        """
        update_data = {"score": score}
        if confidence is not None:
            update_data["confidence"] = confidence
        
        return await self.update(rating_id, **update_data)
    
    async def upsert_rating(
        self,
        stock_id: str,
        expert_id: Optional[str],
        rating_date: datetime,
        **kwargs
    ) -> Rating:
        """
        Insert or update rating.
        
        Args:
            stock_id: Stock ID
            expert_id: Expert ID
            rating_date: Rating date
            **kwargs: Additional rating data
        
        Returns:
            Rating instance
        """
        data = {
            "stock_id": stock_id,
            "expert_id": expert_id,
            "rating_date": rating_date,
            **kwargs
        }
        
        return await self.upsert(
            constraint_fields=["stock_id", "expert_id", "rating_date"],
            **data
        )
    
    # Validation
    
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rating creation data."""
        # Validate required fields
        required_fields = ["stock_id", "rating_type", "score", "recommendation"]
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate score range
        score = data.get("score")
        if not isinstance(score, (int, float, Decimal)):
            raise ValidationError("Score must be a number")
        score = Decimal(str(score))
        if not (Decimal("0.00") <= score <= Decimal("5.00")):
            raise ValidationError("Score must be between 0.00 and 5.00")
        data["score"] = score
        
        # Validate confidence range
        confidence = data.get("confidence")
        if confidence is not None:
            if not isinstance(confidence, (int, float, Decimal)):
                raise ValidationError("Confidence must be a number")
            confidence = Decimal(str(confidence))
            if not (Decimal("0.00") <= confidence <= Decimal("1.00")):
                raise ValidationError("Confidence must be between 0.00 and 1.00")
            data["confidence"] = confidence
        
        # Validate price targets
        price_fields = ["price_target", "price_at_rating"]
        for field in price_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, (int, float, Decimal)) or value < 0:
                    raise ValidationError(f"{field} must be a positive number")
        
        # Validate rating type and expert consistency
        rating_type = data.get("rating_type")
        expert_id = data.get("expert_id")
        
        if rating_type == RatingType.EXPERT and not expert_id:
            raise ValidationError("Expert ratings must have an expert_id")
        if rating_type == RatingType.POPULAR and expert_id:
            raise ValidationError("Popular ratings cannot have an expert_id")
        
        return data
    
    def validate_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rating update data."""
        # Don't allow core field updates
        immutable_fields = ["stock_id", "expert_id", "rating_type", "rating_date"]
        for field in immutable_fields:
            if field in data:
                raise ValidationError(f"Field {field} cannot be updated")
        
        # Validate score range
        score = data.get("score")
        if score is not None:
            if not isinstance(score, (int, float, Decimal)):
                raise ValidationError("Score must be a number")
            score = Decimal(str(score))
            if not (Decimal("0.00") <= score <= Decimal("5.00")):
                raise ValidationError("Score must be between 0.00 and 5.00")
            data["score"] = score
        
        # Validate confidence range
        confidence = data.get("confidence")
        if confidence is not None:
            if not isinstance(confidence, (int, float, Decimal)):
                raise ValidationError("Confidence must be a number")
            confidence = Decimal(str(confidence))
            if not (Decimal("0.00") <= confidence <= Decimal("1.00")):
                raise ValidationError("Confidence must be between 0.00 and 1.00")
            data["confidence"] = confidence
        
        return data