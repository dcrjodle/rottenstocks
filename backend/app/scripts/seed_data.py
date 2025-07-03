"""
Database seeding script for RottenStocks.

Creates sample data for development and testing including stocks, experts,
ratings, and social posts to demonstrate the platform functionality.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Stock, Expert, Rating, SocialPost,
    RatingType, RecommendationType, Platform, SentimentType
)
from app.db.session import AsyncSessionLocal


# Sample stock data
SAMPLE_STOCKS = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "description": "Technology company that designs, develops, and sells consumer electronics, computer software, and online services.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": Decimal("3000000000000"),  # 3T
        "current_price": Decimal("185.45"),
        "previous_close": Decimal("183.20"),
        "day_high": Decimal("186.78"),
        "day_low": Decimal("182.90"),
        "volume": 52340000,
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "description": "Multinational technology company that specializes in Internet-related services and products.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Internet Services",
        "market_cap": Decimal("2100000000000"),  # 2.1T
        "current_price": Decimal("142.33"),
        "previous_close": Decimal("140.15"),
        "day_high": Decimal("143.85"),
        "day_low": Decimal("139.77"),
        "volume": 28450000,
    },
    {
        "symbol": "TSLA",
        "name": "Tesla, Inc.",
        "description": "Electric vehicle and clean energy company that designs, manufactures, and sells electric cars, energy generation and storage systems.",
        "exchange": "NASDAQ",
        "sector": "Automotive",
        "industry": "Electric Vehicles",
        "market_cap": Decimal("800000000000"),  # 800B
        "current_price": Decimal("248.50"),
        "previous_close": Decimal("245.80"),
        "day_high": Decimal("252.30"),
        "day_low": Decimal("244.10"),
        "volume": 45230000,
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "description": "Technology company that develops, manufactures, licenses, supports, and sells computer software, consumer electronics, and personal computers.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Software",
        "market_cap": Decimal("2800000000000"),  # 2.8T
        "current_price": Decimal("378.85"),
        "previous_close": Decimal("375.20"),
        "day_high": Decimal("381.45"),
        "day_low": Decimal("373.90"),
        "volume": 31580000,
    },
    {
        "symbol": "AMZN",
        "name": "Amazon.com, Inc.",
        "description": "Multinational technology company focusing on e-commerce, cloud computing, digital streaming, and artificial intelligence.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "E-commerce",
        "market_cap": Decimal("1500000000000"),  # 1.5T
        "current_price": Decimal("145.12"),
        "previous_close": Decimal("143.88"),
        "day_high": Decimal("146.75"),
        "day_low": Decimal("142.33"),
        "volume": 38920000,
    },
]

# Sample expert data
SAMPLE_EXPERTS = [
    {
        "name": "Sarah Johnson",
        "title": "Senior Technology Analyst",
        "institution": "Goldman Sachs",
        "bio": "15+ years experience analyzing technology stocks with a focus on consumer electronics and software companies.",
        "email": "s.johnson@gs.com",
        "website": "https://www.goldmansachs.com/analysts/sarah-johnson",
        "linkedin_url": "https://linkedin.com/in/sarah-johnson-analyst",
        "years_experience": 15,
        "specializations": '["Technology", "Consumer Electronics", "Software"]',
        "certifications": "CFA, CPA",
        "total_ratings": 234,
        "accuracy_score": 0.87,
        "avg_rating_score": 3.8,
        "follower_count": 15400,
        "is_verified": True,
    },
    {
        "name": "Michael Chen",
        "title": "Portfolio Manager",
        "institution": "Morgan Stanley",
        "bio": "Automotive and clean energy sector specialist with deep expertise in EV market dynamics.",
        "email": "m.chen@ms.com",
        "website": "https://www.morganstanley.com/analysts/michael-chen",
        "linkedin_url": "https://linkedin.com/in/michael-chen-pm",
        "years_experience": 12,
        "specializations": '["Automotive", "Clean Energy", "Electric Vehicles"]',
        "certifications": "CFA, FRM",
        "total_ratings": 187,
        "accuracy_score": 0.82,
        "avg_rating_score": 3.6,
        "follower_count": 12800,
        "is_verified": True,
    },
    {
        "name": "Emily Rodriguez",
        "title": "Research Director",
        "institution": "JP Morgan",
        "bio": "Cloud computing and enterprise software expert with strong track record in growth stock analysis.",
        "email": "e.rodriguez@jpmorgan.com",
        "website": "https://www.jpmorgan.com/research/emily-rodriguez",
        "years_experience": 18,
        "specializations": '["Cloud Computing", "Enterprise Software", "SaaS"]',
        "certifications": "CFA, CAIA",
        "total_ratings": 312,
        "accuracy_score": 0.89,
        "avg_rating_score": 4.1,
        "follower_count": 18600,
        "is_verified": True,
    },
    {
        "name": "David Thompson",
        "title": "Independent Analyst",
        "institution": "Thompson Research",
        "bio": "Independent research analyst specializing in FAANG stocks and growth technology companies.",
        "website": "https://www.thompson-research.com",
        "twitter_handle": "DThompsonAnalyst",
        "years_experience": 8,
        "specializations": '["Technology", "Growth Stocks", "FAANG"]',
        "certifications": "CFA",
        "total_ratings": 89,
        "accuracy_score": 0.79,
        "avg_rating_score": 3.4,
        "follower_count": 7200,
        "is_verified": False,
    },
]


async def create_sample_stocks(session: AsyncSession) -> List[Stock]:
    """Create sample stocks in the database."""
    stocks = []
    
    for stock_data in SAMPLE_STOCKS:
        stock = Stock(**stock_data)
        session.add(stock)
        stocks.append(stock)
    
    await session.commit()
    print(f"✅ Created {len(stocks)} sample stocks")
    return stocks


async def create_sample_experts(session: AsyncSession) -> List[Expert]:
    """Create sample experts in the database."""
    experts = []
    
    for expert_data in SAMPLE_EXPERTS:
        expert = Expert(**expert_data)
        session.add(expert)
        experts.append(expert)
    
    await session.commit()
    print(f"✅ Created {len(experts)} sample experts")
    return experts


async def create_sample_ratings(
    session: AsyncSession, 
    stocks: List[Stock], 
    experts: List[Expert]
) -> List[Rating]:
    """Create sample ratings for stocks by experts."""
    ratings = []
    
    # Sample expert ratings
    expert_ratings_data = [
        # AAPL ratings
        {
            "stock": stocks[0],  # AAPL
            "expert": experts[0],  # Sarah Johnson
            "rating_type": RatingType.EXPERT,
            "score": Decimal("4.2"),
            "recommendation": RecommendationType.BUY,
            "confidence": Decimal("0.85"),
            "price_target": Decimal("195.00"),
            "summary": "Strong fundamentals and iPhone cycle recovery support bullish outlook",
            "analysis": "Apple continues to show resilient demand for its premium products with strong services growth offsetting hardware cyclicality.",
        },
        {
            "stock": stocks[1],  # GOOGL
            "expert": experts[2],  # Emily Rodriguez
            "rating_type": RatingType.EXPERT,
            "score": Decimal("4.5"),
            "recommendation": RecommendationType.STRONG_BUY,
            "confidence": Decimal("0.90"),
            "price_target": Decimal("160.00"),
            "summary": "AI leadership and cloud growth acceleration drive strong buy rating",
            "analysis": "Google's AI capabilities and accelerating cloud growth position it well for the next technology cycle.",
        },
        {
            "stock": stocks[2],  # TSLA
            "expert": experts[1],  # Michael Chen
            "rating_type": RatingType.EXPERT,
            "score": Decimal("3.8"),
            "recommendation": RecommendationType.BUY,
            "confidence": Decimal("0.75"),
            "price_target": Decimal("280.00"),
            "summary": "EV market leadership intact despite increased competition",
            "analysis": "Tesla maintains strong competitive moats in EV technology and manufacturing efficiency.",
        },
        {
            "stock": stocks[3],  # MSFT
            "expert": experts[2],  # Emily Rodriguez
            "rating_type": RatingType.EXPERT,
            "score": Decimal("4.3"),
            "recommendation": RecommendationType.BUY,
            "confidence": Decimal("0.88"),
            "price_target": Decimal("400.00"),
            "summary": "Azure growth and AI integration drive continued outperformance",
            "analysis": "Microsoft's cloud platform and AI integration across products create sustainable competitive advantages.",
        },
    ]
    
    # Sample popular ratings (aggregated sentiment)
    popular_ratings_data = [
        {
            "stock": stocks[0],  # AAPL
            "rating_type": RatingType.POPULAR,
            "score": Decimal("3.9"),
            "recommendation": RecommendationType.BUY,
            "confidence": Decimal("0.72"),
            "summary": "Mixed sentiment but overall positive on Apple's innovation pipeline",
            "sample_size": 1247,
            "sentiment_sources": "Reddit, Twitter, StockTwits",
        },
        {
            "stock": stocks[1],  # GOOGL
            "rating_type": RatingType.POPULAR,
            "score": Decimal("4.1"),
            "recommendation": RecommendationType.BUY,
            "confidence": Decimal("0.78"),
            "summary": "Strong retail investor confidence in Google's AI strategy",
            "sample_size": 892,
            "sentiment_sources": "Reddit, Twitter, Discord",
        },
        {
            "stock": stocks[2],  # TSLA
            "rating_type": RatingType.POPULAR,
            "score": Decimal("3.6"),
            "recommendation": RecommendationType.HOLD,
            "confidence": Decimal("0.65"),
            "summary": "Polarized sentiment with strong bulls and bears",
            "sample_size": 2156,
            "sentiment_sources": "Reddit, Twitter, StockTwits",
        },
    ]
    
    # Create expert ratings
    for rating_data in expert_ratings_data:
        rating = Rating(
            stock_id=rating_data["stock"].id,
            expert_id=rating_data["expert"].id,
            rating_type=rating_data["rating_type"],
            score=rating_data["score"],
            recommendation=rating_data["recommendation"],
            confidence=rating_data["confidence"],
            price_target=rating_data.get("price_target"),
            price_at_rating=rating_data["stock"].current_price,
            summary=rating_data["summary"],
            analysis=rating_data.get("analysis"),
            rating_date=datetime.utcnow() - timedelta(days=2),
        )
        session.add(rating)
        ratings.append(rating)
    
    # Create popular ratings
    for rating_data in popular_ratings_data:
        rating = Rating(
            stock_id=rating_data["stock"].id,
            expert_id=None,  # Popular ratings don't have experts
            rating_type=rating_data["rating_type"],
            score=rating_data["score"],
            recommendation=rating_data["recommendation"],
            confidence=rating_data["confidence"],
            price_at_rating=rating_data["stock"].current_price,
            summary=rating_data["summary"],
            sample_size=rating_data["sample_size"],
            sentiment_sources=rating_data["sentiment_sources"],
            rating_date=datetime.utcnow() - timedelta(hours=6),
        )
        session.add(rating)
        ratings.append(rating)
    
    await session.commit()
    print(f"✅ Created {len(ratings)} sample ratings")
    return ratings


async def create_sample_social_posts(
    session: AsyncSession, 
    stocks: List[Stock]
) -> List[SocialPost]:
    """Create sample social media posts for stocks."""
    posts = []
    
    # Sample social posts data
    posts_data = [
        {
            "stock": stocks[0],  # AAPL
            "platform": Platform.REDDIT,
            "platform_post_id": "reddit_aapl_001",
            "url": "https://reddit.com/r/stocks/comments/sample1",
            "author_username": "TechInvestor2023",
            "title": "Apple Q4 earnings thoughts - bullish on services growth",
            "content": "Just finished analyzing Apple's latest earnings. The services segment continues to impress with 16% YoY growth. iPhone sales were softer but within expectations. I'm still bullish long-term. $AAPL 🚀",
            "score": 47,
            "upvotes": 52,
            "downvotes": 5,
            "comment_count": 23,
            "sentiment_type": SentimentType.POSITIVE,
            "sentiment_score": Decimal("0.72"),
            "sentiment_confidence": Decimal("0.85"),
            "mentions_count": 3,
            "has_financial_data": True,
            "contains_prediction": True,
            "subreddit": "stocks",
            "posted_at": datetime.utcnow() - timedelta(hours=3),
        },
        {
            "stock": stocks[1],  # GOOGL
            "platform": Platform.TWITTER,
            "platform_post_id": "twitter_googl_001",
            "url": "https://twitter.com/user/status/sample2",
            "author_username": "AIAnalyst",
            "content": "Google's Bard showing impressive improvements. This AI race is heating up and $GOOGL is positioned well with their massive data moats. Cloud growth also accelerating. Very optimistic! #AI #CloudComputing",
            "score": 156,
            "comment_count": 12,
            "share_count": 28,
            "sentiment_type": SentimentType.VERY_POSITIVE,
            "sentiment_score": Decimal("0.88"),
            "sentiment_confidence": Decimal("0.92"),
            "mentions_count": 1,
            "has_financial_data": False,
            "contains_prediction": True,
            "hashtags": '["AI", "CloudComputing"]',
            "posted_at": datetime.utcnow() - timedelta(hours=5),
        },
        {
            "stock": stocks[2],  # TSLA
            "platform": Platform.REDDIT,
            "platform_post_id": "reddit_tsla_001",
            "url": "https://reddit.com/r/wallstreetbets/comments/sample3",
            "author_username": "ElonFanBoy",
            "title": "TSLA delivery numbers looking strong for Q4",
            "content": "Just saw some delivery tracker data and Tesla is crushing it this quarter. FSD is also getting better every week. Still think we're early in the EV adoption curve. $TSLA to the moon! 🌙",
            "score": 234,
            "upvotes": 267,
            "downvotes": 33,
            "comment_count": 89,
            "sentiment_type": SentimentType.VERY_POSITIVE,
            "sentiment_score": Decimal("0.91"),
            "sentiment_confidence": Decimal("0.87"),
            "mentions_count": 2,
            "has_financial_data": True,
            "contains_prediction": True,
            "subreddit": "wallstreetbets",
            "posted_at": datetime.utcnow() - timedelta(hours=8),
        },
        {
            "stock": stocks[2],  # TSLA (negative sentiment)
            "platform": Platform.TWITTER,
            "platform_post_id": "twitter_tsla_002",
            "author_username": "BearishOnEV",
            "content": "Tesla's valuation still makes no sense. Competition is catching up fast and margins are compressing. $TSLA looks overvalued at these levels. Taking profits. #Tesla #EV",
            "score": 89,
            "comment_count": 34,
            "share_count": 15,
            "sentiment_type": SentimentType.NEGATIVE,
            "sentiment_score": Decimal("0.28"),
            "sentiment_confidence": Decimal("0.81"),
            "mentions_count": 1,
            "has_financial_data": False,
            "contains_prediction": True,
            "hashtags": '["Tesla", "EV"]',
            "posted_at": datetime.utcnow() - timedelta(hours=12),
        },
    ]
    
    for post_data in posts_data:
        post = SocialPost(
            stock_id=post_data["stock"].id,
            platform=post_data["platform"],
            platform_post_id=post_data["platform_post_id"],
            url=post_data.get("url"),
            author_username=post_data["author_username"],
            title=post_data.get("title"),
            content=post_data["content"],
            score=post_data.get("score"),
            upvotes=post_data.get("upvotes"),
            downvotes=post_data.get("downvotes"),
            comment_count=post_data.get("comment_count"),
            share_count=post_data.get("share_count"),
            sentiment_type=post_data["sentiment_type"],
            sentiment_score=post_data["sentiment_score"],
            sentiment_confidence=post_data["sentiment_confidence"],
            mentions_count=post_data["mentions_count"],
            has_financial_data=post_data["has_financial_data"],
            contains_prediction=post_data["contains_prediction"],
            subreddit=post_data.get("subreddit"),
            hashtags=post_data.get("hashtags"),
            posted_at=post_data["posted_at"],
            collected_at=datetime.utcnow(),
            analyzed_at=datetime.utcnow(),
        )
        session.add(post)
        posts.append(post)
    
    await session.commit()
    print(f"✅ Created {len(posts)} sample social posts")
    return posts


async def seed_database():
    """Main function to seed the database with sample data."""
    print("🌱 Starting database seeding...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Create sample data in order (respecting foreign key constraints)
            stocks = await create_sample_stocks(session)
            experts = await create_sample_experts(session)
            ratings = await create_sample_ratings(session, stocks, experts)
            posts = await create_sample_social_posts(session, stocks)
            
            print(f"\n🎉 Database seeding completed successfully!")
            print(f"📊 Summary:")
            print(f"   - {len(stocks)} stocks")
            print(f"   - {len(experts)} experts")
            print(f"   - {len(ratings)} ratings")
            print(f"   - {len(posts)} social posts")
            
        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            await session.rollback()
            raise
        

if __name__ == "__main__":
    # Run the seeding function
    asyncio.run(seed_database())