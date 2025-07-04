"""
Stock service layer for business logic.

Handles stock-related business operations including CRUD operations,
search functionality, and data validation.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.stock import Stock
from app.db.repositories.stock import StockRepository
from app.schemas.stock import (
    StockCreate,
    StockUpdate,
    StockPriceUpdate,
    StockSearch,
    StockResponse,
    StockListResponse,
    StockBulkCreate,
    StockBulkResponse,
)
from app.api.v1.deps import CommonQueryParams

logger = logging.getLogger(__name__)


class StockService:
    """Service class for stock-related business logic."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.repository = StockRepository(db)
    
    async def create_stock(self, stock_data: StockCreate) -> StockResponse:
        """
        Create a new stock.
        
        Args:
            stock_data: Stock creation data
            
        Returns:
            Created stock response
            
        Raises:
            ValueError: If stock with symbol already exists
        """
        # Check if stock already exists
        existing = await self.repository.get_by_symbol(stock_data.symbol.upper())
        if existing:
            raise ValueError(f"Stock with symbol {stock_data.symbol} already exists")
        
        # Create new stock
        stock_dict = stock_data.dict()
        stock_dict['symbol'] = stock_dict['symbol'].upper()
        
        stock = await self.repository.create(**stock_dict)
        await self.db.commit()
        
        logger.info(f"Created stock: {stock.symbol}")
        return self._to_response(stock)
    
    async def get_stock_by_id(self, stock_id: str) -> Optional[StockResponse]:
        """
        Get stock by ID.
        
        Args:
            stock_id: Stock ID
            
        Returns:
            Stock response or None if not found
        """
        stock = await self.repository.get_by_id(stock_id)
        return self._to_response(stock) if stock else None
    
    async def get_stock_by_symbol(self, symbol: str) -> Optional[StockResponse]:
        """
        Get stock by symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Stock response or None if not found
        """
        stock = await self.repository.get_by_symbol(symbol.upper())
        return self._to_response(stock) if stock else None
    
    async def update_stock(self, stock_id: str, stock_data: StockUpdate) -> Optional[StockResponse]:
        """
        Update existing stock.
        
        Args:
            stock_id: Stock ID
            stock_data: Update data
            
        Returns:
            Updated stock response or None if not found
        """
        stock = await self.repository.get_by_id(stock_id)
        if not stock:
            return None
        
        # Update fields
        update_data = stock_data.dict(exclude_unset=True)
        if update_data:
            stock = await self.repository.update(stock.id, **update_data)
            await self.db.commit()
            logger.info(f"Updated stock: {stock.symbol}")
        
        return self._to_response(stock)
    
    async def update_stock_price(self, symbol: str, price_data: StockPriceUpdate) -> Optional[StockResponse]:
        """
        Update stock price data.
        
        Args:
            symbol: Stock symbol
            price_data: Price update data
            
        Returns:
            Updated stock response or None if not found
        """
        stock = await self.repository.get_by_symbol(symbol.upper())
        if not stock:
            return None
        
        # Update price using model method
        stock.update_price_data(
            current_price=price_data.current_price,
            previous_close=price_data.previous_close,
            day_high=price_data.day_high,
            day_low=price_data.day_low,
            volume=price_data.volume,
        )
        
        await self.db.commit()
        logger.info(f"Updated price for stock: {stock.symbol}")
        
        return self._to_response(stock)
    
    async def delete_stock(self, stock_id: str) -> bool:
        """
        Soft delete a stock (set is_active=False).
        
        Args:
            stock_id: Stock ID
            
        Returns:
            True if deleted, False if not found
        """
        stock = await self.repository.get_by_id(stock_id)
        if not stock:
            return False
        
        await self.repository.update(stock.id, is_active=False)
        await self.db.commit()
        
        logger.info(f"Soft deleted stock: {stock.symbol}")
        return True
    
    async def list_stocks(
        self, 
        params: CommonQueryParams,
        filters: Optional[StockSearch] = None
    ) -> StockListResponse:
        """
        List stocks with pagination and filtering.
        
        Args:
            params: Common query parameters
            filters: Optional search filters
            
        Returns:
            Paginated stock list response
        """
        # Build query
        query = select(Stock)
        
        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
        
        # Apply search
        if params.search:
            search_filter = or_(
                Stock.symbol.ilike(f"%{params.search}%"),
                Stock.name.ilike(f"%{params.search}%"),
                Stock.description.ilike(f"%{params.search}%")
            )
            query = query.where(search_filter)
        
        # Apply sorting
        if params.sort_by:
            sort_column = getattr(Stock, params.sort_by, None)
            if sort_column:
                if params.sort_order == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))
        else:
            # Default sort by symbol
            query = query.order_by(Stock.symbol)
        
        # Get total count
        count_query = select(func.count(Stock.id))
        if filters:
            count_query = self._apply_filters(count_query, filters)
        if params.search:
            count_query = count_query.where(search_filter)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(params.skip).limit(params.limit)
        
        # Execute query
        result = await self.db.execute(query)
        stocks = result.scalars().all()
        
        # Calculate pagination info
        pages = (total + params.limit - 1) // params.limit
        has_next = params.page < pages
        has_prev = params.page > 1
        
        return StockListResponse(
            stocks=[self._to_response(stock) for stock in stocks],
            total=total,
            page=params.page,
            limit=params.limit,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev,
        )
    
    async def search_stocks(
        self,
        search_params: StockSearch,
        params: CommonQueryParams
    ) -> StockListResponse:
        """
        Advanced stock search.
        
        Args:
            search_params: Search parameters
            params: Common query parameters
            
        Returns:
            Search results
        """
        return await self.list_stocks(params, search_params)
    
    async def bulk_create_stocks(self, bulk_data: StockBulkCreate) -> StockBulkResponse:
        """
        Bulk create stocks.
        
        Args:
            bulk_data: Bulk creation data
            
        Returns:
            Bulk operation response
        """
        created = 0
        updated = 0
        errors = []
        stocks = []
        
        for stock_data in bulk_data.stocks:
            try:
                # Check if stock exists
                existing = await self.repository.get_by_symbol(stock_data.symbol.upper())
                
                if existing:
                    # Update existing stock
                    update_data = stock_data.dict(exclude={'symbol'})
                    stock = await self.repository.update(existing.id, **update_data)
                    updated += 1
                else:
                    # Create new stock
                    stock_dict = stock_data.dict()
                    stock_dict['symbol'] = stock_dict['symbol'].upper()
                    stock = await self.repository.create(**stock_dict)
                    created += 1
                
                stocks.append(self._to_response(stock))
                
            except Exception as e:
                error_msg = f"Error processing {stock_data.symbol}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        if created > 0 or updated > 0:
            await self.db.commit()
        
        logger.info(f"Bulk operation completed: {created} created, {updated} updated, {len(errors)} errors")
        
        return StockBulkResponse(
            created=created,
            updated=updated,
            errors=errors,
            stocks=stocks,
        )
    
    async def get_active_stocks_count(self) -> int:
        """Get count of active stocks."""
        query = select(func.count(Stock.id)).where(Stock.is_active == True)
        result = await self.db.execute(query)
        return result.scalar()
    
    async def get_stocks_by_exchange(self, exchange: str) -> List[StockResponse]:
        """Get all stocks for a specific exchange."""
        query = select(Stock).where(
            and_(Stock.exchange == exchange, Stock.is_active == True)
        ).order_by(Stock.symbol)
        
        result = await self.db.execute(query)
        stocks = result.scalars().all()
        
        return [self._to_response(stock) for stock in stocks]
    
    async def get_stocks_by_sector(self, sector: str) -> List[StockResponse]:
        """Get all stocks for a specific sector."""
        query = select(Stock).where(
            and_(Stock.sector == sector, Stock.is_active == True)
        ).order_by(Stock.symbol)
        
        result = await self.db.execute(query)
        stocks = result.scalars().all()
        
        return [self._to_response(stock) for stock in stocks]
    
    def _apply_filters(self, query, filters: StockSearch):
        """Apply search filters to query."""
        conditions = []
        
        if filters.exchange:
            conditions.append(Stock.exchange == filters.exchange)
        
        if filters.sector:
            conditions.append(Stock.sector == filters.sector)
        
        if filters.industry:
            conditions.append(Stock.industry == filters.industry)
        
        if filters.min_price is not None:
            conditions.append(Stock.current_price >= filters.min_price)
        
        if filters.max_price is not None:
            conditions.append(Stock.current_price <= filters.max_price)
        
        if filters.min_market_cap is not None:
            conditions.append(Stock.market_cap >= filters.min_market_cap)
        
        if filters.max_market_cap is not None:
            conditions.append(Stock.market_cap <= filters.max_market_cap)
        
        if filters.is_active is not None:
            conditions.append(Stock.is_active == filters.is_active)
        
        if filters.query:
            search_condition = or_(
                Stock.symbol.ilike(f"%{filters.query}%"),
                Stock.name.ilike(f"%{filters.query}%"),
                Stock.description.ilike(f"%{filters.query}%")
            )
            conditions.append(search_condition)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def _to_response(self, stock: Stock) -> StockResponse:
        """Convert Stock model to response schema."""
        return StockResponse(
            id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            description=stock.description,
            exchange=stock.exchange,
            sector=stock.sector,
            industry=stock.industry,
            market_cap=stock.market_cap,
            current_price=stock.current_price,
            previous_close=stock.previous_close,
            day_high=stock.day_high,
            day_low=stock.day_low,
            volume=stock.volume,
            is_active=stock.is_active,
            last_updated=stock.last_updated,
            created_at=stock.created_at,
            updated_at=stock.updated_at,
            price_change=stock.price_change,
            price_change_percent=stock.price_change_percent,
            is_up=stock.is_up,
        )