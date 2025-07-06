"""
Tests for Reddit data schemas.

Tests the Pydantic models used for Reddit data structures
including validation, computed properties, and data processing.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from app.external_apis.reddit.schemas import (
    RedditPost,
    RedditComment,
    RedditUser,
    SubredditInfo,
    RedditSearchResult
)


class TestRedditUser:
    """Test cases for RedditUser schema."""

    def test_reddit_user_creation(self):
        """Test basic Reddit user creation."""
        user = RedditUser(
            username="test_user",
            karma_comment=1500,
            karma_link=300,
            account_age_days=365,
            is_verified=True,
            is_premium=False
        )
        
        assert user.username == "test_user"
        assert user.total_karma == 1800
        assert user.account_age_days == 365

    def test_total_karma_calculation(self):
        """Test automatic total karma calculation."""
        user = RedditUser(
            username="test_user",
            karma_comment=1000,
            karma_link=500
        )
        
        assert user.total_karma == 1500

    def test_reputation_score_calculation(self):
        """Test reputation score calculation."""
        # High karma, old account
        user1 = RedditUser(
            username="veteran_user",
            karma_comment=15000,
            karma_link=5000,
            account_age_days=1000,
            is_verified=True
        )
        
        # Low karma, new account
        user2 = RedditUser(
            username="new_user", 
            karma_comment=100,
            karma_link=50,
            account_age_days=30
        )
        
        assert user1.reputation_score > user2.reputation_score
        assert 0 <= user1.reputation_score <= 1
        assert 0 <= user2.reputation_score <= 1

    def test_reputation_score_no_age(self):
        """Test reputation score when account age is None."""
        user = RedditUser(
            username="unknown_age_user",
            karma_comment=1000,
            karma_link=500,
            account_age_days=None
        )
        
        assert user.reputation_score == 0.0

    def test_reputation_score_premium_bonus(self):
        """Test reputation score premium user bonus."""
        user_premium = RedditUser(
            username="premium_user",
            karma_comment=1000,
            karma_link=500,
            account_age_days=365,
            is_premium=True
        )
        
        user_regular = RedditUser(
            username="regular_user",
            karma_comment=1000,
            karma_link=500,
            account_age_days=365,
            is_premium=False
        )
        
        assert user_premium.reputation_score > user_regular.reputation_score


class TestRedditComment:
    """Test cases for RedditComment schema."""

    def test_reddit_comment_creation(self):
        """Test basic Reddit comment creation."""
        comment = RedditComment(
            id="comment123",
            body="This is a test comment about TSLA",
            author="commenter",
            score=25,
            created_utc=datetime.utcnow(),
            permalink="/r/stocks/comments/post123/comment123",
            extracted_symbols=["TSLA"],
            mentions_stocks=True
        )
        
        assert comment.id == "comment123"
        assert comment.mentions_stocks is True
        assert "TSLA" in comment.extracted_symbols

    def test_quality_score_calculation(self):
        """Test comment quality score calculation."""
        # High score, long comment
        high_quality = RedditComment(
            id="hq_comment",
            body="A" * 500,  # Long comment
            score=100,
            created_utc=datetime.utcnow(),
            permalink="/test",
            is_distinguished=True
        )
        
        # Low score, short comment
        low_quality = RedditComment(
            id="lq_comment",
            body="Short",
            score=1,
            created_utc=datetime.utcnow(),
            permalink="/test"
        )
        
        assert high_quality.quality_score > low_quality.quality_score
        assert 0 <= high_quality.quality_score <= 1
        assert 0 <= low_quality.quality_score <= 1

    def test_quality_score_distinguished_bonus(self):
        """Test quality score bonus for distinguished comments."""
        distinguished = RedditComment(
            id="dist_comment",
            body="Moderator comment",
            score=10,
            created_utc=datetime.utcnow(),
            permalink="/test",
            is_distinguished=True
        )
        
        regular = RedditComment(
            id="reg_comment",
            body="Regular comment",
            score=10,
            created_utc=datetime.utcnow(),
            permalink="/test",
            is_distinguished=False
        )
        
        assert distinguished.quality_score > regular.quality_score


class TestRedditPost:
    """Test cases for RedditPost schema."""

    def test_reddit_post_creation(self):
        """Test basic Reddit post creation."""
        post = RedditPost(
            id="post123",
            title="TSLA Analysis - Great Stock!",
            selftext="Detailed analysis of Tesla stock",
            author="analyst",
            subreddit="stocks",
            score=150,
            upvote_ratio=0.85,
            num_comments=42,
            created_utc=datetime.utcnow(),
            url="https://reddit.com/r/stocks/post123",
            permalink="/r/stocks/post123",
            extracted_symbols=["TSLA"],
            mentions_stocks=True
        )
        
        assert post.id == "post123"
        assert post.mentions_stocks is True
        assert "TSLA" in post.extracted_symbols

    def test_full_text_property(self):
        """Test full text property combining title and selftext."""
        post = RedditPost(
            id="post123",
            title="Great Title",
            selftext="Detailed content here",
            subreddit="test",
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test"
        )
        
        expected = "Great Title\n\nDetailed content here"
        assert post.full_text == expected

    def test_full_text_empty_selftext(self):
        """Test full text with empty selftext."""
        post = RedditPost(
            id="post123",
            title="Title Only",
            selftext="",
            subreddit="test",
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test"
        )
        
        assert post.full_text == "Title Only"

    def test_quality_score_calculation(self):
        """Test post quality score calculation."""
        high_quality = RedditPost(
            id="hq_post",
            title="High Quality Post with TSLA Analysis",
            selftext="A" * 1000,  # Long content
            subreddit="stocks",
            score=500,
            upvote_ratio=0.95,
            num_comments=100,
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test",
            is_original_content=True
        )
        
        low_quality = RedditPost(
            id="lq_post",
            title="Short",
            selftext="Brief",
            subreddit="test",
            score=5,
            upvote_ratio=0.55,
            num_comments=1,
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test",
            is_locked=True
        )
        
        assert high_quality.quality_score > low_quality.quality_score
        assert 0 <= high_quality.quality_score <= 1
        assert 0 <= low_quality.quality_score <= 1

    def test_is_finance_related_keywords(self):
        """Test finance relation detection by keywords."""
        finance_post = RedditPost(
            id="finance_post",
            title="Stock Market Analysis and Investment Strategy",
            selftext="Discussion about trading and portfolio management",
            subreddit="investing",
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test"
        )
        
        non_finance_post = RedditPost(
            id="other_post",
            title="Cute Cat Pictures",
            selftext="Just sharing some adorable cats",
            subreddit="cats",
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test"
        )
        
        assert finance_post.is_finance_related is True
        assert non_finance_post.is_finance_related is False

    def test_is_finance_related_flair(self):
        """Test finance relation detection by flair."""
        dd_post = RedditPost(
            id="dd_post",
            title="Random Title",
            selftext="No finance keywords here",
            subreddit="test",
            flair_text="DD",
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test"
        )
        
        assert dd_post.is_finance_related is True

    def test_is_finance_related_stock_mentions(self):
        """Test finance relation detection by stock mentions."""
        stock_post = RedditPost(
            id="stock_post",
            title="Random Discussion",
            selftext="No keywords",
            subreddit="test",
            extracted_symbols=["TSLA", "AAPL"],
            mentions_stocks=True,
            created_utc=datetime.utcnow(),
            url="https://test.com",
            permalink="/test"
        )
        
        assert stock_post.is_finance_related is True


class TestSubredditInfo:
    """Test cases for SubredditInfo schema."""

    def test_subreddit_info_creation(self):
        """Test basic subreddit info creation."""
        subreddit = SubredditInfo(
            name="stocks",
            display_name="r/stocks",
            description="Stock market discussion",
            subscribers=500000,
            active_users=5000,
            created_utc=datetime.utcnow() - timedelta(days=3650),
            finance_relevance_score=0.9
        )
        
        assert subreddit.name == "stocks"
        assert subreddit.subscribers == 500000
        assert subreddit.finance_relevance_score == 0.9

    def test_reputation_score_calculation(self):
        """Test subreddit reputation score calculation."""
        large_subreddit = SubredditInfo(
            name="stocks",
            display_name="r/stocks",
            subscribers=1000000,
            active_users=10000,
            created_utc=datetime.utcnow() - timedelta(days=3650),  # 10 years old
        )
        
        small_subreddit = SubredditInfo(
            name="smallstocks",
            display_name="r/smallstocks",
            subscribers=1000,
            active_users=10,
            created_utc=datetime.utcnow() - timedelta(days=30),  # New
        )
        
        assert large_subreddit.reputation_score > small_subreddit.reputation_score
        assert 0 <= large_subreddit.reputation_score <= 1
        assert 0 <= small_subreddit.reputation_score <= 1

    def test_reputation_score_quarantined_penalty(self):
        """Test reputation score penalty for quarantined subreddits."""
        quarantined = SubredditInfo(
            name="quarantined",
            display_name="r/quarantined",
            subscribers=100000,
            active_users=1000,
            created_utc=datetime.utcnow() - timedelta(days=1000),
            is_quarantined=True
        )
        
        normal = SubredditInfo(
            name="normal",
            display_name="r/normal",
            subscribers=100000,
            active_users=1000,
            created_utc=datetime.utcnow() - timedelta(days=1000),
            is_quarantined=False
        )
        
        assert quarantined.reputation_score < normal.reputation_score


class TestRedditSearchResult:
    """Test cases for RedditSearchResult schema."""

    def test_search_result_creation(self):
        """Test basic search result creation."""
        posts = [
            RedditPost(
                id="post1",
                title="Test Post 1",
                subreddit="test",
                created_utc=datetime.utcnow(),
                url="https://test.com/1",
                permalink="/test/1",
                mentions_stocks=True,
                extracted_symbols=["TSLA"]
            ),
            RedditPost(
                id="post2",
                title="Test Post 2",
                subreddit="test",
                created_utc=datetime.utcnow(),
                url="https://test.com/2",
                permalink="/test/2",
                mentions_stocks=False,
                extracted_symbols=[]
            )
        ]
        
        result = RedditSearchResult(
            posts=posts,
            collection_method="test_collection",
            query_parameters={"test": "value"}
        )
        
        assert len(result.posts) == 2
        assert result.total_posts == 2
        assert result.finance_related_posts == 1  # Only one post is finance-related

    def test_automatic_counts(self):
        """Test automatic calculation of counts."""
        posts = [
            RedditPost(
                id=f"post{i}",
                title=f"Post {i}",
                subreddit="test",
                created_utc=datetime.utcnow(),
                url=f"https://test.com/{i}",
                permalink=f"/test/{i}",
                mentions_stocks=i % 2 == 0,  # Every other post mentions stocks
                extracted_symbols=["TSLA"] if i % 2 == 0 else []
            )
            for i in range(5)
        ]
        
        comments = [
            RedditComment(
                id=f"comment{i}",
                body=f"Comment {i}",
                created_utc=datetime.utcnow(),
                permalink=f"/test/comment{i}"
            )
            for i in range(3)
        ]
        
        result = RedditSearchResult(
            posts=posts,
            comments=comments,
            collection_method="test"
        )
        
        assert result.total_posts == 5
        assert result.total_comments == 3
        assert result.finance_related_posts == 3  # Posts 0, 2, 4 mention stocks

    def test_quality_score_calculation(self):
        """Test search result quality score calculation."""
        high_quality_posts = [
            RedditPost(
                id="hq_post",
                title="High Quality Finance Post",
                selftext="Detailed analysis" * 100,
                subreddit="stocks",
                score=500,
                num_comments=100,
                created_utc=datetime.utcnow(),
                url="https://test.com",
                permalink="/test",
                mentions_stocks=True,
                extracted_symbols=["TSLA"]
            )
        ]
        
        low_quality_posts = [
            RedditPost(
                id="lq_post",
                title="Low Quality",
                selftext="Brief",
                subreddit="test",
                score=1,
                num_comments=0,
                created_utc=datetime.utcnow(),
                url="https://test.com",
                permalink="/test"
            )
        ]
        
        high_quality_result = RedditSearchResult(
            posts=high_quality_posts,
            collection_method="test"
        )
        
        low_quality_result = RedditSearchResult(
            posts=low_quality_posts,
            collection_method="test"
        )
        
        assert high_quality_result.quality_score > low_quality_result.quality_score

    def test_quality_score_empty_posts(self):
        """Test quality score with no posts."""
        result = RedditSearchResult(
            posts=[],
            collection_method="test"
        )
        
        assert result.quality_score == 0.0

    def test_engagement_bonus(self):
        """Test engagement bonus in quality score."""
        posts_with_comments = [
            RedditPost(
                id="post1",
                title="Post with Comments",
                subreddit="test",
                score=10,
                num_comments=50,  # High comment ratio
                created_utc=datetime.utcnow(),
                url="https://test.com",
                permalink="/test"
            )
        ]
        
        comments = [
            RedditComment(
                id=f"comment{i}",
                body=f"Comment {i}",
                created_utc=datetime.utcnow(),
                permalink=f"/test/comment{i}"
            )
            for i in range(50)
        ]
        
        result = RedditSearchResult(
            posts=posts_with_comments,
            comments=comments,
            collection_method="test"
        )
        
        # Should have higher quality due to engagement
        assert result.quality_score > 0.3  # Reasonable threshold