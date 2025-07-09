"""
CONTEXT: Stock Sync Service
PURPOSE: Synchronizes stock data from AlphaVantage API to local database
DEPENDENCIES: alphavantage_service, database, asyncio
TESTING: See stock_sync_service_test.py for coverage
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from alphavantage_service import AlphaVantageService
from database import (
    get_all_stocks, 
    get_stock_by_symbol, 
    create_or_update_stock_from_alpha_vantage
)

logger = logging.getLogger(__name__)

class StockSyncService:
    """Service for syncing stock data from AlphaVantage"""
    
    def __init__(self):
        self.alpha_vantage = AlphaVantageService()
        self.sync_interval = 300  # 5 minutes
        self.last_sync_time = None
        self.is_syncing = False
        self.currently_syncing: Set[str] = set()  # Track which symbols are being synced
    
    async def sync_stock_data(self, symbol: str, include_overview: bool = False) -> Dict[str, Any]:
        """Sync data for a single stock"""
        # Check if this symbol is already being synced
        if symbol in self.currently_syncing:
            logger.warning(f"Symbol {symbol} is already being synced, skipping")
            existing_stock = get_stock_by_symbol(symbol)
            if existing_stock:
                return existing_stock
            raise ValueError(f"Symbol {symbol} sync in progress")
        
        try:
            # Mark as syncing to prevent duplicates
            self.currently_syncing.add(symbol)
            
            # Validate symbol format
            if not symbol or len(symbol) < 1 or len(symbol) > 10:
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            # Get quote data (this is the main data we need)
            quote_data = self.alpha_vantage.get_stock_quote(symbol)
            
            # Validate we got real data
            if not quote_data.get('price') or quote_data.get('price') <= 0:
                raise ValueError(f"Invalid price data for symbol {symbol}")
            
            # Only get overview data for individual stock requests (not bulk syncs)
            # This prevents the double API calls we saw in the logs
            overview_data = None
            if include_overview:
                try:
                    overview_data = self.alpha_vantage.get_company_overview(symbol)
                except Exception as e:
                    logger.warning(f"Failed to get overview for {symbol}: {e}")
            
            # Update database
            stock = create_or_update_stock_from_alpha_vantage(symbol, quote_data, overview_data)
            
            logger.info(f"Successfully synced stock {symbol}")
            return stock
            
        except Exception as e:
            logger.error(f"Failed to sync stock {symbol}: {e}")
            raise
        finally:
            # Always remove from syncing set
            self.currently_syncing.discard(symbol)
    
    async def sync_all_stocks(self, include_overview: bool = False) -> List[Dict[str, Any]]:
        """Sync data for all stocks in database"""
        if self.is_syncing:
            logger.warning("Sync already in progress")
            return []
        
        self.is_syncing = True
        synced_stocks = []
        
        try:
            stocks = get_all_stocks()
            logger.info(f"Starting sync for {len(stocks)} stocks")
            
            for stock in stocks:
                try:
                    # For bulk syncs, skip overview data to avoid double API calls
                    # This cuts the API calls in half and speeds up sync significantly
                    synced_stock = await self.sync_stock_data(stock['symbol'], include_overview=False)
                    synced_stocks.append(synced_stock)
                    logger.info(f"Synced {stock['symbol']} successfully")
                    
                    # No delay needed for mock responses - they're instant
                    # Only add delay if we're actually hitting the real API (not rate limited)
                    if not getattr(self.alpha_vantage, '_last_was_rate_limited', True):
                        await asyncio.sleep(12)  # Only delay for real API calls
                    # If rate limited (using mock), no delay needed
                    
                except Exception as e:
                    logger.error(f"Failed to sync {stock['symbol']}: {e}")
                    continue
            
            self.last_sync_time = datetime.now()
            logger.info(f"Completed sync for {len(synced_stocks)} stocks")
            
        except Exception as e:
            logger.error(f"Sync failed with error: {e}")
        finally:
            self.is_syncing = False
        
        return synced_stocks
    
    async def add_and_sync_stock(self, symbol: str) -> Dict[str, Any]:
        """Add a new stock and sync its data"""
        try:
            # Check if stock already exists
            existing_stock = get_stock_by_symbol(symbol)
            if existing_stock:
                logger.info(f"Stock {symbol} already exists, updating data")
                return await self.sync_stock_data(symbol, include_overview=True)
            
            # Add new stock with full data
            stock = await self.sync_stock_data(symbol, include_overview=True)
            logger.info(f"Added new stock {symbol}")
            return stock
            
        except Exception as e:
            logger.error(f"Failed to add and sync stock {symbol}: {e}")
            raise
    
    async def search_and_add_stock(self, keywords: str) -> List[Dict[str, Any]]:
        """Search for stocks and return results"""
        try:
            search_results = self.alpha_vantage.search_stocks(keywords)
            logger.info(f"Found {len(search_results)} stocks matching '{keywords}'")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search stocks with keywords '{keywords}': {e}")
            raise
    
    def should_sync(self) -> bool:
        """Check if stocks should be synced based on time interval"""
        if self.last_sync_time is None:
            return True
        
        time_since_last_sync = datetime.now() - self.last_sync_time
        return time_since_last_sync.total_seconds() > self.sync_interval
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            'is_syncing': self.is_syncing,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_interval': self.sync_interval,
            'should_sync': self.should_sync()
        }

# Global instance
stock_sync_service = StockSyncService()