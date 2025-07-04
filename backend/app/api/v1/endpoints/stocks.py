"""
Stock endpoints for REST API operations.

Provides CRUD operations, search, and bulk operations for stocks.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_database, common_parameters, CommonQueryParams
from app.services.stock_service import StockService
from app.external_apis.providers import get_alpha_vantage_service
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


def get_stock_service(
    db: AsyncSession = Depends(get_database),
    alpha_vantage_service = Depends(get_alpha_vantage_service)
) -> StockService:
    """Dependency to get StockService instance with Alpha Vantage integration."""
    return StockService(db, alpha_vantage_service)


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


# Alpha Vantage Integration Endpoints

@router.post("/search-and-create", response_model=List[StockResponse])
async def search_and_create_stocks(
    query: str = Query(..., description="Search query for stocks"),
    service: StockService = Depends(get_stock_service),
) -> List[StockResponse]:
    """
    Search for stocks using Alpha Vantage and create them in the database.
    
    - **query**: Search terms (company name or symbol)
    - Returns up to 5 matching stocks
    - Creates stocks that don't already exist
    """
    return await service.search_and_create_stock(query)


@router.post("/symbol/{symbol}/sync-from-alpha-vantage", response_model=StockResponse)
async def sync_stock_from_alpha_vantage(
    symbol: str,
    service: StockService = Depends(get_stock_service),
) -> StockResponse:
    """
    Sync stock data from Alpha Vantage API.
    
    Updates both price data and company information from Alpha Vantage.
    """
    # First try to sync price
    price_synced = await service.sync_stock_price_from_alpha_vantage(symbol)
    
    # Then try to enrich data
    data_enriched = await service.enrich_stock_from_alpha_vantage(symbol)
    
    if not price_synced and not data_enriched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync stock data for {symbol} from Alpha Vantage"
        )
    
    # Get updated stock
    stock = await service.get_stock_by_symbol(symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock with symbol {symbol} not found after sync"
        )
    
    return stock


@router.post("/symbol/{symbol}/create-from-alpha-vantage", response_model=StockResponse)
async def create_stock_from_alpha_vantage(
    symbol: str,
    service: StockService = Depends(get_stock_service),
) -> StockResponse:
    """
    Create a new stock using Alpha Vantage data.
    
    Fetches company overview and current quote from Alpha Vantage
    to create a new stock entry.
    """
    stock = await service.create_stock_from_alpha_vantage(symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create stock for {symbol} using Alpha Vantage data"
        )
    
    return stock


@router.get("/symbol/{symbol}/quote", response_model=dict)
async def get_real_time_quote(
    symbol: str,
    service: StockService = Depends(get_stock_service),
) -> dict:
    """
    Get real-time quote from Alpha Vantage.
    
    Returns current market data without updating the database.
    """
    quote = await service.get_alpha_vantage_quote(symbol)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote not available for {symbol}"
        )
    
    return quote


@router.post("/bulk-sync-prices", response_model=dict)
async def bulk_sync_prices_from_alpha_vantage(
    symbols: List[str] = Query(..., description="List of stock symbols to sync"),
    service: StockService = Depends(get_stock_service),
) -> dict:
    """
    Bulk sync stock prices from Alpha Vantage.
    
    - **symbols**: List of stock symbols to sync
    - Maximum 10 symbols per request to respect rate limits
    """
    if len(symbols) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 symbols allowed per bulk sync request"
        )
    
    results = await service.bulk_sync_prices_from_alpha_vantage(symbols)
    return results