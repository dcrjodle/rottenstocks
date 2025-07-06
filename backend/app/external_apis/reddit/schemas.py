"""
Reddit data schemas for financial social media analysis.

Defines Pydantic models for Reddit posts, comments, and users
with fields relevant to financial sentiment analysis.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class RedditUser(BaseModel):
    """Reddit user information."""
    
    username: str = Field(..., description="Reddit username")
    karma_comment: int = Field(0, description="Comment karma")
    karma_link: int = Field(0, description="Link karma")
    total_karma: int = Field(0, description="Total karma")
    account_age_days: Optional[int] = Field(None, description="Account age in days")
    is_verified: bool = Field(False, description="Whether account is verified")
    is_premium: bool = Field(False, description="Whether account has premium")
    
    @validator('total_karma', always=True)
    def calculate_total_karma(cls, v, values):
        """Calculate total karma from comment and link karma."""
        return values.get('karma_comment', 0) + values.get('karma_link', 0)
    
    @property
    def reputation_score(self) -> float:
        """Calculate reputation score based on karma and account age."""
        if self.account_age_days is None or self.account_age_days == 0:
            return 0.0
        
        # Base score from karma
        karma_score = min(self.total_karma / 10000, 1.0)  # Cap at 10k karma
        
        # Age multiplier (accounts older than 1 year get full multiplier)
        age_multiplier = min(self.account_age_days / 365, 1.0)
        
        # Premium/verified bonus
        bonus = 0.1 if (self.is_premium or self.is_verified) else 0.0
        
        return min(karma_score * age_multiplier + bonus, 1.0)


class RedditComment(BaseModel):
    """Reddit comment data."""
    
    id: str = Field(..., description="Comment ID")
    body: str = Field(..., description="Comment text")
    author: Optional[str] = Field(None, description="Author username")
    score: int = Field(0, description="Comment score (upvotes - downvotes)")
    created_utc: datetime = Field(..., description="Comment creation time")
    permalink: str = Field(..., description="Comment permalink")
    parent_id: Optional[str] = Field(None, description="Parent comment/post ID")
    depth: int = Field(0, description="Comment depth in thread")
    is_edited: bool = Field(False, description="Whether comment was edited")
    is_distinguished: bool = Field(False, description="Whether comment is distinguished")
    
    # Sentiment analysis fields (populated later)
    sentiment_score: Optional[float] = Field(None, description="Sentiment score (-1 to 1)")
    sentiment_confidence: Optional[float] = Field(None, description="Confidence in sentiment")
    mentions_stocks: bool = Field(False, description="Whether comment mentions stocks")
    extracted_symbols: List[str] = Field(default_factory=list, description="Stock symbols found")
    
    @property
    def quality_score(self) -> float:
        """Calculate comment quality score."""
        # Base score from upvotes (normalized)
        score_normalized = max(0, min(self.score / 100, 1.0))
        
        # Length bonus (longer comments often have more substance)
        length_bonus = min(len(self.body) / 1000, 0.2)
        
        # Distinguished comment bonus
        distinguished_bonus = 0.1 if self.is_distinguished else 0.0
        
        return min(score_normalized + length_bonus + distinguished_bonus, 1.0)


class RedditPost(BaseModel):
    """Reddit post data for financial analysis."""
    
    # Basic post information
    id: str = Field(..., description="Post ID")
    title: str = Field(..., description="Post title")
    selftext: str = Field("", description="Post text content")
    author: Optional[str] = Field(None, description="Author username")
    subreddit: str = Field(..., description="Subreddit name")
    
    # Post metrics
    score: int = Field(0, description="Post score (upvotes - downvotes)")
    upvote_ratio: float = Field(0.5, description="Upvote ratio")
    num_comments: int = Field(0, description="Number of comments")
    created_utc: datetime = Field(..., description="Post creation time")
    
    # Post metadata
    url: str = Field(..., description="Post URL")
    permalink: str = Field(..., description="Post permalink")
    flair_text: Optional[str] = Field(None, description="Post flair")
    is_original_content: bool = Field(False, description="Whether post is OC")
    is_self: bool = Field(True, description="Whether post is self-post")
    is_video: bool = Field(False, description="Whether post is video")
    is_pinned: bool = Field(False, description="Whether post is pinned")
    is_locked: bool = Field(False, description="Whether post is locked")
    is_archived: bool = Field(False, description="Whether post is archived")
    
    # Financial analysis fields
    mentions_stocks: bool = Field(False, description="Whether post mentions stocks")
    extracted_symbols: List[str] = Field(default_factory=list, description="Stock symbols found")
    sentiment_score: Optional[float] = Field(None, description="Sentiment score (-1 to 1)")
    sentiment_confidence: Optional[float] = Field(None, description="Confidence in sentiment")
    
    # Related comments (populated separately)
    top_comments: List[RedditComment] = Field(default_factory=list, description="Top comments")
    
    @property
    def full_text(self) -> str:
        """Get full post text (title + selftext)."""
        return f"{self.title}\n\n{self.selftext}".strip()
    
    @property
    def quality_score(self) -> float:
        """Calculate post quality score for filtering."""
        # Base score from upvotes (normalized to 0-1)
        score_normalized = max(0, min(self.score / 1000, 1.0))
        
        # Engagement score (comments relative to upvotes)
        engagement_score = min(self.num_comments / max(self.score, 1), 1.0) * 0.3
        
        # Upvote ratio bonus
        ratio_bonus = (self.upvote_ratio - 0.5) * 0.2
        
        # Content length bonus
        content_length = len(self.full_text)
        length_bonus = min(content_length / 2000, 0.2)
        
        # OC bonus
        oc_bonus = 0.1 if self.is_original_content else 0.0
        
        # Penalties
        penalties = 0.0
        if self.is_locked:
            penalties += 0.1
        if self.is_archived:
            penalties += 0.05
        
        total_score = score_normalized + engagement_score + ratio_bonus + length_bonus + oc_bonus - penalties
        return max(0.0, min(total_score, 1.0))
    
    @property
    def is_finance_related(self) -> bool:
        """Check if post is finance-related based on content and flair."""
        finance_keywords = {
            'stock', 'stocks', 'trading', 'investment', 'invest', 'portfolio',
            'market', 'bull', 'bear', 'earnings', 'dividend', 'options',
            'calls', 'puts', 'volatility', 'valuation', 'analysis'
        }
        
        # Check title and text for finance keywords
        full_text_lower = self.full_text.lower()
        has_finance_keywords = any(keyword in full_text_lower for keyword in finance_keywords)
        
        # Check flair
        finance_flair = False
        if self.flair_text:
            flair_lower = self.flair_text.lower()
            finance_flair = any(keyword in flair_lower for keyword in ['dd', 'analysis', 'discussion', 'news'])
        
        return has_finance_keywords or finance_flair or self.mentions_stocks


class SubredditInfo(BaseModel):
    """Subreddit information and metrics."""
    
    name: str = Field(..., description="Subreddit name")
    display_name: str = Field(..., description="Display name")
    description: str = Field("", description="Subreddit description")
    subscribers: int = Field(0, description="Number of subscribers")
    active_users: int = Field(0, description="Currently active users")
    created_utc: datetime = Field(..., description="Subreddit creation time")
    
    # Moderation info
    is_over_18: bool = Field(False, description="Whether subreddit is NSFW")
    is_quarantined: bool = Field(False, description="Whether subreddit is quarantined")
    is_private: bool = Field(False, description="Whether subreddit is private")
    
    # Finance relevance
    finance_relevance_score: float = Field(0.0, description="How relevant to finance (0-1)")
    
    @property
    def reputation_score(self) -> float:
        """Calculate subreddit reputation score."""
        # Base score from subscriber count
        subscriber_score = min(self.subscribers / 1000000, 1.0)  # Cap at 1M subscribers
        
        # Activity ratio (active users / total subscribers)
        if self.subscribers > 0:
            activity_ratio = min(self.active_users / self.subscribers, 0.1)
        else:
            activity_ratio = 0.0
        
        # Age bonus (older subreddits tend to be more established)
        age_days = (datetime.utcnow() - self.created_utc).days
        age_bonus = min(age_days / 3650, 0.2)  # Cap at 10 years
        
        # Penalties
        penalties = 0.0
        if self.is_quarantined:
            penalties += 0.5
        if self.is_over_18:
            penalties += 0.1
        
        total_score = subscriber_score + activity_ratio + age_bonus - penalties
        return max(0.0, min(total_score, 1.0))


class RedditSearchResult(BaseModel):
    """Result from Reddit search/collection operation."""
    
    posts: List[RedditPost] = Field(default_factory=list, description="Collected posts")
    comments: List[RedditComment] = Field(default_factory=list, description="Collected comments")
    subreddit_info: Optional[SubredditInfo] = Field(None, description="Subreddit information")
    
    # Collection metadata
    collection_time: datetime = Field(default_factory=datetime.utcnow, description="When data was collected")
    collection_method: str = Field("", description="How data was collected (hot, new, top, etc.)")
    query_parameters: dict = Field(default_factory=dict, description="Search parameters used")
    
    # Statistics
    total_posts: int = Field(0, description="Total posts found")
    total_comments: int = Field(0, description="Total comments found")
    finance_related_posts: int = Field(0, description="Finance-related posts found")
    
    @validator('total_posts', always=True)
    def calculate_total_posts(cls, v, values):
        """Calculate total posts from posts list."""
        return len(values.get('posts', []))
    
    @validator('total_comments', always=True)
    def calculate_total_comments(cls, v, values):
        """Calculate total comments from comments list."""
        return len(values.get('comments', []))
    
    @validator('finance_related_posts', always=True)
    def calculate_finance_posts(cls, v, values):
        """Calculate finance-related posts."""
        posts = values.get('posts', [])
        return sum(1 for post in posts if post.is_finance_related)
    
    @property
    def quality_score(self) -> float:
        """Calculate overall quality score of the collection."""
        if not self.posts:
            return 0.0
        
        # Average quality score of posts
        post_quality = sum(post.quality_score for post in self.posts) / len(self.posts)
        
        # Finance relevance bonus
        finance_ratio = self.finance_related_posts / self.total_posts if self.total_posts > 0 else 0
        finance_bonus = finance_ratio * 0.2
        
        # Engagement score (comments per post)
        engagement_score = min(self.total_comments / self.total_posts, 10) / 10 if self.total_posts > 0 else 0
        
        return min(post_quality + finance_bonus + engagement_score, 1.0)