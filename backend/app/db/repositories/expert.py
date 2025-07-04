"""
Expert repository for database operations.

This module provides expert-specific database operations including
CRUD operations, verification management, and expert performance analysis.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.expert import Expert
from ..exceptions import NotFoundError, ValidationError, DatabaseErrorHandler
from .base import BaseRepository

logger = logging.getLogger(__name__)


class ExpertRepository(BaseRepository[Expert]):
    """Repository for expert-related database operations."""
    
    def get_model_class(self) -> type[Expert]:
        """Get the Expert model class."""
        return Expert
    
    def get_unique_fields(self) -> List[str]:
        """Get unique fields for Expert model."""
        return ["email"]
    
    # Expert-specific queries
    
    async def get_by_email(self, email: str) -> Optional[Expert]:
        """
        Get expert by email address.
        
        Args:
            email: Expert email address
        
        Returns:
            Expert instance or None if not found
        """
        return await self.get_by_field("email", email.lower())
    
    async def get_by_name(self, name: str) -> Optional[Expert]:
        """
        Get expert by name.
        
        Args:
            name: Expert name
        
        Returns:
            Expert instance or None if not found
        """
        return await self.get_by_field("name", name)
    
    async def get_with_ratings(self, expert_id: str) -> Optional[Expert]:
        """
        Get expert with all their ratings loaded.
        
        Args:
            expert_id: Expert ID
        
        Returns:
            Expert instance with ratings or None if not found
        """
        return await self.get_by_id(
            expert_id,
            options=[selectinload(Expert.ratings)]
        )
    
    async def get_verified_experts(
        self, 
        limit: Optional[int] = None
    ) -> List[Expert]:
        """
        Get all verified experts.
        
        Args:
            limit: Maximum number of experts to return
        
        Returns:
            List of verified experts
        """
        return await self.filter(
            filters={"is_verified": True, "is_active": True},
            limit=limit,
            order_by="name"
        )
    
    async def get_by_institution(
        self, 
        institution: str, 
        limit: Optional[int] = None
    ) -> List[Expert]:
        """
        Get experts by institution.
        
        Args:
            institution: Institution name
            limit: Maximum number of experts to return
        
        Returns:
            List of experts from the institution
        """
        return await self.filter(
            filters={"institution": {"ilike": f"%{institution}%"}},
            limit=limit,
            order_by="name"
        )
    
    async def search_experts(
        self, 
        query: str, 
        limit: int = 20
    ) -> List[Expert]:
        """
        Search experts by name, institution, or specializations.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching experts
        """
        async with DatabaseErrorHandler("Searching experts"):
            stmt = select(Expert).where(
                and_(
                    Expert.is_active == True,
                    or_(
                        Expert.name.ilike(f"%{query}%"),
                        Expert.institution.ilike(f"%{query}%"),
                        Expert.specializations.ilike(f"%{query}%")
                    )
                )
            ).order_by(
                Expert.is_verified.desc(),
                Expert.name
            ).limit(limit)
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_by_specialization(
        self, 
        specialization: str,
        limit: Optional[int] = None
    ) -> List[Expert]:
        """
        Get experts by specialization.
        
        Args:
            specialization: Specialization area
            limit: Maximum number of experts to return
        
        Returns:
            List of experts with the specialization
        """
        return await self.filter(
            filters={
                "specializations": {"ilike": f"%{specialization}%"},
                "is_active": True
            },
            limit=limit,
            order_by="name"
        )
    
    async def get_top_rated_experts(
        self, 
        limit: int = 10,
        min_ratings: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top-rated experts based on their rating performance.
        
        Args:
            limit: Number of experts to return
            min_ratings: Minimum number of ratings required
        
        Returns:
            List of expert performance summaries
        """
        async with DatabaseErrorHandler("Getting top-rated experts"):
            from ..models.rating import Rating
            
            stmt = (
                select(
                    Expert,
                    func.count(Rating.id).label("rating_count"),
                    func.avg(Rating.score).label("avg_score"),
                    func.avg(Rating.confidence).label("avg_confidence")
                )
                .join(Rating)
                .where(Expert.is_active == True)
                .group_by(Expert.id)
                .having(func.count(Rating.id) >= min_ratings)
                .order_by(func.avg(Rating.score).desc())
                .limit(limit)
            )
            
            result = await self.session.execute(stmt)
            
            return [
                {
                    "expert": row.Expert,
                    "rating_count": row.rating_count,
                    "avg_score": float(row.avg_score) if row.avg_score else 0,
                    "avg_confidence": float(row.avg_confidence) if row.avg_confidence else 0
                }
                for row in result.fetchall()
            ]
    
    # Expert management operations
    
    async def verify_expert(self, expert_id: str) -> Optional[Expert]:
        """
        Verify an expert.
        
        Args:
            expert_id: Expert ID
        
        Returns:
            Updated expert instance or None if not found
        """
        async with DatabaseErrorHandler(f"Verifying expert {expert_id}"):
            expert = await self.get_by_id(expert_id)
            if not expert:
                return None
            
            expert.verify()
            await self.session.flush()
            await self.session.refresh(expert)
            
            logger.info(f"Verified expert: {expert.name}")
            return expert
    
    async def deactivate_expert(self, expert_id: str) -> Optional[Expert]:
        """
        Deactivate an expert.
        
        Args:
            expert_id: Expert ID
        
        Returns:
            Updated expert instance or None if not found
        """
        async with DatabaseErrorHandler(f"Deactivating expert {expert_id}"):
            expert = await self.get_by_id(expert_id)
            if not expert:
                return None
            
            expert.is_active = False
            await self.session.flush()
            await self.session.refresh(expert)
            
            logger.info(f"Deactivated expert: {expert.name}")
            return expert
    
    async def update_expert_stats(self, expert_id: str) -> Optional[Expert]:
        """
        Update expert statistics based on their ratings.
        
        Args:
            expert_id: Expert ID
        
        Returns:
            Updated expert instance or None if not found
        """
        async with DatabaseErrorHandler(f"Updating expert stats for {expert_id}"):
            from ..models.rating import Rating
            
            expert = await self.get_by_id(expert_id)
            if not expert:
                return None
            
            # Calculate statistics from ratings
            stats = await self.session.execute(
                select(
                    func.count(Rating.id).label("total_ratings"),
                    func.avg(Rating.score).label("avg_accuracy"),
                    func.avg(Rating.confidence).label("avg_confidence")
                )
                .where(Rating.expert_id == expert_id)
            )
            
            stats_row = stats.fetchone()
            
            if stats_row and stats_row.total_ratings > 0:
                expert.total_ratings = stats_row.total_ratings
                expert.avg_accuracy = Decimal(str(stats_row.avg_accuracy))
                
                await self.session.flush()
                await self.session.refresh(expert)
            
            logger.info(f"Updated stats for expert: {expert.name}")
            return expert
    
    async def upsert_expert(
        self,
        name: str,
        email: str,
        institution: Optional[str] = None,
        **kwargs
    ) -> Expert:
        """
        Insert or update expert information.
        
        Args:
            name: Expert name
            email: Expert email
            institution: Institution name
            **kwargs: Additional expert data
        
        Returns:
            Expert instance
        """
        data = {
            "name": name,
            "email": email.lower(),
            "institution": institution,
            **kwargs
        }
        
        return await self.upsert(
            constraint_fields=["email"],
            **data
        )
    
    # Analytics and performance tracking
    
    async def get_expert_performance(
        self, 
        expert_id: str,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get detailed performance metrics for an expert.
        
        Args:
            expert_id: Expert ID
            days: Number of days to look back (None for all time)
        
        Returns:
            Performance metrics dictionary
        """
        async with DatabaseErrorHandler(f"Getting performance for expert {expert_id}"):
            from ..models.rating import Rating, RecommendationType
            
            expert = await self.get_by_id(expert_id)
            if not expert:
                raise NotFoundError(f"Expert with ID {expert_id} not found")
            
            # Build date filter if specified
            date_filter = []
            if days:
                threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
                date_filter.append(Rating.rating_date >= threshold_date)
            
            # Overall statistics
            overall_stats = await self.session.execute(
                select(
                    func.count(Rating.id).label("total_ratings"),
                    func.avg(Rating.score).label("avg_score"),
                    func.avg(Rating.confidence).label("avg_confidence")
                )
                .where(
                    and_(
                        Rating.expert_id == expert_id,
                        *date_filter
                    )
                )
            )
            
            overall = overall_stats.fetchone()
            
            # Recommendation breakdown
            rec_breakdown = await self.session.execute(
                select(
                    Rating.recommendation,
                    func.count(Rating.id).label("count")
                )
                .where(
                    and_(
                        Rating.expert_id == expert_id,
                        *date_filter
                    )
                )
                .group_by(Rating.recommendation)
            )
            
            recommendations = {rec.recommendation.value: rec.count for rec in rec_breakdown.fetchall()}
            
            # Recent activity (last 30 days)
            recent_threshold = datetime.now(timezone.utc) - timedelta(days=30)
            recent_activity = await self.session.execute(
                select(func.count(Rating.id))
                .where(
                    and_(
                        Rating.expert_id == expert_id,
                        Rating.rating_date >= recent_threshold
                    )
                )
            )
            
            return {
                "expert_id": expert_id,
                "expert_name": expert.name,
                "total_ratings": overall.total_ratings or 0,
                "avg_score": float(overall.avg_score) if overall.avg_score else 0,
                "avg_confidence": float(overall.avg_confidence) if overall.avg_confidence else 0,
                "recommendation_breakdown": recommendations,
                "recent_activity_30d": recent_activity.scalar() or 0,
                "is_verified": expert.is_verified,
                "is_active": expert.is_active
            }
    
    async def get_institution_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary statistics by institution.
        
        Returns:
            List of institution summaries
        """
        async with DatabaseErrorHandler("Getting institution summary"):
            stmt = (
                select(
                    Expert.institution,
                    func.count(Expert.id).label("expert_count"),
                    func.sum(func.case((Expert.is_verified == True, 1), else_=0)).label("verified_count"),
                    func.avg(Expert.avg_accuracy).label("avg_accuracy")
                )
                .where(Expert.is_active == True)
                .group_by(Expert.institution)
                .order_by(func.count(Expert.id).desc())
            )
            
            result = await self.session.execute(stmt)
            
            return [
                {
                    "institution": row.institution,
                    "expert_count": row.expert_count,
                    "verified_count": row.verified_count or 0,
                    "avg_accuracy": float(row.avg_accuracy) if row.avg_accuracy else 0
                }
                for row in result.fetchall()
            ]
    
    async def get_experts_needing_verification(self) -> List[Expert]:
        """
        Get experts that need verification.
        
        Returns:
            List of unverified active experts
        """
        return await self.filter(
            filters={
                "is_verified": False,
                "is_active": True
            },
            order_by="created_at"
        )
    
    # Validation
    
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate expert creation data."""
        # Ensure email is lowercase
        if "email" in data:
            data["email"] = data["email"].lower()
        
        # Validate required fields
        required_fields = ["name", "email"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate email format (basic validation)
        if "email" in data and "@" not in data["email"]:
            raise ValidationError("Invalid email format")
        
        # Validate years_experience
        if "years_experience" in data and data["years_experience"] is not None:
            if not isinstance(data["years_experience"], int) or data["years_experience"] < 0:
                raise ValidationError("Years of experience must be a non-negative integer")
        
        # Validate avg_accuracy
        if "avg_accuracy" in data and data["avg_accuracy"] is not None:
            if not isinstance(data["avg_accuracy"], (int, float, Decimal)):
                raise ValidationError("Average accuracy must be a number")
            if not (0 <= float(data["avg_accuracy"]) <= 1):
                raise ValidationError("Average accuracy must be between 0 and 1")
        
        return data
    
    def validate_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate expert update data."""
        # Don't allow email updates (would break uniqueness)
        if "email" in data:
            raise ValidationError("Expert email cannot be updated")
        
        # Validate years_experience
        if "years_experience" in data and data["years_experience"] is not None:
            if not isinstance(data["years_experience"], int) or data["years_experience"] < 0:
                raise ValidationError("Years of experience must be a non-negative integer")
        
        # Validate avg_accuracy
        if "avg_accuracy" in data and data["avg_accuracy"] is not None:
            if not isinstance(data["avg_accuracy"], (int, float, Decimal)):
                raise ValidationError("Average accuracy must be a number")
            if not (0 <= float(data["avg_accuracy"]) <= 1):
                raise ValidationError("Average accuracy must be between 0 and 1")
        
        return data