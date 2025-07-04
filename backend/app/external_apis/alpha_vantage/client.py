"""
Alpha Vantage API client.

Provides methods for fetching stock market data from the Alpha Vantage API
including real-time quotes, company overviews, and historical time series.
"""


from structlog import get_logger

from app.core.config import get_settings
from app.external_apis.alpha_vantage.schemas import (
    AlphaVantageError,
    AlphaVantageOverview,
    AlphaVantageQuote,
    AlphaVantageResponse,
    AlphaVantageSearchResults,
    AlphaVantageTimeSeries,
)
from app.external_apis.base.client import BaseHTTPClient
from app.external_apis.base.exceptions import ExternalAPIError, ValidationError
from app.external_apis.base.rate_limiter import RateLimiter
from app.external_apis.base.retry import CircuitBreaker, RetryConfig

logger = get_logger(__name__)
settings = get_settings()


class AlphaVantageClient:
    """
    Alpha Vantage API client.
    
    Provides methods for fetching stock market data with automatic
    rate limiting, retries, and error handling.
    """

    BASE_URL = "https://www.alphavantage.co"

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None
    ):
        """
        Initialize Alpha Vantage client.
        
        Args:
            api_key: Alpha Vantage API key
            rate_limiter: Rate limiter instance
            retry_config: Retry configuration
            circuit_breaker: Circuit breaker instance
        """
        self.api_key = api_key

        # Initialize HTTP client
        self.http_client = BaseHTTPClient(
            base_url=self.BASE_URL,
            provider="alpha_vantage",
            rate_limiter=rate_limiter,
            retry_config=retry_config,
            circuit_breaker=circuit_breaker,
            timeout=30.0
        )

        logger.info("Alpha Vantage client initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the client."""
        await self.http_client.close()

    def _check_for_api_error(self, response_data: dict) -> None:
        """
        Check API response for errors.
        
        Args:
            response_data: Raw API response
            
        Raises:
            ExternalAPIError: If API returned an error
        """
        # Check for various error indicators
        if "Error Message" in response_data:
            error = AlphaVantageError(**response_data)
            raise ExternalAPIError(
                error.error_message,
                provider="alpha_vantage",
                response_data=response_data
            )

        if "Note" in response_data and "API call frequency" in response_data["Note"]:
            raise ExternalAPIError(
                "API call frequency limit reached",
                provider="alpha_vantage",
                response_data=response_data
            )

        if "Information" in response_data:
            # This usually indicates rate limiting or invalid parameters
            raise ExternalAPIError(
                response_data["Information"],
                provider="alpha_vantage",
                response_data=response_data
            )

    async def get_quote(self, symbol: str) -> AlphaVantageResponse:
        """
        Get real-time quote for a stock symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Response with quote data or error
        """
        try:
            logger.debug("Fetching quote", symbol=symbol)

            response_data = await self.http_client.get(
                "/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.api_key
                }
            )

            # Check for errors
            self._check_for_api_error(response_data)

            # Parse quote data
            if "Global Quote" not in response_data:
                raise ValidationError(
                    f"Invalid quote response format for {symbol}",
                    provider="alpha_vantage",
                    response_data=response_data
                )

            quote_data = response_data["Global Quote"]
            if not quote_data:
                raise ValidationError(
                    f"Empty quote data for {symbol}",
                    provider="alpha_vantage",
                    response_data=response_data
                )

            quote = AlphaVantageQuote(**quote_data)

            logger.info("Quote fetched successfully", symbol=symbol, price=quote.price)
            return AlphaVantageResponse.success_response(quote, response_data)

        except ValidationError as e:
            # Handle validation errors as error responses
            logger.warning("Validation error in quote fetch", symbol=symbol, error=str(e))
            error = AlphaVantageError(error_message=str(e))
            return AlphaVantageResponse.error_response(error)
        except ExternalAPIError:
            # Re-raise other API errors (rate limits, network issues, etc.)
            raise
        except Exception as e:
            logger.error("Failed to fetch quote", symbol=symbol, error=str(e))
            error = AlphaVantageError(error_message=f"Failed to fetch quote: {e!s}")
            return AlphaVantageResponse.error_response(error)

    async def get_company_overview(self, symbol: str) -> AlphaVantageResponse:
        """
        Get company overview for a stock symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Response with company overview data or error
        """
        try:
            logger.debug("Fetching company overview", symbol=symbol)

            response_data = await self.http_client.get(
                "/query",
                params={
                    "function": "OVERVIEW",
                    "symbol": symbol,
                    "apikey": self.api_key
                }
            )

            # Check for errors
            self._check_for_api_error(response_data)

            # Check if response is empty (invalid symbol)
            if not response_data or response_data.get("Symbol") != symbol:
                raise ValidationError(
                    f"Invalid or empty overview data for {symbol}",
                    provider="alpha_vantage",
                    response_data=response_data
                )

            overview = AlphaVantageOverview(**response_data)

            logger.info("Company overview fetched successfully", symbol=symbol, name=overview.name)
            return AlphaVantageResponse.success_response(overview, response_data)

        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error("Failed to fetch company overview", symbol=symbol, error=str(e))
            error = AlphaVantageError(error_message=f"Failed to fetch overview: {e!s}")
            return AlphaVantageResponse.error_response(error)

    async def get_daily_time_series(
        self,
        symbol: str,
        output_size: str = "compact"
    ) -> AlphaVantageResponse:
        """
        Get daily time series data for a stock symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            output_size: 'compact' (last 100 days) or 'full' (all data)
            
        Returns:
            Response with time series data or error
        """
        try:
            logger.debug("Fetching daily time series", symbol=symbol, output_size=output_size)

            response_data = await self.http_client.get(
                "/query",
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": output_size,
                    "apikey": self.api_key
                }
            )

            # Check for errors
            self._check_for_api_error(response_data)

            # Parse time series data
            time_series = AlphaVantageTimeSeries.from_api_response(response_data, symbol)

            logger.info(
                "Daily time series fetched successfully",
                symbol=symbol,
                data_points=len(time_series.data)
            )
            return AlphaVantageResponse.success_response(time_series, response_data)

        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error("Failed to fetch daily time series", symbol=symbol, error=str(e))
            error = AlphaVantageError(error_message=f"Failed to fetch time series: {e!s}")
            return AlphaVantageResponse.error_response(error)

    async def search_symbols(self, keywords: str) -> AlphaVantageResponse:
        """
        Search for stock symbols using keywords.
        
        Args:
            keywords: Search keywords
            
        Returns:
            Response with search results or error
        """
        try:
            logger.debug("Searching symbols", keywords=keywords)

            response_data = await self.http_client.get(
                "/query",
                params={
                    "function": "SYMBOL_SEARCH",
                    "keywords": keywords,
                    "apikey": self.api_key
                }
            )

            # Check for errors
            self._check_for_api_error(response_data)

            # Parse search results
            search_results = AlphaVantageSearchResults.from_api_response(response_data)

            logger.info(
                "Symbol search completed successfully",
                keywords=keywords,
                results_count=len(search_results.best_matches)
            )
            return AlphaVantageResponse.success_response(search_results, response_data)

        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error("Failed to search symbols", keywords=keywords, error=str(e))
            error = AlphaVantageError(error_message=f"Failed to search symbols: {e!s}")
            return AlphaVantageResponse.error_response(error)

    async def get_batch_quotes(self, symbols: list[str]) -> dict[str, AlphaVantageResponse]:
        """
        Get quotes for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to their quote responses
        """
        results = {}

        logger.info("Fetching batch quotes", symbols=symbols, count=len(symbols))

        for symbol in symbols:
            try:
                results[symbol] = await self.get_quote(symbol)
            except Exception as e:
                logger.error("Failed to fetch quote in batch", symbol=symbol, error=str(e))
                error = AlphaVantageError(error_message=f"Batch quote failed: {e!s}")
                results[symbol] = AlphaVantageResponse.error_response(error)

        logger.info("Batch quotes completed", total=len(symbols), success=len([r for r in results.values() if r.success]))
        return results

    async def health_check(self) -> dict[str, any]:
        """
        Perform health check on Alpha Vantage API.
        
        Returns:
            Health check results
        """
        try:
            # Try to fetch a quote for a well-known stock
            response = await self.get_quote("AAPL")

            return {
                "provider": "alpha_vantage",
                "status": "healthy" if response.success else "unhealthy",
                "test_symbol": "AAPL",
                "api_accessible": response.success,
                "error": response.error.error_message if response.error else None
            }
        except Exception as e:
            return {
                "provider": "alpha_vantage",
                "status": "unhealthy",
                "test_symbol": "AAPL",
                "api_accessible": False,
                "error": str(e)
            }
