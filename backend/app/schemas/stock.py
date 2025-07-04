"""
Stock Pydantic schemas for request/response validation.

Defines schemas for stock creation, updates, and API responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, validator


class StockBase(BaseModel):
    """Base stock schema with common fields."""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    exchange: str = Field(..., min_length=1, max_length=10, description="Stock exchange")
    sector: Optional[str] = Field(None, max_length=100, description="Market sector")
    industry: Optional[str] = Field(None, max_length=100, description="Industry classification")
    market_cap: Optional[Decimal] = Field(None, ge=0, description="Market capitalization in USD")
    
    @validator('symbol')
    def symbol_must_be_uppercase(cls, v):
        """Ensure symbol is uppercase."""
        return v.upper() if v else v


class StockCreate(StockBase):
    """Schema for creating a new stock."""
    
    current_price: Optional[Decimal] = Field(None, gt=0, description="Current stock price")
    previous_close: Optional[Decimal] = Field(None, gt=0, description="Previous close price")
    day_high: Optional[Decimal] = Field(None, gt=0, description="Day's high price")
    day_low: Optional[Decimal] = Field(None, gt=0, description="Day's low price")
    volume: Optional[int] = Field(None, ge=0, description="Trading volume")
    is_active: bool = Field(True, description="Whether the stock is actively tracked")


class StockUpdate(BaseModel):
    """Schema for updating an existing stock."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    exchange: Optional[str] = Field(None, min_length=1, max_length=10)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market_cap: Optional[Decimal] = Field(None, ge=0)
    current_price: Optional[Decimal] = Field(None, gt=0)
    previous_close: Optional[Decimal] = Field(None, gt=0)
    day_high: Optional[Decimal] = Field(None, gt=0)
    day_low: Optional[Decimal] = Field(None, gt=0)
    volume: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class StockPriceUpdate(BaseModel):
    """Schema for updating stock price data only."""
    
    current_price: Decimal = Field(..., gt=0, description="Current stock price")
    previous_close: Optional[Decimal] = Field(None, gt=0, description="Previous close price")
    day_high: Optional[Decimal] = Field(None, gt=0, description="Day's high price")
    day_low: Optional[Decimal] = Field(None, gt=0, description="Day's low price")
    volume: Optional[int] = Field(None, ge=0, description="Trading volume")


class StockResponse(StockBase):
    """Schema for stock API responses."""
    
    id: str = Field(..., description="Stock ID")
    current_price: Optional[Decimal] = Field(None, description="Current stock price")
    previous_close: Optional[Decimal] = Field(None, description="Previous close price")
    day_high: Optional[Decimal] = Field(None, description="Day's high price")
    day_low: Optional[Decimal] = Field(None, description="Day's low price")
    volume: Optional[int] = Field(None, description="Trading volume")
    is_active: bool = Field(..., description="Whether the stock is actively tracked")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    
    # Computed fields
    price_change: Optional[Decimal] = Field(None, description="Price change from previous close")
    price_change_percent: Optional[Decimal] = Field(None, description="Percentage price change")
    is_up: Optional[bool] = Field(None, description="Whether price is up from previous close")
    
    class Config:
        from_attributes = True


class StockListResponse(BaseModel):
    """Schema for paginated stock list responses."""
    
    stocks: list[StockResponse] = Field(..., description="List of stocks")
    total: int = Field(..., description="Total number of stocks")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class StockSearch(BaseModel):
    """Schema for stock search parameters."""
    
    query: Optional[str] = Field(None, description="Search query for symbol or name")
    exchange: Optional[str] = Field(None, description="Filter by exchange")
    sector: Optional[str] = Field(None, description="Filter by sector")
    industry: Optional[str] = Field(None, description="Filter by industry")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Maximum price filter")
    min_market_cap: Optional[Decimal] = Field(None, ge=0, description="Minimum market cap filter")
    max_market_cap: Optional[Decimal] = Field(None, ge=0, description="Maximum market cap filter")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    
    @validator('max_price')
    def max_price_greater_than_min(cls, v, values):
        """Ensure max_price is greater than min_price if both provided."""
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v <= values['min_price']:
                raise ValueError('max_price must be greater than min_price')
        return v
    
    @validator('max_market_cap')
    def max_market_cap_greater_than_min(cls, v, values):
        """Ensure max_market_cap is greater than min_market_cap if both provided."""
        if v is not None and 'min_market_cap' in values and values['min_market_cap'] is not None:
            if v <= values['min_market_cap']:
                raise ValueError('max_market_cap must be greater than min_market_cap')
        return v


class StockBulkCreate(BaseModel):
    """Schema for bulk stock creation."""
    
    stocks: list[StockCreate] = Field(..., min_items=1, max_items=100, description="List of stocks to create")


class StockBulkResponse(BaseModel):
    """Schema for bulk operation responses."""
    
    created: int = Field(..., description="Number of stocks created")
    updated: int = Field(..., description="Number of stocks updated")
    errors: list[str] = Field(default_factory=list, description="List of errors encountered")
    stocks: list[StockResponse] = Field(default_factory=list, description="Successfully processed stocks")