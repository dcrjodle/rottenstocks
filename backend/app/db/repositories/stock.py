"""
Stock repository for database operations.

This module provides stock-specific database operations including
CRUD operations, market data updates, and stock analysis queries.
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.stock import Stock
from ..exceptions import NotFoundError, ValidationError, DatabaseErrorHandler
from .base import BaseRepository

logger = logging.getLogger(__name__)


class StockRepository(BaseRepository[Stock]):
    """Repository for stock-related database operations."""
    
    def get_model_class(self) -> type[Stock]:
        """Get the Stock model class."""
        return Stock
    
    def get_unique_fields(self) -> List[str]:
        """Get unique fields for Stock model."""
        return ["symbol"]
    
    # Stock-specific queries
    
    async def get_by_symbol(self, symbol: str) -> Optional[Stock]:
        """
        Get stock by symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
        
        Returns:
            Stock instance or None if not found
        """
        return await self.get_by_field("symbol", symbol.upper())
    
    async def get_with_ratings(self, symbol: str) -> Optional[Stock]:
        """
        Get stock with all its ratings loaded.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Stock instance with ratings or None if not found
        """
        return await self.get_by_field(
            "symbol", 
            symbol.upper(),
            options=[selectinload(Stock.ratings)]
        )
    
    async def get_with_social_posts(self, symbol: str) -> Optional[Stock]:
        """
        Get stock with all its social posts loaded.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Stock instance with social posts or None if not found
        """
        return await self.get_by_field(
            "symbol",
            symbol.upper(),
            options=[selectinload(Stock.social_posts)]
        )
    
    async def get_by_sector(
        self, 
        sector: str, 
        limit: Optional[int] = None
    ) -> List[Stock]:
        """
        Get stocks by sector.
        
        Args:
            sector: Sector name
            limit: Maximum number of stocks to return
        
        Returns:
            List of stocks in the sector
        """
        return await self.filter(
            filters={"sector": sector},
            limit=limit,
            order_by="symbol"
        )
    
    async def get_by_exchange(
        self, 
        exchange: str, 
        limit: Optional[int] = None
    ) -> List[Stock]:
        """
        Get stocks by exchange.
        
        Args:
            exchange: Exchange name (e.g., 'NASDAQ', 'NYSE')
            limit: Maximum number of stocks to return
        
        Returns:
            List of stocks on the exchange
        """
        return await self.filter(
            filters={"exchange": exchange},
            limit=limit,
            order_by="symbol"
        )
    
    async def search_by_name_or_symbol(
        self, 
        query: str, 
        limit: int = 20
    ) -> List[Stock]:
        """
        Search stocks by name or symbol.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching stocks
        """
        async with DatabaseErrorHandler("Searching stocks"):
            query_upper = query.upper()
            
            stmt = select(Stock).where(
                or_(
                    Stock.symbol.ilike(f"%{query_upper}%"),
                    Stock.name.ilike(f"%{query}%")
                )
            ).order_by(
                # Prioritize exact symbol matches
                Stock.symbol == query_upper,
                Stock.symbol
            ).limit(limit)
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_by_price_range(
        self, 
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        limit: Optional[int] = None
    ) -> List[Stock]:
        """
        Get stocks within a price range.
        
        Args:
            min_price: Minimum price (inclusive)
            max_price: Maximum price (inclusive)
            limit: Maximum number of stocks to return
        
        Returns:
            List of stocks in the price range
        """
        filters = {}
        if min_price is not None:
            filters["current_price"] = {"gte": min_price}
        if max_price is not None:
            if "current_price" not in filters:
                filters["current_price"] = {}
            filters["current_price"]["lte"] = max_price
        
        return await self.filter(
            filters=filters,
            limit=limit,
            order_by="current_price"
        )
    
    async def get_top_performers(
        self, 
        limit: int = 10,
        by_volume: bool = False
    ) -> List[Stock]:
        """
        Get top performing stocks.
        
        Args:
            limit: Number of stocks to return
            by_volume: If True, sort by volume instead of price change
        
        Returns:
            List of top performing stocks
        """
        if by_volume:
            order_field = "-volume"
        else:
            order_field = "-current_price"  # This could be improved with actual price change calculation
        
        return await self.filter(
            limit=limit,
            order_by=order_field
        )
    
    async def get_stocks_with_recent_activity(
        self, 
        days: int = 7,
        min_posts: int = 5
    ) -> List[Stock]:
        """
        Get stocks with recent social media activity.
        
        Args:
            days: Number of days to look back
            min_posts: Minimum number of posts required
        
        Returns:
            List of stocks with recent activity
        """
        async with DatabaseErrorHandler("Getting stocks with recent activity"):
            from ..models.social_post import SocialPost
            
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timezone.timedelta(days=days)
            
            # Query stocks with recent social posts
            stmt = (
                select(Stock)
                .join(SocialPost)
                .where(SocialPost.posted_at >= threshold_date)
                .group_by(Stock.id)
                .having(func.count(SocialPost.id) >= min_posts)
                .order_by(func.count(SocialPost.id).desc())
            )
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
    
    # Market data operations
    
    async def update_market_data(
        self,
        symbol: str,
        current_price: Optional[Decimal] = None,
        volume: Optional[int] = None,
        day_high: Optional[Decimal] = None,
        day_low: Optional[Decimal] = None,
        **kwargs
    ) -> Optional[Stock]:
        """
        Update market data for a stock.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            volume: Trading volume
            day_high: Day's high price
            day_low: Day's low price
            **kwargs: Additional fields to update
        
        Returns:
            Updated stock instance or None if not found
        """
        async with DatabaseErrorHandler(f"Updating market data for {symbol}"):
            stock = await self.get_by_symbol(symbol)
            if not stock:
                return None
            
            # Update previous close before updating current price
            if current_price is not None and stock.current_price:
                stock.previous_close = stock.current_price
            
            # Update market data
            stock.update_market_data(
                current_price=current_price,
                volume=volume,
                day_high=day_high,
                day_low=day_low,
                **kwargs
            )
            
            await self.session.flush()
            await self.session.refresh(stock)
            
            logger.info(f"Updated market data for {symbol}")
            return stock
    
    async def upsert_stock(
        self,
        symbol: str,
        name: str,
        exchange: str,
        **kwargs
    ) -> Stock:
        """
        Insert or update stock information.
        
        Args:
            symbol: Stock symbol
            name: Company name
            exchange: Stock exchange
            **kwargs: Additional stock data
        
        Returns:
            Stock instance
        """
        data = {
            "symbol": symbol.upper(),
            "name": name,
            "exchange": exchange,
            **kwargs
        }
        
        return await self.upsert(
            constraint_fields=["symbol"],
            **data
        )
    
    # Analytics and aggregations
    
    async def get_sector_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary statistics by sector.
        
        Returns:
            List of sector summaries with count and average price
        """
        async with DatabaseErrorHandler("Getting sector summary"):
            stmt = (
                select(
                    Stock.sector,
                    func.count(Stock.id).label("stock_count"),
                    func.avg(Stock.current_price).label("avg_price"),
                    func.sum(Stock.market_cap).label("total_market_cap")
                )
                .group_by(Stock.sector)
                .order_by(func.count(Stock.id).desc())
            )
            
            result = await self.session.execute(stmt)
            
            return [
                {
                    "sector": row.sector,
                    "stock_count": row.stock_count,
                    "avg_price": float(row.avg_price) if row.avg_price else 0,
                    "total_market_cap": float(row.total_market_cap) if row.total_market_cap else 0
                }
                for row in result.fetchall()
            ]
    
    async def get_exchange_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary statistics by exchange.
        
        Returns:
            List of exchange summaries
        """
        async with DatabaseErrorHandler("Getting exchange summary"):
            stmt = (
                select(
                    Stock.exchange,
                    func.count(Stock.id).label("stock_count"),
                    func.avg(Stock.current_price).label("avg_price")
                )
                .group_by(Stock.exchange)
                .order_by(func.count(Stock.id).desc())
            )
            
            result = await self.session.execute(stmt)
            
            return [
                {
                    "exchange": row.exchange,
                    "stock_count": row.stock_count,
                    "avg_price": float(row.avg_price) if row.avg_price else 0
                }
                for row in result.fetchall()
            ]
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """
        Get overall market overview statistics.
        
        Returns:
            Dictionary with market statistics
        """
        async with DatabaseErrorHandler("Getting market overview"):
            # Total stocks
            total_stocks = await self.count()
            
            # Price statistics
            price_stats = await self.session.execute(
                select(
                    func.avg(Stock.current_price).label("avg_price"),
                    func.min(Stock.current_price).label("min_price"),
                    func.max(Stock.current_price).label("max_price"),
                    func.sum(Stock.market_cap).label("total_market_cap")
                )
            )
            stats = price_stats.fetchone()
            
            # Volume statistics
            volume_stats = await self.session.execute(
                select(
                    func.sum(Stock.volume).label("total_volume"),
                    func.avg(Stock.volume).label("avg_volume")
                )
            )
            vol_stats = volume_stats.fetchone()
            
            return {
                "total_stocks": total_stocks,
                "avg_price": float(stats.avg_price) if stats.avg_price else 0,
                "min_price": float(stats.min_price) if stats.min_price else 0,
                "max_price": float(stats.max_price) if stats.max_price else 0,
                "total_market_cap": float(stats.total_market_cap) if stats.total_market_cap else 0,
                "total_volume": int(vol_stats.total_volume) if vol_stats.total_volume else 0,
                "avg_volume": int(vol_stats.avg_volume) if vol_stats.avg_volume else 0,
            }
    
    # Validation
    
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate stock creation data."""
        # Ensure symbol is uppercase
        if "symbol" in data:
            data["symbol"] = data["symbol"].upper()
        
        # Validate required fields
        required_fields = ["symbol", "name", "exchange"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate price fields
        price_fields = ["current_price", "previous_close", "day_high", "day_low"]
        for field in price_fields:
            if field in data and data[field] is not None:
                if not isinstance(data[field], (int, float, Decimal)) or data[field] < 0:
                    raise ValidationError(f"Invalid {field}: must be a positive number")
        
        # Validate volume
        if "volume" in data and data["volume"] is not None:
            if not isinstance(data["volume"], int) or data["volume"] < 0:
                raise ValidationError("Invalid volume: must be a positive integer")
        
        return data
    
    def validate_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate stock update data."""
        # Don't allow symbol updates
        if "symbol" in data:
            raise ValidationError("Stock symbol cannot be updated")
        
        # Validate price fields
        price_fields = ["current_price", "previous_close", "day_high", "day_low"]
        for field in price_fields:
            if field in data and data[field] is not None:
                if not isinstance(data[field], (int, float, Decimal)) or data[field] < 0:
                    raise ValidationError(f"Invalid {field}: must be a positive number")
        
        return data