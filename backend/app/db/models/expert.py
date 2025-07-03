"""
Expert model for storing expert analyst information.

Represents financial experts, analysts, and institutions that provide
professional stock ratings and recommendations.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class Expert(BaseModel):
    """
    Expert model representing financial analysts and institutions.
    
    Stores information about experts who provide professional ratings
    and analysis for stocks in the system.
    """
    
    __tablename__ = "experts"
    
    # Basic expert information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Expert or institution name",
    )
    
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Professional title or role",
    )
    
    institution: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Institution or company name",
    )
    
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Expert biography or description",
    )
    
    # Contact and social information
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact email",
    )
    
    website: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Professional website or profile URL",
    )
    
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="LinkedIn profile URL",
    )
    
    twitter_handle: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Twitter handle (without @)",
    )
    
    # Professional credentials
    years_experience: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Years of experience in financial analysis",
    )
    
    specializations: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Areas of specialization (JSON array of sectors/industries)",
    )
    
    certifications: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Professional certifications (CFA, CPA, etc.)",
    )
    
    # Rating and reputation metrics
    total_ratings: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Total number of ratings provided",
    )
    
    accuracy_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Historical accuracy score (0.0 to 1.0)",
    )
    
    avg_rating_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Average rating score given by this expert",
    )
    
    follower_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of followers/subscribers",
    )
    
    # Status and verification
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the expert is verified by our platform",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the expert is currently active",
    )
    
    verification_date: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when expert was verified",
    )
    
    # Relationships
    ratings: Mapped[List["Rating"]] = relationship(
        "Rating",
        back_populates="expert",
        cascade="all, delete-orphan",
    )
    
    def __init__(self, **kwargs):
        """Initialize Expert model with proper defaults."""
        # Set default values if not provided
        if 'total_ratings' not in kwargs:
            kwargs['total_ratings'] = 0
        if 'follower_count' not in kwargs:
            kwargs['follower_count'] = 0
        if 'is_verified' not in kwargs:
            kwargs['is_verified'] = False
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        
        # Call parent constructor (BaseModel handles ID and timestamps)
        super().__init__(**kwargs)
    
    # Computed properties
    @property
    def display_name(self) -> str:
        """Get display name combining name and institution."""
        if self.institution:
            return f"{self.name} ({self.institution})"
        return self.name
    
    @property
    def reputation_level(self) -> str:
        """Get reputation level based on metrics."""
        if not self.accuracy_score or self.total_ratings < 10:
            return "New"
        elif self.accuracy_score >= 0.8 and self.total_ratings >= 100:
            return "Expert"
        elif self.accuracy_score >= 0.7 and self.total_ratings >= 50:
            return "Experienced"
        elif self.accuracy_score >= 0.6:
            return "Intermediate"
        else:
            return "Developing"
    
    @property
    def expertise_areas(self) -> List[str]:
        """Get list of expertise areas from specializations JSON."""
        if self.specializations:
            try:
                import json
                return json.loads(self.specializations)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def add_specialization(self, area: str) -> None:
        """Add a new area of specialization."""
        areas = self.expertise_areas
        if area not in areas:
            areas.append(area)
            import json
            self.specializations = json.dumps(areas)
    
    def update_metrics(
        self,
        total_ratings: Optional[int] = None,
        accuracy_score: Optional[float] = None,
        avg_rating_score: Optional[float] = None,
        follower_count: Optional[int] = None,
    ) -> None:
        """Update expert performance metrics."""
        if total_ratings is not None:
            self.total_ratings = total_ratings
        if accuracy_score is not None:
            self.accuracy_score = max(0.0, min(1.0, accuracy_score))  # Clamp 0-1
        if avg_rating_score is not None:
            self.avg_rating_score = avg_rating_score
        if follower_count is not None:
            self.follower_count = max(0, follower_count)  # Non-negative
    
    def verify(self) -> None:
        """Mark expert as verified."""
        self.is_verified = True
        self.verification_date = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<Expert(name='{self.name}', institution='{self.institution}', verified={self.is_verified})>"


# Database indexes for optimal query performance
Index("idx_experts_name", Expert.name)
Index("idx_experts_institution", Expert.institution)
Index("idx_experts_verified", Expert.is_verified)
Index("idx_experts_active", Expert.is_active)
Index("idx_experts_accuracy", Expert.accuracy_score)
Index("idx_experts_total_ratings", Expert.total_ratings)

# Composite indexes for common query patterns
Index("idx_experts_verified_active", Expert.is_verified, Expert.is_active)
Index("idx_experts_reputation", Expert.is_verified, Expert.accuracy_score, Expert.total_ratings)