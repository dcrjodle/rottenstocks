"""
Stock synchronization tasks for Alpha Vantage integration.

Provides automated stock data synchronization with rate limiting and
comprehensive error handling.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_managed_session
from app.db.models.stock import Stock
from app.services.stock_service import StockService
from app.external_apis.providers import get_alpha_vantage_client
from app.external_apis.alpha_vantage.service import AlphaVantageService
from app.external_apis.base.exceptions import RateLimitExceededError, ExternalAPIError as APIError

logger = get_logger(__name__)
settings = get_settings()


class StockSyncTaskManager:
    """Manages stock synchronization tasks with rate limiting."""
    
    def __init__(self):
        self.stock_service: Optional[StockService] = None
        self.alpha_vantage_service: Optional[AlphaVantageService] = None
        self._daily_request_count = 0
        self._last_reset_date = datetime.now().date()
    
    async def initialize_services(self, session) -> None:
        """Initialize required services."""
        if not self.stock_service:
            self.stock_service = StockService(session)
        
        if not self.alpha_vantage_service:
            client = get_alpha_vantage_client()
            self.alpha_vantage_service = AlphaVantageService(client=client, db=session)
    
    async def get_active_stocks(self) -> List[Stock]:
        """Get list of active stocks to sync."""
        async with get_managed_session() as session:
            # Get stocks that have been updated in the last 30 days or are flagged for tracking
            query = select(Stock).where(
                Stock.is_active == True
            ).order_by(
                # Prioritize stocks that haven't been updated recently
                Stock.last_updated.asc().nulls_first()
            ).limit(settings.get_batch_size())
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def sync_stock_data(self) -> Dict[str, Any]:
        """
        Synchronize stock data from Alpha Vantage API.
        
        Returns:
            Dict with sync results and statistics
        """
        # Check daily request limit first
        if self._check_daily_limit():
            return {
                "status": "skipped",
                "reason": "Daily API request limit reached",
                "requests_used": self._daily_request_count,
                "limit": settings.get_alpha_vantage_daily_limit()
            }
        
        try:
            # Get stocks to sync
            stocks_to_sync = await self.get_active_stocks()
            
            if not stocks_to_sync:
                logger.info("No stocks found for synchronization")
                return {
                    "status": "completed",
                    "stocks_processed": 0,
                    "requests_used": self._daily_request_count,
                    "message": "No stocks to sync"
                }
            
            # Initialize services with a session
            async with get_managed_session() as session:
                await self.initialize_services(session)
                
                # Process stocks
                results = {
                    "status": "completed",
                    "stocks_processed": 0,
                    "successful_updates": 0,
                    "failed_updates": 0,
                    "requests_used": self._daily_request_count,
                    "errors": [],
                    "updated_stocks": []
                }
                
                for stock in stocks_to_sync:
                    if self._check_daily_limit():
                        results["status"] = "partial"
                        results["errors"].append("Daily API request limit reached")
                        break
                    
                    try:
                        # Sync stock data
                        await self._sync_single_stock(stock)
                        results["successful_updates"] += 1
                        results["updated_stocks"].append(stock.symbol)
                        self._daily_request_count += 1
                        
                        # Small delay to avoid overwhelming the API
                        await asyncio.sleep(1)
                        
                    except RateLimitExceededError:
                        results["status"] = "partial"
                        results["errors"].append(f"Rate limit exceeded for {stock.symbol}")
                        break
                        
                    except APIError as e:
                        results["failed_updates"] += 1
                        results["errors"].append(f"API error for {stock.symbol}: {str(e)}")
                        logger.warning(f"API error syncing {stock.symbol}: {e}")
                        
                    except Exception as e:
                        results["failed_updates"] += 1
                        results["errors"].append(f"Unexpected error for {stock.symbol}: {str(e)}")
                        logger.error(f"Unexpected error syncing {stock.symbol}: {e}")
                    
                    finally:
                        results["stocks_processed"] += 1
                
                results["requests_used"] = self._daily_request_count
                
                logger.info(
                    f"Stock sync completed: {results['successful_updates']} successful, "
                    f"{results['failed_updates']} failed, "
                    f"{results['requests_used']} requests used"
                )
                
                return results
            
        except Exception as e:
            logger.error(f"Stock sync task failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "stocks_processed": 0,
                "requests_used": self._daily_request_count
            }
    
    async def _sync_single_stock(self, stock: Stock) -> None:
        """Sync a single stock's data."""
        try:
            # Get real-time quote
            quote_data = await self.alpha_vantage_service.get_stock_quote(stock.symbol)
            
            # Update stock with new data
            async with get_managed_session() as session:
                # Refresh the stock object in this session
                await session.refresh(stock)
                
                # Update stock data
                stock.current_price = quote_data.price
                stock.previous_close = quote_data.previous_close
                stock.change = quote_data.change
                stock.change_percent = quote_data.change_percent
                stock.volume = quote_data.volume
                stock.last_updated = datetime.now()
                
                # Update market data if available
                if hasattr(quote_data, 'high'):
                    stock.day_high = quote_data.high
                if hasattr(quote_data, 'low'):
                    stock.day_low = quote_data.low
                if hasattr(quote_data, 'open'):
                    stock.day_open = quote_data.open
                
                await session.commit()
                
                logger.debug(f"Updated stock data for {stock.symbol}")
                
        except Exception as e:
            logger.error(f"Failed to sync stock {stock.symbol}: {e}")
            raise
    
    def _check_daily_limit(self) -> bool:
        """Check if daily API request limit has been reached."""
        current_date = datetime.now().date()
        
        # Reset counter if it's a new day
        if current_date != self._last_reset_date:
            self._daily_request_count = 0
            self._last_reset_date = current_date
        
        return self._daily_request_count >= settings.get_alpha_vantage_daily_limit()
    
    async def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        async with get_managed_session() as session:
            # Get total stocks
            total_stocks = await session.execute(select(func.count(Stock.id)))
            total_stocks = total_stocks.scalar()
            
            # Get active stocks
            active_stocks = await session.execute(
                select(func.count(Stock.id)).where(Stock.is_active == True)
            )
            active_stocks = active_stocks.scalar()
            
            # Get recently updated stocks (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            recent_updates = await session.execute(
                select(func.count(Stock.id)).where(Stock.last_updated >= yesterday)
            )
            recent_updates = recent_updates.scalar()
            
            # Get stocks that need updating (older than 1 hour)
            hour_ago = datetime.now() - timedelta(hours=1)
            needs_update = await session.execute(
                select(func.count(Stock.id)).where(
                    Stock.is_active == True,
                    Stock.last_updated < hour_ago
                )
            )
            needs_update = needs_update.scalar()
            
            daily_limit = settings.get_alpha_vantage_daily_limit()
            return {
                "total_stocks": total_stocks,
                "active_stocks": active_stocks,
                "recently_updated": recent_updates,
                "needs_update": needs_update,
                "requests_used_today": self._daily_request_count,
                "daily_limit": daily_limit,
                "requests_remaining": max(0, daily_limit - self._daily_request_count),
                "last_reset_date": self._last_reset_date.isoformat()
            }


# Global task manager instance
_task_manager: Optional[StockSyncTaskManager] = None


def get_task_manager() -> StockSyncTaskManager:
    """Get the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = StockSyncTaskManager()
    return _task_manager


async def scheduled_stock_sync() -> None:
    """Scheduled task function for stock synchronization."""
    logger.info("Starting scheduled stock synchronization")
    
    task_manager = get_task_manager()
    result = await task_manager.sync_stock_data()
    
    if result["status"] == "failed":
        logger.error(f"Stock sync failed: {result.get('error', 'Unknown error')}")
    else:
        logger.info(f"Stock sync {result['status']}: {result['successful_updates']} successful, {result['failed_updates']} failed")


async def scheduled_stock_discovery() -> None:
    """Scheduled task for discovering new stocks to track."""
    logger.info("Starting scheduled stock discovery")
    
    try:
        # This could be expanded to automatically discover popular stocks
        # For now, just log that the task ran
        logger.info("Stock discovery task completed (placeholder)")
        
    except Exception as e:
        logger.error(f"Stock discovery task failed: {e}")


async def scheduled_cleanup() -> None:
    """Scheduled task for cleaning up old data."""
    logger.info("Starting scheduled cleanup")
    
    try:
        async with get_managed_session() as session:
            # Clean up old cache entries or inactive stocks
            # This is a placeholder for future cleanup logic
            logger.info("Cleanup task completed (placeholder)")
            
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")