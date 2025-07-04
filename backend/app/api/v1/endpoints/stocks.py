"""
Stock endpoints for REST API operations.

Provides CRUD operations, search, and bulk operations for stocks.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_database, common_parameters, CommonQueryParams
from app.services.stock_service import StockService
from app.schemas.stock import (
    StockCreate,
    StockUpdate,
    StockPriceUpdate,
    StockResponse,
    StockListResponse,
    StockSearch,
    StockBulkCreate,
    StockBulkResponse,
)

router = APIRouter()


def get_stock_service(db: AsyncSession = Depends(get_database)) -> StockService:
    """Dependency to get StockService instance."""
    return StockService(db)


@router.post("/", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
async def create_stock(
    stock_data: StockCreate,
    service: StockService = Depends(get_stock_service),
) -> StockResponse:
    """
    Create a new stock.
    
    - **symbol**: Stock ticker symbol (will be converted to uppercase)
    - **name**: Company name
    - **exchange**: Stock exchange (NYSE, NASDAQ, etc.)
    - **sector**: Market sector (optional)
    - **industry**: Industry classification (optional)
    - **market_cap**: Market capitalization in USD (optional)
    - **current_price**: Current stock price (optional)
    """
    try:
        return await service.create_stock(stock_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=StockListResponse)
async def list_stocks(
    params: CommonQueryParams = Depends(common_parameters),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    min_market_cap: Optional[float] = Query(None, ge=0, description="Minimum market cap filter"),
    max_market_cap: Optional[float] = Query(None, ge=0, description="Maximum market cap filter"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    service: StockService = Depends(get_stock_service),
) -> StockListResponse:
    """
    List stocks with pagination and filtering.
    
    Supports filtering by:
    - **exchange**: Stock exchange
    - **sector**: Market sector
    - **industry**: Industry classification
    - **min_price/max_price**: Price range
    - **min_market_cap/max_market_cap**: Market cap range
    - **is_active**: Active status
    - **search**: Text search in symbol, name, or description
    - **sort_by**: Field to sort by
    - **sort_order**: asc or desc
    """
    filters = StockSearch(
        exchange=exchange,
        sector=sector,
        industry=industry,
        min_price=min_price,
        max_price=max_price,
        min_market_cap=min_market_cap,
        max_market_cap=max_market_cap,
        is_active=is_active,
    )
    
    return await service.list_stocks(params, filters)


@router.get("/search", response_model=StockListResponse)
async def search_stocks(
    q: str = Query(..., description="Search query"),
    params: CommonQueryParams = Depends(common_parameters),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    service: StockService = Depends(get_stock_service),
) -> StockListResponse:
    """
    Search stocks with advanced filtering.
    
    Search in stock symbol, name, and description with optional filters.
    """
    search_params = StockSearch(
        query=q,
        exchange=exchange,
        sector=sector,
        industry=industry,
        min_price=min_price,
        max_price=max_price,
        is_active=is_active,
    )
    
    return await service.search_stocks(search_params, params)


@router.get("/exchange/{exchange}", response_model=List[StockResponse])
async def get_stocks_by_exchange(
    exchange: str,
    service: StockService = Depends(get_stock_service),
) -> List[StockResponse]:
    """Get all active stocks for a specific exchange."""
    return await service.get_stocks_by_exchange(exchange)


@router.get("/sector/{sector}", response_model=List[StockResponse])
async def get_stocks_by_sector(
    sector: str,
    service: StockService = Depends(get_stock_service),
) -> List[StockResponse]:
    """Get all active stocks for a specific sector."""
    return await service.get_stocks_by_sector(sector)


@router.get("/stats/count")
async def get_active_stocks_count(
    service: StockService = Depends(get_stock_service),
) -> dict:
    """Get count of active stocks."""
    count = await service.get_active_stocks_count()
    return {"active_stocks": count}


@router.get("/{stock_id}", response_model=StockResponse)
async def get_stock_by_id(
    stock_id: str,
    service: StockService = Depends(get_stock_service),
) -> StockResponse:
    """Get stock by ID."""
    stock = await service.get_stock_by_id(stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock not found"
        )
    return stock


@router.get("/symbol/{symbol}", response_model=StockResponse)
async def get_stock_by_symbol(
    symbol: str,
    service: StockService = Depends(get_stock_service),
) -> StockResponse:
    """Get stock by symbol."""
    stock = await service.get_stock_by_symbol(symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock with symbol {symbol} not found"
        )
    return stock


@router.put("/{stock_id}", response_model=StockResponse)
async def update_stock(
    stock_id: str,
    stock_data: StockUpdate,
    service: StockService = Depends(get_stock_service),
) -> StockResponse:
    """Update stock information."""
    stock = await service.update_stock(stock_id, stock_data)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock not found"
        )
    return stock


@router.patch("/symbol/{symbol}/price", response_model=StockResponse)
async def update_stock_price(
    symbol: str,
    price_data: StockPriceUpdate,
    service: StockService = Depends(get_stock_service),
) -> StockResponse:
    """
    Update stock price data.
    
    This endpoint is optimized for frequent price updates from data feeds.
    """
    stock = await service.update_stock_price(symbol, price_data)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock with symbol {symbol} not found"
        )
    return stock


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(
    stock_id: str,
    service: StockService = Depends(get_stock_service),
) -> None:
    """
    Soft delete a stock (sets is_active=False).
    
    The stock will no longer appear in active listings but data is preserved.
    """
    deleted = await service.delete_stock(stock_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock not found"
        )


@router.post("/bulk", response_model=StockBulkResponse)
async def bulk_create_stocks(
    bulk_data: StockBulkCreate,
    service: StockService = Depends(get_stock_service),
) -> StockBulkResponse:
    """
    Bulk create or update stocks.
    
    - Creates new stocks if they don't exist
    - Updates existing stocks if they already exist (based on symbol)
    - Returns summary of operations performed
    - Maximum 100 stocks per request
    """
    return await service.bulk_create_stocks(bulk_data)