"""
Rating endpoints for REST API operations.

Provides CRUD operations, aggregations, and analytics for stock ratings.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_database, common_parameters, CommonQueryParams
from app.services.rating_service import RatingService
from app.schemas.rating import (
    RatingCreate,
    RatingUpdate,
    RatingResponse,
    RatingListResponse,
    RatingSearch,
    RatingAggregation,
    RatingHistory,
    RatingBulkCreate,
    RatingBulkResponse,
    RatingType,
    RecommendationType,
)

router = APIRouter()


def get_rating_service(db: AsyncSession = Depends(get_database)) -> RatingService:
    """Dependency to get RatingService instance."""
    return RatingService(db)


@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(
    rating_data: RatingCreate,
    service: RatingService = Depends(get_rating_service),
) -> RatingResponse:
    """
    Create a new rating.
    
    - **stock_id**: ID of the stock being rated
    - **expert_id**: ID of expert (null for popular ratings)
    - **rating_type**: Type of rating (expert, popular, historical)
    - **score**: Rating score from 0.00 to 5.00
    - **recommendation**: Buy/sell recommendation
    - **confidence**: Confidence level (0.00 to 1.00)
    - **price_target**: Price target for the stock
    """
    try:
        return await service.create_rating(rating_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=RatingListResponse)
async def list_ratings(
    params: CommonQueryParams = Depends(common_parameters),
    stock_id: Optional[str] = Query(None, description="Filter by stock ID"),
    expert_id: Optional[str] = Query(None, description="Filter by expert ID"),
    rating_type: Optional[RatingType] = Query(None, description="Filter by rating type"),
    recommendation: Optional[RecommendationType] = Query(None, description="Filter by recommendation"),
    min_score: Optional[float] = Query(None, ge=0, le=5, description="Minimum score filter"),
    max_score: Optional[float] = Query(None, ge=0, le=5, description="Maximum score filter"),
    from_date: Optional[datetime] = Query(None, description="Filter ratings from this date"),
    to_date: Optional[datetime] = Query(None, description="Filter ratings to this date"),
    is_expired: Optional[bool] = Query(None, description="Filter by expiry status"),
    service: RatingService = Depends(get_rating_service),
) -> RatingListResponse:
    """
    List ratings with pagination and filtering.
    
    Supports filtering by:
    - **stock_id**: Specific stock
    - **expert_id**: Specific expert
    - **rating_type**: expert, popular, or historical
    - **recommendation**: Buy/sell recommendation type
    - **min_score/max_score**: Score range
    - **from_date/to_date**: Date range
    - **is_expired**: Expiry status
    - **search**: Text search in summaries and related entities
    """
    filters = RatingSearch(
        stock_id=stock_id,
        expert_id=expert_id,
        rating_type=rating_type,
        recommendation=recommendation,
        min_score=min_score,
        max_score=max_score,
        from_date=from_date,
        to_date=to_date,
        is_expired=is_expired,
    )
    
    return await service.list_ratings(params, filters)


@router.get("/stock/{stock_id}", response_model=List[RatingResponse])
async def get_stock_ratings(
    stock_id: str,
    service: RatingService = Depends(get_rating_service),
) -> List[RatingResponse]:
    """Get all ratings for a specific stock, ordered by date."""
    return await service.get_stock_ratings(stock_id)


@router.get("/expert/{expert_id}", response_model=List[RatingResponse])
async def get_expert_ratings(
    expert_id: str,
    service: RatingService = Depends(get_rating_service),
) -> List[RatingResponse]:
    """Get all ratings by a specific expert, ordered by date."""
    return await service.get_expert_ratings(expert_id)


@router.get("/stock/{stock_id}/aggregation", response_model=RatingAggregation)
async def get_stock_rating_aggregation(
    stock_id: str,
    service: RatingService = Depends(get_rating_service),
) -> RatingAggregation:
    """
    Get aggregated rating data for a stock.
    
    Returns:
    - Expert ratings statistics
    - Popular ratings statistics  
    - Overall recommendation
    - Overall weighted score
    - Total ratings count
    """
    aggregation = await service.get_rating_aggregation(stock_id)
    if not aggregation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock with ID {stock_id} not found"
        )
    return aggregation


@router.get("/stock/{stock_id}/history", response_model=RatingHistory)
async def get_stock_rating_history(
    stock_id: str,
    rating_type: RatingType = Query(RatingType.EXPERT, description="Type of ratings to include"),
    period: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Aggregation period"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    service: RatingService = Depends(get_rating_service),
) -> RatingHistory:
    """
    Get historical rating data for a stock.
    
    - **rating_type**: expert, popular, or historical
    - **period**: daily, weekly, or monthly aggregation
    - **days**: Number of days to include (1-365)
    """
    return await service.get_rating_history(stock_id, rating_type, period, days)


@router.get("/{rating_id}", response_model=RatingResponse)
async def get_rating_by_id(
    rating_id: str,
    service: RatingService = Depends(get_rating_service),
) -> RatingResponse:
    """Get rating by ID."""
    rating = await service.get_rating_by_id(rating_id)
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )
    return rating


@router.put("/{rating_id}", response_model=RatingResponse)
async def update_rating(
    rating_id: str,
    rating_data: RatingUpdate,
    service: RatingService = Depends(get_rating_service),
) -> RatingResponse:
    """Update rating information."""
    rating = await service.update_rating(rating_id, rating_data)
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )
    return rating


@router.delete("/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(
    rating_id: str,
    service: RatingService = Depends(get_rating_service),
) -> None:
    """Delete a rating."""
    deleted = await service.delete_rating(rating_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )


@router.post("/bulk", response_model=RatingBulkResponse)
async def bulk_create_ratings(
    bulk_data: RatingBulkCreate,
    service: RatingService = Depends(get_rating_service),
) -> RatingBulkResponse:
    """
    Bulk create or update ratings.
    
    - Creates new ratings if they don't exist
    - Updates existing ratings if they already exist (based on stock_id, expert_id, rating_date)
    - Returns summary of operations performed
    - Maximum 100 ratings per request
    """
    return await service.bulk_create_ratings(bulk_data)


# Additional analytics endpoints

@router.get("/analytics/recommendations/distribution")
async def get_recommendation_distribution(
    stock_id: Optional[str] = Query(None, description="Filter by stock ID"),
    expert_id: Optional[str] = Query(None, description="Filter by expert ID"),
    rating_type: Optional[RatingType] = Query(None, description="Filter by rating type"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    service: RatingService = Depends(get_rating_service),
) -> dict:
    """Get distribution of recommendations across the platform."""
    # This would need additional service method implementation
    return {
        "message": "Recommendation distribution analytics endpoint",
        "note": "Implementation pending based on specific analytics requirements"
    }


@router.get("/analytics/scores/trends")
async def get_score_trends(
    stock_id: Optional[str] = Query(None, description="Filter by stock ID"),
    rating_type: Optional[RatingType] = Query(None, description="Filter by rating type"),
    period: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Aggregation period"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    service: RatingService = Depends(get_rating_service),
) -> dict:
    """Get rating score trends over time."""
    # This would need additional service method implementation
    return {
        "message": "Score trends analytics endpoint",
        "note": "Implementation pending based on specific analytics requirements"
    }


@router.get("/analytics/experts/performance")
async def get_expert_performance(
    expert_id: Optional[str] = Query(None, description="Specific expert ID"),
    min_ratings: int = Query(10, ge=1, description="Minimum number of ratings"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    service: RatingService = Depends(get_rating_service),
) -> dict:
    """Get expert performance analytics."""
    # This would need additional service method implementation
    return {
        "message": "Expert performance analytics endpoint",
        "note": "Implementation pending based on specific analytics requirements"
    }