"""
Rating Pydantic schemas for request/response validation.

Defines schemas for rating creation, updates, and API responses.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class RatingType(str, Enum):
    """Types of ratings in the system."""
    EXPERT = "expert"
    POPULAR = "popular"
    HISTORICAL = "historical"


class RecommendationType(str, Enum):
    """Stock recommendation types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class RatingBase(BaseModel):
    """Base rating schema with common fields."""
    
    rating_type: RatingType = Field(..., description="Type of rating")
    score: Decimal = Field(..., ge=0, le=5, description="Rating score from 0.00 to 5.00")
    recommendation: RecommendationType = Field(..., description="Buy/sell recommendation")
    confidence: Optional[Decimal] = Field(None, ge=0, le=1, description="Confidence level (0.00 to 1.00)")
    price_target: Optional[Decimal] = Field(None, gt=0, description="Price target for the stock")
    summary: Optional[str] = Field(None, max_length=1000, description="Brief summary of rating rationale")
    analysis: Optional[str] = Field(None, description="Detailed analysis supporting the rating")
    risks: Optional[str] = Field(None, description="Key risks identified")
    catalysts: Optional[str] = Field(None, description="Potential catalysts for price movement")
    
    @validator('score')
    def validate_score(cls, v):
        """Ensure score is within valid range with 2 decimal places."""
        return round(Decimal(str(v)), 2)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is within valid range with 2 decimal places."""
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v


class RatingCreate(RatingBase):
    """Schema for creating a new rating."""
    
    stock_id: str = Field(..., description="ID of the stock being rated")
    expert_id: Optional[str] = Field(None, description="ID of expert (null for popular ratings)")
    price_at_rating: Optional[Decimal] = Field(None, gt=0, description="Stock price when rating was made")
    rating_date: datetime = Field(..., description="Date when rating was issued")
    expiry_date: Optional[datetime] = Field(None, description="Date when rating expires")
    sample_size: Optional[int] = Field(None, ge=1, description="Sample size for popular ratings")
    sentiment_sources: Optional[str] = Field(None, max_length=500, description="Sources for sentiment analysis")
    
    @validator('expiry_date')
    def expiry_after_rating_date(cls, v, values):
        """Ensure expiry date is after rating date."""
        if v is not None and 'rating_date' in values and values['rating_date'] is not None:
            if v <= values['rating_date']:
                raise ValueError('expiry_date must be after rating_date')
        return v
    
    @validator('expert_id')
    def expert_id_for_expert_rating(cls, v, values):
        """Ensure expert_id is provided for expert ratings."""
        if 'rating_type' in values:
            if values['rating_type'] == RatingType.EXPERT and v is None:
                raise ValueError('expert_id is required for expert ratings')
            elif values['rating_type'] == RatingType.POPULAR and v is not None:
                raise ValueError('expert_id should be null for popular ratings')
        return v


class RatingUpdate(BaseModel):
    """Schema for updating an existing rating."""
    
    score: Optional[Decimal] = Field(None, ge=0, le=5)
    recommendation: Optional[RecommendationType] = None
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    price_target: Optional[Decimal] = Field(None, gt=0)
    summary: Optional[str] = Field(None, max_length=1000)
    analysis: Optional[str] = None
    risks: Optional[str] = None
    catalysts: Optional[str] = None
    expiry_date: Optional[datetime] = None
    
    @validator('score')
    def validate_score(cls, v):
        """Ensure score is within valid range with 2 decimal places."""
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is within valid range with 2 decimal places."""
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v


class RatingResponse(RatingBase):
    """Schema for rating API responses."""
    
    id: str = Field(..., description="Rating ID")
    stock_id: str = Field(..., description="Stock ID")
    expert_id: Optional[str] = Field(None, description="Expert ID")
    price_at_rating: Optional[Decimal] = Field(None, description="Stock price when rating was made")
    rating_date: datetime = Field(..., description="Date when rating was issued")
    expiry_date: Optional[datetime] = Field(None, description="Date when rating expires")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    sample_size: Optional[int] = Field(None, description="Sample size for popular ratings")
    sentiment_sources: Optional[str] = Field(None, description="Sources for sentiment analysis")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    
    # Computed fields
    is_bullish: bool = Field(..., description="Whether rating is bullish")
    is_bearish: bool = Field(..., description="Whether rating is bearish")
    is_expert_rating: bool = Field(..., description="Whether this is an expert rating")
    is_popular_rating: bool = Field(..., description="Whether this is a popular rating")
    score_percentage: int = Field(..., description="Score as percentage (0-100)")
    recommendation_display: str = Field(..., description="Display-friendly recommendation text")
    
    class Config:
        from_attributes = True


class RatingWithRelations(RatingResponse):
    """Rating response with related stock and expert information."""
    
    stock: Optional[dict] = Field(None, description="Related stock information")
    expert: Optional[dict] = Field(None, description="Related expert information")


class RatingListResponse(BaseModel):
    """Schema for paginated rating list responses."""
    
    ratings: List[RatingResponse] = Field(..., description="List of ratings")
    total: int = Field(..., description="Total number of ratings")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class RatingSearch(BaseModel):
    """Schema for rating search parameters."""
    
    stock_id: Optional[str] = Field(None, description="Filter by stock ID")
    expert_id: Optional[str] = Field(None, description="Filter by expert ID")
    rating_type: Optional[RatingType] = Field(None, description="Filter by rating type")
    recommendation: Optional[RecommendationType] = Field(None, description="Filter by recommendation")
    min_score: Optional[Decimal] = Field(None, ge=0, le=5, description="Minimum score filter")
    max_score: Optional[Decimal] = Field(None, ge=0, le=5, description="Maximum score filter")
    min_confidence: Optional[Decimal] = Field(None, ge=0, le=1, description="Minimum confidence filter")
    from_date: Optional[datetime] = Field(None, description="Filter ratings from this date")
    to_date: Optional[datetime] = Field(None, description="Filter ratings to this date")
    is_expired: Optional[bool] = Field(None, description="Filter by expiry status")
    
    @validator('max_score')
    def max_score_greater_than_min(cls, v, values):
        """Ensure max_score is greater than min_score if both provided."""
        if v is not None and 'min_score' in values and values['min_score'] is not None:
            if v <= values['min_score']:
                raise ValueError('max_score must be greater than min_score')
        return v
    
    @validator('to_date')
    def to_date_after_from_date(cls, v, values):
        """Ensure to_date is after from_date if both provided."""
        if v is not None and 'from_date' in values and values['from_date'] is not None:
            if v <= values['from_date']:
                raise ValueError('to_date must be after from_date')
        return v


class RatingAggregation(BaseModel):
    """Schema for rating aggregation responses."""
    
    stock_id: str = Field(..., description="Stock ID")
    expert_ratings: "RatingStats" = Field(..., description="Expert ratings statistics")
    popular_ratings: "RatingStats" = Field(..., description="Popular ratings statistics")
    overall_recommendation: RecommendationType = Field(..., description="Overall recommendation")
    overall_score: Decimal = Field(..., description="Overall aggregated score")
    total_ratings: int = Field(..., description="Total number of ratings")
    last_updated: datetime = Field(..., description="Last update timestamp")


class RatingStats(BaseModel):
    """Schema for rating statistics."""
    
    count: int = Field(..., description="Number of ratings")
    average_score: Optional[Decimal] = Field(None, description="Average score")
    median_score: Optional[Decimal] = Field(None, description="Median score")
    score_distribution: dict = Field(default_factory=dict, description="Score distribution")
    recommendation_distribution: dict = Field(default_factory=dict, description="Recommendation distribution")
    bullish_percentage: Optional[Decimal] = Field(None, description="Percentage of bullish ratings")
    bearish_percentage: Optional[Decimal] = Field(None, description="Percentage of bearish ratings")


class RatingHistory(BaseModel):
    """Schema for historical rating data."""
    
    stock_id: str = Field(..., description="Stock ID")
    rating_type: RatingType = Field(..., description="Type of ratings")
    period: str = Field(..., description="Time period (daily, weekly, monthly)")
    data_points: List["RatingHistoryPoint"] = Field(..., description="Historical data points")


class RatingHistoryPoint(BaseModel):
    """Schema for a single historical rating data point."""
    
    date: datetime = Field(..., description="Date of the data point")
    average_score: Decimal = Field(..., description="Average score for the period")
    rating_count: int = Field(..., description="Number of ratings in the period")
    recommendation_distribution: dict = Field(default_factory=dict, description="Recommendation distribution")


class RatingBulkCreate(BaseModel):
    """Schema for bulk rating creation."""
    
    ratings: List[RatingCreate] = Field(..., min_items=1, max_items=100, description="List of ratings to create")


class RatingBulkResponse(BaseModel):
    """Schema for bulk operation responses."""
    
    created: int = Field(..., description="Number of ratings created")
    updated: int = Field(..., description="Number of ratings updated")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    ratings: List[RatingResponse] = Field(default_factory=list, description="Successfully processed ratings")


# Forward references for circular imports
# These will be imported when needed to avoid circular imports