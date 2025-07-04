"""
Alpha Vantage service layer.

Business logic for integrating Alpha Vantage data with the RottenStocks
application, including data transformation and caching.
"""

from decimal import Decimal

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import get_settings
from app.db.models.stock import Stock
from app.db.repositories.stock import StockRepository
from app.external_apis.alpha_vantage.client import AlphaVantageClient
from app.external_apis.alpha_vantage.schemas import (
    AlphaVantageOverview,
    AlphaVantageQuote,
    AlphaVantageSearchResults,
)

logger = get_logger(__name__)
settings = get_settings()


class AlphaVantageService:
    """
    Service for integrating Alpha Vantage data with RottenStocks.
    
    Handles data fetching, transformation, caching, and database updates.
    """

    def __init__(
        self,
        client: AlphaVantageClient,
        db: AsyncSession,
        redis_client: redis.Redis | None = None
    ):
        """
        Initialize Alpha Vantage service.
        
        Args:
            client: Alpha Vantage API client
            db: Database session
            redis_client: Redis client for caching
        """
        self.client = client
        self.db = db
        self.redis = redis_client
        self.stock_repository = StockRepository(db)

        # Cache TTL settings
        self.quote_cache_ttl = settings.CACHE_TTL_STOCK_PRICE
        self.overview_cache_ttl = 86400  # 24 hours for company data
        self.search_cache_ttl = 3600     # 1 hour for search results

        logger.info("Alpha Vantage service initialized")

    def _get_cache_key(self, key_type: str, identifier: str) -> str:
        """Generate Redis cache key."""
        return f"{settings.CACHE_PREFIX}:alpha_vantage:{key_type}:{identifier}"

    async def _get_cached_data(self, cache_key: str) -> dict | None:
        """Get data from cache."""
        if not self.redis:
            return None

        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception as e:
            logger.warning("Failed to read from cache", cache_key=cache_key, error=str(e))

        return None

    async def _set_cached_data(self, cache_key: str, data: dict, ttl: int) -> None:
        """Set data in cache."""
        if not self.redis:
            return

        try:
            import json
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning("Failed to write to cache", cache_key=cache_key, error=str(e))

    async def get_stock_quote(
        self,
        symbol: str,
        use_cache: bool = True
    ) -> AlphaVantageQuote | None:
        """
        Get real-time quote for a stock symbol.
        
        Args:
            symbol: Stock symbol
            use_cache: Whether to use cached data
            
        Returns:
            Quote data or None if not found
        """
        symbol = symbol.upper()
        cache_key = self._get_cache_key("quote", symbol)

        # Try cache first
        if use_cache:
            cached_data = await self._get_cached_data(cache_key)
            if cached_data:
                logger.debug("Quote found in cache", symbol=symbol)
                return AlphaVantageQuote(**cached_data)

        # Fetch from API
        try:
            logger.debug("Fetching quote from API", symbol=symbol)
            response = await self.client.get_quote(symbol)

            if response.success and response.data:
                # Cache the result
                if use_cache:
                    await self._set_cached_data(
                        cache_key,
                        response.data.dict(),
                        self.quote_cache_ttl
                    )

                return response.data
            logger.warning(
                "Failed to fetch quote",
                symbol=symbol,
                error=response.error.error_message if response.error else "Unknown error"
            )
            return None

        except Exception as e:
            logger.error("Error fetching quote", symbol=symbol, error=str(e))
            return None

    async def get_company_overview(
        self,
        symbol: str,
        use_cache: bool = True
    ) -> AlphaVantageOverview | None:
        """
        Get company overview for a stock symbol.
        
        Args:
            symbol: Stock symbol
            use_cache: Whether to use cached data
            
        Returns:
            Company overview data or None if not found
        """
        symbol = symbol.upper()
        cache_key = self._get_cache_key("overview", symbol)

        # Try cache first
        if use_cache:
            cached_data = await self._get_cached_data(cache_key)
            if cached_data:
                logger.debug("Overview found in cache", symbol=symbol)
                return AlphaVantageOverview(**cached_data)

        # Fetch from API
        try:
            logger.debug("Fetching overview from API", symbol=symbol)
            response = await self.client.get_company_overview(symbol)

            if response.success and response.data:
                # Cache the result
                if use_cache:
                    await self._set_cached_data(
                        cache_key,
                        response.data.dict(),
                        self.overview_cache_ttl
                    )

                return response.data
            logger.warning(
                "Failed to fetch overview",
                symbol=symbol,
                error=response.error.error_message if response.error else "Unknown error"
            )
            return None

        except Exception as e:
            logger.error("Error fetching overview", symbol=symbol, error=str(e))
            return None

    async def search_symbols(
        self,
        keywords: str,
        use_cache: bool = True
    ) -> AlphaVantageSearchResults | None:
        """
        Search for stock symbols.
        
        Args:
            keywords: Search keywords
            use_cache: Whether to use cached data
            
        Returns:
            Search results or None if error
        """
        cache_key = self._get_cache_key("search", keywords.lower())

        # Try cache first
        if use_cache:
            cached_data = await self._get_cached_data(cache_key)
            if cached_data:
                logger.debug("Search results found in cache", keywords=keywords)
                return AlphaVantageSearchResults(**cached_data)

        # Fetch from API
        try:
            logger.debug("Searching symbols via API", keywords=keywords)
            response = await self.client.search_symbols(keywords)

            if response.success and response.data:
                # Cache the result
                if use_cache:
                    await self._set_cached_data(
                        cache_key,
                        response.data.dict(),
                        self.search_cache_ttl
                    )

                return response.data
            logger.warning(
                "Failed to search symbols",
                keywords=keywords,
                error=response.error.error_message if response.error else "Unknown error"
            )
            return None

        except Exception as e:
            logger.error("Error searching symbols", keywords=keywords, error=str(e))
            return None

    async def update_stock_price(self, symbol: str) -> bool:
        """
        Update stock price in database from Alpha Vantage.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get quote from Alpha Vantage
            quote = await self.get_stock_quote(symbol, use_cache=False)
            if not quote:
                logger.warning("No quote data available for price update", symbol=symbol)
                return False

            # Find stock in database
            stock = await self.stock_repository.get_by_symbol(symbol)
            if not stock:
                logger.warning("Stock not found in database", symbol=symbol)
                return False

            # Update stock price data
            stock.update_price_data(
                current_price=quote.price,
                previous_close=quote.previous_close,
                day_high=quote.high_price,
                day_low=quote.low_price,
                volume=quote.volume,
            )

            await self.db.commit()

            logger.info(
                "Stock price updated successfully",
                symbol=symbol,
                new_price=quote.price,
                change=quote.change,
                change_percent=quote.change_percent
            )
            return True

        except Exception as e:
            logger.error("Failed to update stock price", symbol=symbol, error=str(e))
            await self.db.rollback()
            return False

    async def enrich_stock_data(self, symbol: str) -> bool:
        """
        Enrich stock data with Alpha Vantage company overview.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get overview from Alpha Vantage
            overview = await self.get_company_overview(symbol, use_cache=False)
            if not overview:
                logger.warning("No overview data available for enrichment", symbol=symbol)
                return False

            # Find stock in database
            stock = await self.stock_repository.get_by_symbol(symbol)
            if not stock:
                logger.warning("Stock not found in database", symbol=symbol)
                return False

            # Update stock with overview data
            update_data = {}

            if overview.name and overview.name != stock.name:
                update_data["name"] = overview.name

            if overview.description and not stock.description:
                update_data["description"] = overview.description

            if overview.sector and overview.sector != stock.sector:
                update_data["sector"] = overview.sector

            if overview.industry and overview.industry != stock.industry:
                update_data["industry"] = overview.industry

            if overview.exchange and overview.exchange != stock.exchange:
                update_data["exchange"] = overview.exchange

            if overview.market_capitalization:
                update_data["market_cap"] = Decimal(str(overview.market_capitalization))

            # Update if we have changes
            if update_data:
                await self.stock_repository.update(stock.id, **update_data)
                await self.db.commit()

                logger.info(
                    "Stock data enriched successfully",
                    symbol=symbol,
                    updated_fields=list(update_data.keys())
                )
            else:
                logger.debug("No new data to update for stock", symbol=symbol)

            return True

        except Exception as e:
            logger.error("Failed to enrich stock data", symbol=symbol, error=str(e))
            await self.db.rollback()
            return False

    async def sync_stock_prices(self, symbols: list[str]) -> dict[str, bool]:
        """
        Sync prices for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to success status
        """
        results = {}

        logger.info("Starting bulk price sync", symbols=symbols, count=len(symbols))

        for symbol in symbols:
            try:
                results[symbol] = await self.update_stock_price(symbol)
            except Exception as e:
                logger.error("Failed to sync price", symbol=symbol, error=str(e))
                results[symbol] = False

        successful = sum(1 for success in results.values() if success)
        logger.info(
            "Bulk price sync completed",
            total=len(symbols),
            successful=successful,
            failed=len(symbols) - successful
        )

        return results

    async def create_stock_from_search(self, symbol: str) -> Stock | None:
        """
        Create a new stock in database using Alpha Vantage data.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Created stock or None if failed
        """
        try:
            # Get both quote and overview
            quote = await self.get_stock_quote(symbol, use_cache=False)
            overview = await self.get_company_overview(symbol, use_cache=False)

            if not quote and not overview:
                logger.warning("No data available to create stock", symbol=symbol)
                return None

            # Check if stock already exists
            existing_stock = await self.stock_repository.get_by_symbol(symbol)
            if existing_stock:
                logger.warning("Stock already exists", symbol=symbol)
                return existing_stock

            # Prepare stock data
            stock_data = {
                "symbol": symbol.upper(),
                "name": overview.name if overview else symbol,
                "exchange": overview.exchange if overview else "UNKNOWN",
            }

            # Add optional fields from overview
            if overview:
                if overview.description:
                    stock_data["description"] = overview.description
                if overview.sector:
                    stock_data["sector"] = overview.sector
                if overview.industry:
                    stock_data["industry"] = overview.industry
                if overview.market_capitalization:
                    stock_data["market_cap"] = Decimal(str(overview.market_capitalization))

            # Add price data from quote
            if quote:
                stock_data.update({
                    "current_price": quote.price,
                    "previous_close": quote.previous_close,
                    "day_high": quote.high_price,
                    "day_low": quote.low_price,
                    "volume": quote.volume,
                })

            # Create stock in database
            stock = await self.stock_repository.create(**stock_data)
            await self.db.commit()

            logger.info("Stock created successfully from Alpha Vantage data", symbol=symbol)
            return stock

        except Exception as e:
            logger.error("Failed to create stock from Alpha Vantage", symbol=symbol, error=str(e))
            await self.db.rollback()
            return None

    async def get_cache_stats(self) -> dict[str, any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        if not self.redis:
            return {"cache_enabled": False}

        try:
            # Count cached items by type
            quote_pattern = self._get_cache_key("quote", "*")
            overview_pattern = self._get_cache_key("overview", "*")
            search_pattern = self._get_cache_key("search", "*")

            quote_keys = await self.redis.keys(quote_pattern)
            overview_keys = await self.redis.keys(overview_pattern)
            search_keys = await self.redis.keys(search_pattern)

            return {
                "cache_enabled": True,
                "cached_quotes": len(quote_keys),
                "cached_overviews": len(overview_keys),
                "cached_searches": len(search_keys),
                "total_cached_items": len(quote_keys) + len(overview_keys) + len(search_keys),
                "ttl_settings": {
                    "quotes": self.quote_cache_ttl,
                    "overviews": self.overview_cache_ttl,
                    "searches": self.search_cache_ttl,
                }
            }
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {"cache_enabled": True, "error": str(e)}
