"""
Pydantic schemas for Alpha Vantage API responses.

Defines data models for parsing and validating Alpha Vantage API responses
including quotes, company overviews, time series data, and search results.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AlphaVantageError(BaseModel):
    """Alpha Vantage API error response."""

    error_message: str = Field(..., alias="Error Message")
    note: str | None = Field(None, alias="Note")
    information: str | None = Field(None, alias="Information")

    class Config:
        populate_by_name = True


class AlphaVantageQuote(BaseModel):
    """Real-time stock quote from Alpha Vantage."""

    symbol: str = Field(..., alias="01. symbol")
    open_price: Decimal = Field(..., alias="02. open")
    high_price: Decimal = Field(..., alias="03. high")
    low_price: Decimal = Field(..., alias="04. low")
    price: Decimal = Field(..., alias="05. price")
    volume: int = Field(..., alias="06. volume")
    latest_trading_day: datetime = Field(..., alias="07. latest trading day")
    previous_close: Decimal = Field(..., alias="08. previous close")
    change: Decimal = Field(..., alias="09. change")
    change_percent: str = Field(..., alias="10. change percent")

    @field_validator("latest_trading_day", mode="before")
    @classmethod
    def parse_trading_day(cls, v):
        """Parse trading day from string."""
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d").date()
        return v

    @field_validator("change_percent", mode="before")
    @classmethod
    def clean_change_percent(cls, v):
        """Clean change percent string."""
        if isinstance(v, str):
            return v.replace("%", "")
        return v

    @property
    def change_percent_decimal(self) -> Decimal:
        """Get change percent as decimal."""
        return Decimal(self.change_percent)

    class Config:
        populate_by_name = True


class AlphaVantageOverview(BaseModel):
    """Company overview from Alpha Vantage."""

    symbol: str = Field(..., alias="Symbol")
    asset_type: str = Field(..., alias="AssetType")
    name: str = Field(..., alias="Name")
    description: str = Field(..., alias="Description")
    cik: str | None = Field(None, alias="CIK")
    exchange: str = Field(..., alias="Exchange")
    currency: str = Field(..., alias="Currency")
    country: str = Field(..., alias="Country")
    sector: str = Field(..., alias="Sector")
    industry: str = Field(..., alias="Industry")
    address: str | None = Field(None, alias="Address")
    fiscal_year_end: str | None = Field(None, alias="FiscalYearEnd")
    latest_quarter: datetime | None = Field(None, alias="LatestQuarter")

    # Financial metrics
    market_capitalization: int | None = Field(None, alias="MarketCapitalization")
    ebitda: int | None = Field(None, alias="EBITDA")
    pe_ratio: Decimal | None = Field(None, alias="PERatio")
    peg_ratio: Decimal | None = Field(None, alias="PEGRatio")
    book_value: Decimal | None = Field(None, alias="BookValue")
    dividend_per_share: Decimal | None = Field(None, alias="DividendPerShare")
    dividend_yield: Decimal | None = Field(None, alias="DividendYield")
    eps: Decimal | None = Field(None, alias="EPS")
    revenue_per_share_ttm: Decimal | None = Field(None, alias="RevenuePerShareTTM")
    profit_margin: Decimal | None = Field(None, alias="ProfitMargin")
    operating_margin_ttm: Decimal | None = Field(None, alias="OperatingMarginTTM")
    return_on_assets_ttm: Decimal | None = Field(None, alias="ReturnOnAssetsTTM")
    return_on_equity_ttm: Decimal | None = Field(None, alias="ReturnOnEquityTTM")
    revenue_ttm: int | None = Field(None, alias="RevenueTTM")
    gross_profit_ttm: int | None = Field(None, alias="GrossProfitTTM")
    diluted_eps_ttm: Decimal | None = Field(None, alias="DilutedEPSTTM")
    quarterly_earnings_growth_yoy: Decimal | None = Field(None, alias="QuarterlyEarningsGrowthYOY")
    quarterly_revenue_growth_yoy: Decimal | None = Field(None, alias="QuarterlyRevenueGrowthYOY")

    # Trading metrics
    analyst_target_price: Decimal | None = Field(None, alias="AnalystTargetPrice")
    trailing_pe: Decimal | None = Field(None, alias="TrailingPE")
    forward_pe: Decimal | None = Field(None, alias="ForwardPE")
    price_to_sales_ratio_ttm: Decimal | None = Field(None, alias="PriceToSalesRatioTTM")
    price_to_book_ratio: Decimal | None = Field(None, alias="PriceToBookRatio")
    ev_to_revenue: Decimal | None = Field(None, alias="EVToRevenue")
    ev_to_ebitda: Decimal | None = Field(None, alias="EVToEBITDA")
    beta: Decimal | None = Field(None, alias="Beta")
    week_52_high: Decimal | None = Field(None, alias="52WeekHigh")
    week_52_low: Decimal | None = Field(None, alias="52WeekLow")
    day_50_moving_average: Decimal | None = Field(None, alias="50DayMovingAverage")
    day_200_moving_average: Decimal | None = Field(None, alias="200DayMovingAverage")
    shares_outstanding: int | None = Field(None, alias="SharesOutstanding")
    dividend_date: datetime | None = Field(None, alias="DividendDate")
    ex_dividend_date: datetime | None = Field(None, alias="ExDividendDate")

    @field_validator("latest_quarter", "dividend_date", "ex_dividend_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Parse date from string."""
        if isinstance(v, str) and v not in ["None", ""]:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return None
        return v if v not in ["None", ""] else None

    @field_validator(
        "market_capitalization", "ebitda", "revenue_ttm", "gross_profit_ttm", "shares_outstanding",
        mode="before"
    )
    @classmethod
    def parse_int_or_none(cls, v):
        """Parse integer or return None."""
        if isinstance(v, str):
            if v in ["None", "", "-"]:
                return None
            try:
                return int(v)
            except ValueError:
                return None
        return v

    @field_validator(
        "pe_ratio", "peg_ratio", "book_value", "dividend_per_share", "dividend_yield",
        "eps", "revenue_per_share_ttm", "profit_margin", "operating_margin_ttm",
        "return_on_assets_ttm", "return_on_equity_ttm", "diluted_eps_ttm",
        "quarterly_earnings_growth_yoy", "quarterly_revenue_growth_yoy",
        "analyst_target_price", "trailing_pe", "forward_pe", "price_to_sales_ratio_ttm",
        "price_to_book_ratio", "ev_to_revenue", "ev_to_ebitda", "beta",
        "week_52_high", "week_52_low", "day_50_moving_average", "day_200_moving_average",
        mode="before"
    )
    @classmethod
    def parse_decimal_or_none(cls, v):
        """Parse decimal or return None."""
        if isinstance(v, str):
            if v in ["None", "", "-"]:
                return None
            try:
                return Decimal(v)
            except (ValueError, InvalidOperation):
                return None
        return v

    class Config:
        populate_by_name = True


class AlphaVantageTimeSeriesData(BaseModel):
    """Single time series data point."""

    open_price: Decimal = Field(..., alias="1. open")
    high_price: Decimal = Field(..., alias="2. high")
    low_price: Decimal = Field(..., alias="3. low")
    close_price: Decimal = Field(..., alias="4. close")
    volume: int = Field(..., alias="5. volume")

    class Config:
        populate_by_name = True


class AlphaVantageTimeSeries(BaseModel):
    """Time series data from Alpha Vantage."""

    symbol: str
    last_refreshed: datetime
    time_zone: str
    interval: str | None = None
    output_size: str | None = None
    data: dict[datetime, AlphaVantageTimeSeriesData]

    @classmethod
    def from_api_response(cls, response: dict[str, Any], symbol: str) -> "AlphaVantageTimeSeries":
        """Create from API response."""
        # Extract metadata
        metadata_key = None
        data_key = None

        for key in response:
            if "Meta Data" in key:
                metadata_key = key
            elif "Time Series" in key:
                data_key = key

        if not metadata_key or not data_key:
            raise ValueError("Invalid time series response format")

        metadata = response[metadata_key]
        time_series_data = response[data_key]

        # Parse metadata
        last_refreshed = datetime.strptime(
            metadata["3. Last Refreshed"],
            "%Y-%m-%d %H:%M:%S" if " " in metadata["3. Last Refreshed"] else "%Y-%m-%d"
        )

        # Parse time series data
        parsed_data = {}
        for date_str, values in time_series_data.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            parsed_data[date_obj] = AlphaVantageTimeSeriesData(**values)

        return cls(
            symbol=symbol,
            last_refreshed=last_refreshed,
            time_zone=metadata["4. Time Zone"],
            interval=metadata.get("4. Interval"),
            output_size=metadata.get("5. Output Size"),
            data=parsed_data
        )


class AlphaVantageSearchMatch(BaseModel):
    """Single search result match."""

    symbol: str = Field(..., alias="1. symbol")
    name: str = Field(..., alias="2. name")
    type: str = Field(..., alias="3. type")
    region: str = Field(..., alias="4. region")
    market_open: str = Field(..., alias="5. marketOpen")
    market_close: str = Field(..., alias="6. marketClose")
    timezone: str = Field(..., alias="7. timezone")
    currency: str = Field(..., alias="8. currency")
    match_score: Decimal = Field(..., alias="9. matchScore")

    class Config:
        populate_by_name = True


class AlphaVantageSearchResults(BaseModel):
    """Search results from Alpha Vantage."""

    best_matches: list[AlphaVantageSearchMatch]

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "AlphaVantageSearchResults":
        """Create from API response."""
        matches = []
        for match_data in response.get("bestMatches", []):
            matches.append(AlphaVantageSearchMatch(**match_data))

        return cls(best_matches=matches)


# Response wrapper for handling errors
class AlphaVantageResponse(BaseModel):
    """Wrapper for Alpha Vantage API responses."""

    success: bool
    data: Any | None = None
    error: AlphaVantageError | None = None
    raw_response: dict[str, Any] | None = None

    @classmethod
    def success_response(cls, data: Any, raw_response: dict[str, Any] | None = None):
        """Create successful response."""
        return cls(success=True, data=data, raw_response=raw_response)

    @classmethod
    def error_response(cls, error: AlphaVantageError, raw_response: dict[str, Any] | None = None):
        """Create error response."""
        return cls(success=False, error=error, raw_response=raw_response)
