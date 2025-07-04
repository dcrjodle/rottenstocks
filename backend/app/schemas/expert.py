"""
Expert Pydantic schemas for request/response validation.

Defines schemas for expert creation, updates, and API responses.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator, EmailStr


class ExpertBase(BaseModel):
    """Base expert schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Expert or institution name")
    title: Optional[str] = Field(None, max_length=255, description="Professional title or role")
    institution: Optional[str] = Field(None, max_length=255, description="Institution or company name")
    bio: Optional[str] = Field(None, description="Expert biography or description")
    website: Optional[str] = Field(None, max_length=500, description="Professional website or profile URL")
    linkedin_url: Optional[str] = Field(None, max_length=500, description="LinkedIn profile URL")
    twitter_handle: Optional[str] = Field(None, max_length=100, description="Twitter handle (without @)")
    years_experience: Optional[int] = Field(None, ge=0, description="Years of experience in financial analysis")
    specializations: Optional[List[str]] = Field(None, description="Areas of specialization")
    certifications: Optional[List[str]] = Field(None, description="Professional certifications")
    
    @validator('twitter_handle')
    def clean_twitter_handle(cls, v):
        """Remove @ symbol if present."""
        if v:
            return v.lstrip('@')
        return v
    
    @validator('linkedin_url', 'website')
    def validate_url(cls, v):
        """Basic URL validation."""
        if v and not v.startswith(('http://', 'https://')):
            return f"https://{v}"
        return v


class ExpertCreate(ExpertBase):
    """Schema for creating a new expert."""
    
    email: EmailStr = Field(..., description="Contact email")
    is_verified: bool = Field(False, description="Whether the expert is verified")
    is_active: bool = Field(True, description="Whether the expert is currently active")
    follower_count: int = Field(0, ge=0, description="Number of followers/subscribers")


class ExpertUpdate(BaseModel):
    """Schema for updating an existing expert."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    institution: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    years_experience: Optional[int] = Field(None, ge=0)
    specializations: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    is_active: Optional[bool] = None
    follower_count: Optional[int] = Field(None, ge=0)
    
    @validator('twitter_handle')
    def clean_twitter_handle(cls, v):
        """Remove @ symbol if present."""
        if v:
            return v.lstrip('@')
        return v
    
    @validator('linkedin_url', 'website')
    def validate_url(cls, v):
        """Basic URL validation."""
        if v and not v.startswith(('http://', 'https://')):
            return f"https://{v}"
        return v


class ExpertMetricsUpdate(BaseModel):
    """Schema for updating expert performance metrics."""
    
    total_ratings: Optional[int] = Field(None, ge=0, description="Total number of ratings provided")
    accuracy_score: Optional[float] = Field(None, ge=0, le=1, description="Historical accuracy score")
    avg_rating_score: Optional[float] = Field(None, ge=0, le=5, description="Average rating score")
    follower_count: Optional[int] = Field(None, ge=0, description="Number of followers")


class ExpertResponse(ExpertBase):
    """Schema for expert API responses."""
    
    id: str = Field(..., description="Expert ID")
    email: str = Field(..., description="Contact email")
    total_ratings: int = Field(..., description="Total number of ratings provided")
    accuracy_score: Optional[float] = Field(None, description="Historical accuracy score")
    avg_rating_score: Optional[float] = Field(None, description="Average rating score")
    follower_count: int = Field(..., description="Number of followers/subscribers")
    is_verified: bool = Field(..., description="Whether the expert is verified")
    is_active: bool = Field(..., description="Whether the expert is currently active")
    verification_date: Optional[datetime] = Field(None, description="Date when expert was verified")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    
    # Computed fields
    display_name: str = Field(..., description="Display name with institution")
    reputation_level: str = Field(..., description="Reputation level based on metrics")
    
    class Config:
        from_attributes = True


class ExpertListResponse(BaseModel):
    """Schema for paginated expert list responses."""
    
    experts: List[ExpertResponse] = Field(..., description="List of experts")
    total: int = Field(..., description="Total number of experts")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class ExpertSearch(BaseModel):
    """Schema for expert search parameters."""
    
    query: Optional[str] = Field(None, description="Search query for name or institution")
    institution: Optional[str] = Field(None, description="Filter by institution")
    specialization: Optional[str] = Field(None, description="Filter by specialization area")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    min_accuracy: Optional[float] = Field(None, ge=0, le=1, description="Minimum accuracy score")
    min_ratings: Optional[int] = Field(None, ge=0, description="Minimum number of ratings")
    min_experience: Optional[int] = Field(None, ge=0, description="Minimum years of experience")


class ExpertStats(BaseModel):
    """Schema for expert statistics."""
    
    total_experts: int = Field(..., description="Total number of experts")
    verified_experts: int = Field(..., description="Number of verified experts")
    active_experts: int = Field(..., description="Number of active experts")
    average_accuracy: Optional[float] = Field(None, description="Average accuracy score")
    total_ratings_by_experts: int = Field(..., description="Total ratings provided by all experts")
    top_institutions: List[dict] = Field(default_factory=list, description="Top institutions by expert count")
    specialization_distribution: dict = Field(default_factory=dict, description="Distribution of specializations")


class ExpertVerification(BaseModel):
    """Schema for expert verification request."""
    
    expert_id: str = Field(..., description="Expert ID to verify")
    verification_notes: Optional[str] = Field(None, description="Notes about verification process")


class ExpertBulkCreate(BaseModel):
    """Schema for bulk expert creation."""
    
    experts: List[ExpertCreate] = Field(..., min_items=1, max_items=50, description="List of experts to create")


class ExpertBulkResponse(BaseModel):
    """Schema for bulk operation responses."""
    
    created: int = Field(..., description="Number of experts created")
    updated: int = Field(..., description="Number of experts updated")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    experts: List[ExpertResponse] = Field(default_factory=list, description="Successfully processed experts")