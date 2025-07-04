"""
Rating service layer for business logic.

Handles rating-related business operations including CRUD operations,
aggregations, and rating calculations.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, or_, select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.rating import Rating, RatingType, RecommendationType
from app.db.models.stock import Stock
from app.db.models.expert import Expert
from app.db.repositories.rating import RatingRepository
from app.schemas.rating import (
    RatingCreate,
    RatingUpdate,
    RatingResponse,
    RatingListResponse,
    RatingSearch,
    RatingAggregation,
    RatingStats,
    RatingHistory,
    RatingHistoryPoint,
    RatingBulkCreate,
    RatingBulkResponse,
)
from app.api.v1.deps import CommonQueryParams

logger = logging.getLogger(__name__)


class RatingService:
    """Service class for rating-related business logic."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.repository = RatingRepository(db)
    
    async def create_rating(self, rating_data: RatingCreate) -> RatingResponse:
        """
        Create a new rating.
        
        Args:
            rating_data: Rating creation data
            
        Returns:
            Created rating response
            
        Raises:
            ValueError: If stock or expert doesn't exist, or rating already exists
        """
        # Validate stock exists
        stock_query = select(Stock).where(Stock.id == rating_data.stock_id)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()
        if not stock:
            raise ValueError(f"Stock with ID {rating_data.stock_id} not found")
        
        # Validate expert exists if expert_id provided
        if rating_data.expert_id:
            expert_query = select(Expert).where(Expert.id == rating_data.expert_id)
            expert_result = await self.db.execute(expert_query)
            expert = expert_result.scalar_one_or_none()
            if not expert:
                raise ValueError(f"Expert with ID {rating_data.expert_id} not found")
        
        # Check for existing rating (unique constraint)
        existing_query = select(Rating).where(
            and_(
                Rating.stock_id == rating_data.stock_id,
                Rating.expert_id == rating_data.expert_id,
                Rating.rating_date == rating_data.rating_date
            )
        )
        existing = await self.db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise ValueError("Rating already exists for this stock, expert, and date")
        
        # Create rating
        rating_dict = rating_data.dict()
        rating = await self.repository.create(**rating_dict)
        await self.db.commit()
        
        logger.info(f"Created rating: Stock {rating.stock_id}, Expert {rating.expert_id}")
        return self._to_response(rating)
    
    async def get_rating_by_id(self, rating_id: str) -> Optional[RatingResponse]:
        """
        Get rating by ID.
        
        Args:
            rating_id: Rating ID
            
        Returns:
            Rating response or None if not found
        """
        rating = await self.repository.get_by_id(rating_id)
        return self._to_response(rating) if rating else None
    
    async def update_rating(self, rating_id: str, rating_data: RatingUpdate) -> Optional[RatingResponse]:
        """
        Update existing rating.
        
        Args:
            rating_id: Rating ID
            rating_data: Update data
            
        Returns:
            Updated rating response or None if not found
        """
        rating = await self.repository.get_by_id(rating_id)
        if not rating:
            return None
        
        # Update fields
        update_data = rating_data.dict(exclude_unset=True)
        if update_data:
            # Use model method for proper validation
            rating.update_rating(
                score=update_data.get('score'),
                recommendation=update_data.get('recommendation'),
                confidence=update_data.get('confidence'),
                price_target=update_data.get('price_target'),
                summary=update_data.get('summary'),
                analysis=update_data.get('analysis'),
            )
            
            # Update other fields directly
            for field in ['risks', 'catalysts', 'expiry_date']:
                if field in update_data:
                    setattr(rating, field, update_data[field])
            
            await self.db.commit()
            logger.info(f"Updated rating: {rating.id}")
        
        return self._to_response(rating)
    
    async def delete_rating(self, rating_id: str) -> bool:
        """
        Delete a rating.
        
        Args:
            rating_id: Rating ID
            
        Returns:
            True if deleted, False if not found
        """
        rating = await self.repository.get_by_id(rating_id)
        if not rating:
            return False
        
        await self.repository.delete(rating)
        await self.db.commit()
        
        logger.info(f"Deleted rating: {rating_id}")
        return True
    
    async def list_ratings(
        self,
        params: CommonQueryParams,
        filters: Optional[RatingSearch] = None
    ) -> RatingListResponse:
        """
        List ratings with pagination and filtering.
        
        Args:
            params: Common query parameters
            filters: Optional search filters
            
        Returns:
            Paginated rating list response
        """
        # Build query
        query = select(Rating).options(
            selectinload(Rating.stock),
            selectinload(Rating.expert)
        )
        
        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
        
        # Apply search
        if params.search:
            # Join with stock and expert for text search
            query = query.join(Stock).outerjoin(Expert)
            search_filter = or_(
                Stock.symbol.ilike(f"%{params.search}%"),
                Stock.name.ilike(f"%{params.search}%"),
                Expert.name.ilike(f"%{params.search}%"),
                Rating.summary.ilike(f"%{params.search}%")
            )
            query = query.where(search_filter)
        
        # Apply sorting
        if params.sort_by:
            sort_column = getattr(Rating, params.sort_by, None)
            if sort_column:
                if params.sort_order == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))
        else:
            # Default sort by rating date desc
            query = query.order_by(desc(Rating.rating_date))
        
        # Get total count
        count_query = select(func.count(Rating.id))
        if filters:
            count_query = self._apply_filters(count_query, filters)
        if params.search:
            count_query = count_query.join(Stock).outerjoin(Expert).where(search_filter)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(params.skip).limit(params.limit)
        
        # Execute query
        result = await self.db.execute(query)
        ratings = result.scalars().all()
        
        # Calculate pagination info
        pages = (total + params.limit - 1) // params.limit
        has_next = params.page < pages
        has_prev = params.page > 1
        
        return RatingListResponse(
            ratings=[self._to_response(rating) for rating in ratings],
            total=total,
            page=params.page,
            limit=params.limit,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev,
        )
    
    async def get_stock_ratings(self, stock_id: str) -> List[RatingResponse]:
        """Get all ratings for a specific stock."""
        query = select(Rating).where(Rating.stock_id == stock_id).options(
            selectinload(Rating.stock),
            selectinload(Rating.expert)
        ).order_by(desc(Rating.rating_date))
        
        result = await self.db.execute(query)
        ratings = result.scalars().all()
        
        return [self._to_response(rating) for rating in ratings]
    
    async def get_expert_ratings(self, expert_id: str) -> List[RatingResponse]:
        """Get all ratings by a specific expert."""
        query = select(Rating).where(Rating.expert_id == expert_id).options(
            selectinload(Rating.stock),
            selectinload(Rating.expert)
        ).order_by(desc(Rating.rating_date))
        
        result = await self.db.execute(query)
        ratings = result.scalars().all()
        
        return [self._to_response(rating) for rating in ratings]
    
    async def get_rating_aggregation(self, stock_id: str) -> Optional[RatingAggregation]:
        """
        Get aggregated rating data for a stock.
        
        Args:
            stock_id: Stock ID
            
        Returns:
            Rating aggregation data
        """
        # Get stock
        stock_query = select(Stock).where(Stock.id == stock_id)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()
        if not stock:
            return None
        
        # Get expert ratings stats
        expert_stats = await self._get_rating_stats(stock_id, RatingType.EXPERT)
        
        # Get popular ratings stats
        popular_stats = await self._get_rating_stats(stock_id, RatingType.POPULAR)
        
        # Calculate overall recommendation
        overall_recommendation = await self._calculate_overall_recommendation(stock_id)
        
        # Calculate overall score (weighted average)
        overall_score = await self._calculate_overall_score(stock_id)
        
        # Get total ratings count
        total_query = select(func.count(Rating.id)).where(Rating.stock_id == stock_id)
        total_result = await self.db.execute(total_query)
        total_ratings = total_result.scalar()
        
        return RatingAggregation(
            stock_id=stock_id,
            expert_ratings=expert_stats,
            popular_ratings=popular_stats,
            overall_recommendation=overall_recommendation,
            overall_score=overall_score,
            total_ratings=total_ratings,
            last_updated=datetime.now(timezone.utc),
        )
    
    async def get_rating_history(
        self,
        stock_id: str,
        rating_type: RatingType,
        period: str = "daily",
        days: int = 30
    ) -> RatingHistory:
        """
        Get historical rating data for a stock.
        
        Args:
            stock_id: Stock ID
            rating_type: Type of ratings to include
            period: Aggregation period (daily, weekly, monthly)
            days: Number of days to include
            
        Returns:
            Historical rating data
        """
        # This would need more complex SQL for proper time-based aggregation
        # For now, return a simple structure
        query = select(Rating).where(
            and_(
                Rating.stock_id == stock_id,
                Rating.rating_type == rating_type,
                Rating.rating_date >= datetime.now(timezone.utc).date() - timedelta(days=days)
            )
        ).order_by(Rating.rating_date)
        
        result = await self.db.execute(query)
        ratings = result.scalars().all()
        
        # Group by date for daily aggregation
        data_points = []
        if ratings:
            # Simple daily aggregation
            from collections import defaultdict
            daily_data = defaultdict(list)
            
            for rating in ratings:
                date_key = rating.rating_date.date()
                daily_data[date_key].append(rating)
            
            for date, day_ratings in daily_data.items():
                avg_score = sum(r.score for r in day_ratings) / len(day_ratings)
                recommendation_dist = {}
                for rating in day_ratings:
                    rec = rating.recommendation.value
                    recommendation_dist[rec] = recommendation_dist.get(rec, 0) + 1
                
                data_points.append(RatingHistoryPoint(
                    date=datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc),
                    average_score=avg_score,
                    rating_count=len(day_ratings),
                    recommendation_distribution=recommendation_dist,
                ))
        
        return RatingHistory(
            stock_id=stock_id,
            rating_type=rating_type,
            period=period,
            data_points=data_points,
        )
    
    async def bulk_create_ratings(self, bulk_data: RatingBulkCreate) -> RatingBulkResponse:
        """
        Bulk create ratings.
        
        Args:
            bulk_data: Bulk creation data
            
        Returns:
            Bulk operation response
        """
        created = 0
        updated = 0
        errors = []
        ratings = []
        
        for rating_data in bulk_data.ratings:
            try:
                # Check if rating exists
                existing_query = select(Rating).where(
                    and_(
                        Rating.stock_id == rating_data.stock_id,
                        Rating.expert_id == rating_data.expert_id,
                        Rating.rating_date == rating_data.rating_date
                    )
                )
                existing_result = await self.db.execute(existing_query)
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    # Update existing rating
                    update_data = rating_data.dict(exclude={'stock_id', 'expert_id', 'rating_date'})
                    for field, value in update_data.items():
                        setattr(existing, field, value)
                    rating = existing
                    updated += 1
                else:
                    # Create new rating
                    rating_dict = rating_data.dict()
                    rating = await self.repository.create(**rating_dict)
                    created += 1
                
                ratings.append(self._to_response(rating))
                
            except Exception as e:
                error_msg = f"Error processing rating for stock {rating_data.stock_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        if created > 0 or updated > 0:
            await self.db.commit()
        
        logger.info(f"Bulk rating operation: {created} created, {updated} updated, {len(errors)} errors")
        
        return RatingBulkResponse(
            created=created,
            updated=updated,
            errors=errors,
            ratings=ratings,
        )
    
    def _apply_filters(self, query, filters: RatingSearch):
        """Apply search filters to query."""
        conditions = []
        
        if filters.stock_id:
            conditions.append(Rating.stock_id == filters.stock_id)
        
        if filters.expert_id:
            conditions.append(Rating.expert_id == filters.expert_id)
        
        if filters.rating_type:
            conditions.append(Rating.rating_type == filters.rating_type)
        
        if filters.recommendation:
            conditions.append(Rating.recommendation == filters.recommendation)
        
        if filters.min_score is not None:
            conditions.append(Rating.score >= filters.min_score)
        
        if filters.max_score is not None:
            conditions.append(Rating.score <= filters.max_score)
        
        if filters.min_confidence is not None:
            conditions.append(Rating.confidence >= filters.min_confidence)
        
        if filters.from_date:
            conditions.append(Rating.rating_date >= filters.from_date)
        
        if filters.to_date:
            conditions.append(Rating.rating_date <= filters.to_date)
        
        if filters.is_expired is not None:
            now = datetime.now(timezone.utc)
            if filters.is_expired:
                conditions.append(Rating.expiry_date < now)
            else:
                conditions.append(or_(Rating.expiry_date.is_(None), Rating.expiry_date >= now))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    async def _get_rating_stats(self, stock_id: str, rating_type: RatingType) -> RatingStats:
        """Get statistics for a specific rating type."""
        query = select(Rating).where(
            and_(Rating.stock_id == stock_id, Rating.rating_type == rating_type)
        )
        
        result = await self.db.execute(query)
        ratings = result.scalars().all()
        
        if not ratings:
            return RatingStats(
                count=0,
                average_score=None,
                median_score=None,
                score_distribution={},
                recommendation_distribution={},
                bullish_percentage=None,
                bearish_percentage=None,
            )
        
        scores = [float(rating.score) for rating in ratings]
        recommendations = [rating.recommendation for rating in ratings]
        
        # Calculate statistics
        count = len(ratings)
        average_score = Decimal(str(sum(scores) / count))
        median_score = Decimal(str(sorted(scores)[count // 2]))
        
        # Score distribution
        score_dist = {}
        for score in scores:
            score_range = f"{int(score)}-{int(score)+1}"
            score_dist[score_range] = score_dist.get(score_range, 0) + 1
        
        # Recommendation distribution
        rec_dist = {}
        for rec in recommendations:
            rec_dist[rec.value] = rec_dist.get(rec.value, 0) + 1
        
        # Bullish/bearish percentages
        bullish_count = sum(1 for rating in ratings if rating.is_bullish)
        bearish_count = sum(1 for rating in ratings if rating.is_bearish)
        
        return RatingStats(
            count=count,
            average_score=average_score,
            median_score=median_score,
            score_distribution=score_dist,
            recommendation_distribution=rec_dist,
            bullish_percentage=Decimal(str(bullish_count / count * 100)),
            bearish_percentage=Decimal(str(bearish_count / count * 100)),
        )
    
    async def _calculate_overall_recommendation(self, stock_id: str) -> RecommendationType:
        """Calculate overall recommendation for a stock."""
        # Get latest expert and popular ratings
        expert_query = select(Rating).where(
            and_(Rating.stock_id == stock_id, Rating.rating_type == RatingType.EXPERT)
        ).order_by(desc(Rating.rating_date)).limit(10)
        
        popular_query = select(Rating).where(
            and_(Rating.stock_id == stock_id, Rating.rating_type == RatingType.POPULAR)
        ).order_by(desc(Rating.rating_date)).limit(5)
        
        expert_result = await self.db.execute(expert_query)
        expert_ratings = expert_result.scalars().all()
        
        popular_result = await self.db.execute(popular_query)
        popular_ratings = popular_result.scalars().all()
        
        # Weight expert ratings higher
        expert_weight = 0.7
        popular_weight = 0.3
        
        all_ratings = []
        for rating in expert_ratings:
            all_ratings.extend([rating.recommendation] * int(expert_weight * 10))
        for rating in popular_ratings:
            all_ratings.extend([rating.recommendation] * int(popular_weight * 10))
        
        if not all_ratings:
            return RecommendationType.HOLD
        
        # Count recommendations and return most common
        from collections import Counter
        counter = Counter(all_ratings)
        return counter.most_common(1)[0][0]
    
    async def _calculate_overall_score(self, stock_id: str) -> Decimal:
        """Calculate overall weighted score for a stock."""
        # Similar to recommendation but for scores
        expert_query = select(Rating.score).where(
            and_(Rating.stock_id == stock_id, Rating.rating_type == RatingType.EXPERT)
        ).order_by(desc(Rating.rating_date)).limit(10)
        
        popular_query = select(Rating.score).where(
            and_(Rating.stock_id == stock_id, Rating.rating_type == RatingType.POPULAR)
        ).order_by(desc(Rating.rating_date)).limit(5)
        
        expert_result = await self.db.execute(expert_query)
        expert_scores = expert_result.scalars().all()
        
        popular_result = await self.db.execute(popular_query)
        popular_scores = popular_result.scalars().all()
        
        if not expert_scores and not popular_scores:
            return Decimal("0.00")
        
        # Weighted average
        total_weight = 0
        weighted_sum = Decimal("0")
        
        for score in expert_scores:
            weighted_sum += score * Decimal("0.7")
            total_weight += 0.7
        
        for score in popular_scores:
            weighted_sum += score * Decimal("0.3")
            total_weight += 0.3
        
        return weighted_sum / Decimal(str(total_weight)) if total_weight > 0 else Decimal("0.00")
    
    def _to_response(self, rating: Rating) -> RatingResponse:
        """Convert Rating model to response schema."""
        return RatingResponse(
            id=rating.id,
            stock_id=rating.stock_id,
            expert_id=rating.expert_id,
            rating_type=rating.rating_type,
            score=rating.score,
            recommendation=rating.recommendation,
            confidence=rating.confidence,
            price_target=rating.price_target,
            price_at_rating=rating.price_at_rating,
            summary=rating.summary,
            analysis=rating.analysis,
            risks=rating.risks,
            catalysts=rating.catalysts,
            rating_date=rating.rating_date,
            expiry_date=rating.expiry_date,
            last_updated=rating.last_updated,
            sample_size=rating.sample_size,
            sentiment_sources=rating.sentiment_sources,
            created_at=rating.created_at,
            updated_at=rating.updated_at,
            is_bullish=rating.is_bullish,
            is_bearish=rating.is_bearish,
            is_expert_rating=rating.is_expert_rating,
            is_popular_rating=rating.is_popular_rating,
            score_percentage=rating.score_percentage,
            recommendation_display=rating.recommendation_display,
        )