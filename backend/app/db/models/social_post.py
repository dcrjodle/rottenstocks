"""
Social post model for storing social media data and sentiment.

Represents social media posts from Reddit, Twitter, and other platforms
that mention stocks, with sentiment analysis and engagement metrics.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class Platform(PyEnum):
    """Social media platforms."""
    REDDIT = "reddit"
    TWITTER = "twitter"
    STOCKTWITS = "stocktwits"
    DISCORD = "discord"
    OTHER = "other"


class SentimentType(PyEnum):
    """Sentiment analysis results."""
    VERY_POSITIVE = "very_positive"  # 0.8 - 1.0
    POSITIVE = "positive"             # 0.6 - 0.8
    NEUTRAL = "neutral"               # 0.4 - 0.6
    NEGATIVE = "negative"             # 0.2 - 0.4
    VERY_NEGATIVE = "very_negative"   # 0.0 - 0.2


class SocialPost(BaseModel):
    """
    Social media post model for sentiment analysis.
    
    Stores posts from various social platforms that mention stocks,
    with sentiment analysis, engagement metrics, and content analysis.
    """
    
    __tablename__ = "social_posts"
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint(
            "platform", "platform_post_id",
            name="uq_social_posts_platform_id"
        ),
    )
    
    # Foreign key relationships
    stock_id: Mapped[str] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the stock mentioned in the post",
    )
    
    # Platform and post identification
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform),
        nullable=False,
        comment="Social media platform where post originated",
    )
    
    platform_post_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Unique post ID from the platform",
    )
    
    url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Direct URL to the post",
    )
    
    # Author information
    author_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Username of the post author",
    )
    
    author_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Platform-specific author ID",
    )
    
    author_follower_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of followers the author has",
    )
    
    # Post content
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Post title (for Reddit posts, forum posts, etc.)",
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full text content of the post",
    )
    
    content_excerpt: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Shortened excerpt for display",
    )
    
    # Engagement metrics
    score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Platform-specific score (Reddit upvotes, Twitter likes, etc.)",
    )
    
    upvotes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of upvotes (Reddit)",
    )
    
    downvotes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of downvotes (Reddit)",
    )
    
    comment_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of comments/replies",
    )
    
    share_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of shares/retweets",
    )
    
    # Sentiment analysis
    sentiment_type: Mapped[Optional[SentimentType]] = mapped_column(
        Enum(SentimentType),
        nullable=True,
        comment="Categorized sentiment analysis result",
    )
    
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Sentiment score from 0.00 (very negative) to 1.00 (very positive)",
    )
    
    sentiment_confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Confidence in sentiment analysis (0.00 to 1.00)",
    )
    
    # Content analysis
    mentions_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of times the stock is mentioned in the post",
    )
    
    has_financial_data: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether post contains financial data or analysis",
    )
    
    contains_prediction: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether post contains price predictions",
    )
    
    # Platform-specific metadata
    subreddit: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Reddit subreddit (for Reddit posts)",
    )
    
    hashtags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Hashtags mentioned in the post (JSON array)",
    )
    
    # Timestamps
    posted_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the post was originally created",
    )
    
    collected_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When we collected/scraped this post",
    )
    
    analyzed_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When sentiment analysis was performed",
    )
    
    # Relationships
    stock: Mapped["Stock"] = relationship(
        "Stock",
        back_populates="social_posts",
    )
    
    def __init__(self, **kwargs):
        """Initialize SocialPost model with proper defaults."""
        # Set default values if not provided
        if 'mentions_count' not in kwargs:
            kwargs['mentions_count'] = 1
        if 'has_financial_data' not in kwargs:
            kwargs['has_financial_data'] = False
        if 'contains_prediction' not in kwargs:
            kwargs['contains_prediction'] = False
        
        # Call parent constructor (BaseModel handles ID and timestamps)
        super().__init__(**kwargs)
    
    # Computed properties
    @property
    def engagement_score(self) -> int:
        """Calculate overall engagement score."""
        score = 0
        if self.score:
            score += self.score
        if self.comment_count:
            score += self.comment_count * 2  # Comments weighted higher
        if self.share_count:
            score += self.share_count * 3  # Shares weighted highest
        return score
    
    @property
    def is_positive_sentiment(self) -> bool:
        """Check if sentiment is positive."""
        return self.sentiment_type in [SentimentType.POSITIVE, SentimentType.VERY_POSITIVE]
    
    @property
    def is_negative_sentiment(self) -> bool:
        """Check if sentiment is negative."""
        return self.sentiment_type in [SentimentType.NEGATIVE, SentimentType.VERY_NEGATIVE]
    
    @property
    def sentiment_display(self) -> str:
        """Get display-friendly sentiment text."""
        if self.sentiment_type:
            return self.sentiment_type.value.replace("_", " ").title()
        return "Unknown"
    
    @property
    def platform_display(self) -> str:
        """Get display-friendly platform name."""
        return self.platform.value.title()
    
    def update_sentiment(
        self,
        sentiment_score: Decimal,
        confidence: Decimal,
        analyzed_at: Optional[DateTime] = None,
    ) -> None:
        """Update sentiment analysis results."""
        self.sentiment_score = max(Decimal("0.00"), min(Decimal("1.00"), sentiment_score))
        self.sentiment_confidence = max(Decimal("0.00"), min(Decimal("1.00"), confidence))
        
        # Categorize sentiment based on score
        if sentiment_score >= Decimal("0.8"):
            self.sentiment_type = SentimentType.VERY_POSITIVE
        elif sentiment_score >= Decimal("0.6"):
            self.sentiment_type = SentimentType.POSITIVE
        elif sentiment_score >= Decimal("0.4"):
            self.sentiment_type = SentimentType.NEUTRAL
        elif sentiment_score >= Decimal("0.2"):
            self.sentiment_type = SentimentType.NEGATIVE
        else:
            self.sentiment_type = SentimentType.VERY_NEGATIVE
        
        self.analyzed_at = analyzed_at or datetime.utcnow()
    
    def update_engagement(
        self,
        score: Optional[int] = None,
        upvotes: Optional[int] = None,
        downvotes: Optional[int] = None,
        comment_count: Optional[int] = None,
        share_count: Optional[int] = None,
    ) -> None:
        """Update engagement metrics."""
        if score is not None:
            self.score = score
        if upvotes is not None:
            self.upvotes = upvotes
        if downvotes is not None:
            self.downvotes = downvotes
        if comment_count is not None:
            self.comment_count = comment_count
        if share_count is not None:
            self.share_count = share_count
    
    def __repr__(self) -> str:
        stock_symbol = self.stock.symbol if self.stock else "Unknown"
        sentiment_display = self.sentiment_type.value if self.sentiment_type else "unknown"
        return f"<SocialPost(platform='{self.platform.value}', stock='{stock_symbol}', sentiment='{sentiment_display}')>"


# Database indexes for optimal query performance
Index("idx_social_posts_stock", SocialPost.stock_id)
Index("idx_social_posts_platform", SocialPost.platform)
Index("idx_social_posts_sentiment", SocialPost.sentiment_type)
Index("idx_social_posts_score", SocialPost.sentiment_score)
Index("idx_social_posts_posted", SocialPost.posted_at)
Index("idx_social_posts_collected", SocialPost.collected_at)
Index("idx_social_posts_author", SocialPost.author_username)

# Composite indexes for common query patterns
Index("idx_social_posts_stock_platform", SocialPost.stock_id, SocialPost.platform)
Index("idx_social_posts_stock_posted", SocialPost.stock_id, SocialPost.posted_at)
Index("idx_social_posts_platform_posted", SocialPost.platform, SocialPost.posted_at)
Index("idx_social_posts_sentiment_posted", SocialPost.sentiment_type, SocialPost.posted_at)

