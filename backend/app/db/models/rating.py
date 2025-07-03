"""
Rating model for storing stock ratings and recommendations.

Represents both expert and aggregated popular ratings for stocks,
including historical data and sentiment analysis.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class RatingType(PyEnum):
    """Types of ratings in the system."""
    EXPERT = "expert"  # Professional analyst rating
    POPULAR = "popular"  # Aggregated social sentiment rating
    HISTORICAL = "historical"  # Historical rating snapshot


class RecommendationType(PyEnum):
    """Stock recommendation types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class Rating(BaseModel):
    """
    Rating model representing stock ratings and recommendations.
    
    Stores individual expert ratings and aggregated popular sentiment
    ratings for stocks, with historical tracking capabilities.
    """
    
    __tablename__ = "ratings"
    
    # Foreign key relationships
    stock_id: Mapped[str] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the stock being rated",
    )
    
    expert_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("experts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to expert who provided rating (null for popular ratings)",
    )
    
    # Rating information
    rating_type: Mapped[RatingType] = mapped_column(
        Enum(RatingType),
        nullable=False,
        comment="Type of rating (expert, popular, historical)",
    )
    
    score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        comment="Rating score from 0.00 to 5.00 (like Rotten Tomatoes)",
    )
    
    recommendation: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType),
        nullable=False,
        comment="Buy/sell recommendation",
    )
    
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Confidence level in the rating (0.00 to 1.00)",
    )
    
    # Target and pricing information
    price_target: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Price target for the stock",
    )
    
    price_at_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Stock price when rating was made",
    )
    
    # Detailed analysis
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Brief summary of the rating rationale",
    )
    
    analysis: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed analysis supporting the rating",
    )
    
    risks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Key risks identified",
    )
    
    catalysts: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Potential catalysts for price movement",
    )
    
    # Time-based information
    rating_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Date when rating was issued",
    )
    
    expiry_date: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when rating expires",
    )
    
    last_updated: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when rating was last updated",
    )
    
    # Metadata for popular ratings
    sample_size: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Number of social posts/opinions aggregated (for popular ratings)",
    )
    
    sentiment_sources: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Sources used for sentiment analysis (Reddit, Twitter, etc.)",
    )
    
    # Relationships
    stock: Mapped["Stock"] = relationship(
        "Stock",
        back_populates="ratings",
    )
    
    expert: Mapped[Optional["Expert"]] = relationship(
        "Expert",
        back_populates="ratings",
    )
    
    # Computed properties
    @property
    def is_bullish(self) -> bool:
        """Check if rating is bullish (buy recommendation)."""
        return self.recommendation in [RecommendationType.BUY, RecommendationType.STRONG_BUY]
    
    @property
    def is_bearish(self) -> bool:
        """Check if rating is bearish (sell recommendation)."""
        return self.recommendation in [RecommendationType.SELL, RecommendationType.STRONG_SELL]
    
    @property
    def is_expert_rating(self) -> bool:
        """Check if this is an expert rating."""
        return self.rating_type == RatingType.EXPERT
    
    @property
    def is_popular_rating(self) -> bool:
        """Check if this is a popular sentiment rating."""
        return self.rating_type == RatingType.POPULAR
    
    @property
    def score_percentage(self) -> int:
        """Get score as percentage (0-100)."""
        return int((self.score / Decimal('5.0')) * 100)
    
    @property
    def recommendation_display(self) -> str:
        """Get display-friendly recommendation text."""
        return self.recommendation.value.replace("_", " ").title()
    
    def update_rating(
        self,
        score: Optional[Decimal] = None,
        recommendation: Optional[RecommendationType] = None,
        confidence: Optional[Decimal] = None,
        price_target: Optional[Decimal] = None,
        summary: Optional[str] = None,
        analysis: Optional[str] = None,
    ) -> None:
        """Update rating information."""
        if score is not None:
            self.score = max(Decimal("0.00"), min(Decimal("5.00"), score))
        if recommendation is not None:
            self.recommendation = recommendation
        if confidence is not None:
            self.confidence = max(Decimal("0.00"), min(Decimal("1.00"), confidence))
        if price_target is not None:
            self.price_target = price_target
        if summary is not None:
            self.summary = summary
        if analysis is not None:
            self.analysis = analysis
        
        self.last_updated = datetime.utcnow()
    
    def __repr__(self) -> str:
        expert_name = self.expert.name if self.expert else "Popular"
        return f"<Rating(stock='{self.stock.symbol}', expert='{expert_name}', score={self.score}, recommendation='{self.recommendation.value}')>"


# Database indexes for optimal query performance
Index("idx_ratings_stock", Rating.stock_id)
Index("idx_ratings_expert", Rating.expert_id)
Index("idx_ratings_type", Rating.rating_type)
Index("idx_ratings_recommendation", Rating.recommendation)
Index("idx_ratings_score", Rating.score)
Index("idx_ratings_date", Rating.rating_date)

# Composite indexes for common query patterns
Index("idx_ratings_stock_type", Rating.stock_id, Rating.rating_type)
Index("idx_ratings_stock_date", Rating.stock_id, Rating.rating_date)
Index("idx_ratings_expert_date", Rating.expert_id, Rating.rating_date)
Index("idx_ratings_type_score", Rating.rating_type, Rating.score)

# Unique constraints
UniqueConstraint(
    "stock_id", "expert_id", "rating_date",
    name="uq_ratings_stock_expert_date",
)