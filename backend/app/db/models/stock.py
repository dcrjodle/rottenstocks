"""
Stock model for storing stock information.

Represents individual stocks with market data, ratings, and relationships
to other entities in the system.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class Stock(BaseModel):
    """
    Stock model representing individual securities.
    
    Stores basic stock information, current pricing, and market data.
    Links to ratings, social posts, and expert analyses.
    """
    
    __tablename__ = "stocks"
    
    # Basic stock information
    symbol: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        index=True,
        nullable=False,
        comment="Stock ticker symbol (e.g., AAPL, GOOGL)",
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Company name",
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Company description",
    )
    
    # Market information
    exchange: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Stock exchange (NYSE, NASDAQ, etc.)",
    )
    
    sector: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Market sector",
    )
    
    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Industry classification",
    )
    
    market_cap: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="Market capitalization in USD",
    )
    
    # Current pricing data
    current_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Current stock price",
    )
    
    previous_close: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Previous trading day close price",
    )
    
    day_high: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Day's high price",
    )
    
    day_low: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Day's low price",
    )
    
    volume: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Trading volume",
    )
    
    # Status and metadata
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the stock is actively tracked",
    )
    
    last_updated: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time stock data was updated",
    )
    
    # Relationships
    ratings: Mapped[List["Rating"]] = relationship(
        "Rating",
        back_populates="stock",
        cascade="all, delete-orphan",
    )
    
    social_posts: Mapped[List["SocialPost"]] = relationship(
        "SocialPost",
        back_populates="stock",
        cascade="all, delete-orphan",
    )
    
    def __init__(self, **kwargs):
        """Initialize Stock model with proper defaults."""
        # Set boolean defaults if not provided
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        
        # Call parent constructor (BaseModel handles ID and timestamps)
        super().__init__(**kwargs)
    
    # Computed properties
    @property
    def price_change(self) -> Optional[Decimal]:
        """Calculate price change from previous close."""
        if self.current_price and self.previous_close:
            return self.current_price - self.previous_close
        return None
    
    @property
    def price_change_percent(self) -> Optional[Decimal]:
        """Calculate percentage price change from previous close."""
        if self.current_price and self.previous_close and self.previous_close > 0:
            change = self.current_price - self.previous_close
            return (change / self.previous_close) * 100
        return None
    
    @property
    def is_up(self) -> Optional[bool]:
        """Check if stock is up from previous close."""
        price_change = self.price_change
        if price_change is not None:
            return price_change > 0
        return None
    
    def update_price_data(
        self,
        current_price: Decimal,
        previous_close: Optional[Decimal] = None,
        day_high: Optional[Decimal] = None,
        day_low: Optional[Decimal] = None,
        volume: Optional[int] = None,
    ) -> None:
        """Update stock price data."""
        self.current_price = current_price
        if previous_close is not None:
            self.previous_close = previous_close
        if day_high is not None:
            self.day_high = day_high
        if day_low is not None:
            self.day_low = day_low
        if volume is not None:
            self.volume = volume
        self.last_updated = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<Stock(symbol='{self.symbol}', name='{self.name}', price={self.current_price})>"


# Database indexes for optimal query performance
Index("idx_stocks_symbol", Stock.symbol)
Index("idx_stocks_exchange", Stock.exchange)
Index("idx_stocks_sector", Stock.sector)
Index("idx_stocks_active", Stock.is_active)
Index("idx_stocks_updated", Stock.last_updated)

# Composite indexes for common query patterns
Index("idx_stocks_exchange_sector", Stock.exchange, Stock.sector)
Index("idx_stocks_active_updated", Stock.is_active, Stock.last_updated)