#!/usr/bin/env python3
"""
Sample Data Generator for RottenStocks Database

This script generates realistic sample data for testing and development.
It creates stocks, experts, ratings, and social posts with realistic
relationships and data distributions.

Usage:
    python generate_samples.py [options]
    
Examples:
    # Generate default sample set
    python generate_samples.py
    
    # Generate specific amounts
    python generate_samples.py --stocks 20 --experts 10 --posts-per-stock 50
    
    # Generate only social media data
    python generate_samples.py --social-only --posts 200
    
    # Clear existing data first
    python generate_samples.py --clear-first --stocks 10
"""

import sys
import os
import asyncio
import argparse
import random
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import models directly
from app.db.models.stock import Stock
from app.db.models.expert import Expert
from app.db.models.rating import Rating, RatingType, RecommendationType
from app.db.models.social_post import SocialPost, Platform, SentimentType


class SampleDataGenerator:
    """Generates realistic sample data for the RottenStocks database."""
    
    # Sample data sets
    STOCK_DATA = [
        ("AAPL", "Apple Inc.", "NASDAQ", "Technology", 150.00),
        ("GOOGL", "Alphabet Inc.", "NASDAQ", "Technology", 2500.00),
        ("MSFT", "Microsoft Corporation", "NASDAQ", "Technology", 300.00),
        ("TSLA", "Tesla, Inc.", "NASDAQ", "Automotive", 800.00),
        ("AMZN", "Amazon.com Inc.", "NASDAQ", "E-commerce", 3200.00),
        ("NVDA", "NVIDIA Corporation", "NASDAQ", "Technology", 400.00),
        ("META", "Meta Platforms Inc.", "NASDAQ", "Technology", 250.00),
        ("NFLX", "Netflix Inc.", "NASDAQ", "Entertainment", 380.00),
        ("JPM", "JPMorgan Chase & Co.", "NYSE", "Banking", 140.00),
        ("JNJ", "Johnson & Johnson", "NYSE", "Healthcare", 160.00),
        ("PG", "Procter & Gamble Co.", "NYSE", "Consumer Goods", 145.00),
        ("KO", "The Coca-Cola Company", "NYSE", "Beverages", 58.00),
        ("DIS", "The Walt Disney Company", "NYSE", "Entertainment", 95.00),
        ("WMT", "Walmart Inc.", "NYSE", "Retail", 145.00),
        ("V", "Visa Inc.", "NYSE", "Financial Services", 220.00),
        ("MA", "Mastercard Incorporated", "NYSE", "Financial Services", 350.00),
        ("HD", "The Home Depot Inc.", "NYSE", "Retail", 310.00),
        ("BAC", "Bank of America Corporation", "NYSE", "Banking", 32.00),
        ("XOM", "Exxon Mobil Corporation", "NYSE", "Energy", 105.00),
        ("CVX", "Chevron Corporation", "NYSE", "Energy", 160.00),
    ]
    
    EXPERT_DATA = [
        ("John Smith", "Goldman Sachs", "Technology, Growth Stocks", 15),
        ("Sarah Johnson", "Morgan Stanley", "Healthcare, Biotechnology", 12),
        ("Michael Chen", "JP Morgan", "Banking, Financial Services", 18),
        ("Emily Rodriguez", "Deutsche Bank", "Energy, Commodities", 10),
        ("David Kim", "Barclays", "Consumer Goods, Retail", 14),
        ("Lisa Zhang", "Credit Suisse", "Technology, AI", 8),
        ("Robert Wilson", "UBS", "Automotive, Manufacturing", 20),
        ("Maria Garcia", "Citigroup", "Entertainment, Media", 11),
        ("James Lee", "Bank of America", "REITs, Real Estate", 16),
        ("Anna Petrov", "Wells Fargo", "Pharmaceuticals, Healthcare", 13),
        ("Carlos Santos", "HSBC", "Emerging Markets, International", 9),
        ("Rachel Green", "Nomura", "ESG, Sustainable Investing", 7),
        ("Thomas Brown", "RBC Capital", "Mining, Materials", 22),
        ("Sofia Nakamura", "Mizuho", "Technology, Innovation", 6),
        ("Alexander Kumar", "Standard Chartered", "Fintech, Digital Banking", 5),
    ]
    
    SOCIAL_CONTENT_TEMPLATES = {
        "positive": [
            "{symbol} just reported amazing earnings! 🚀 This stock is going to the moon!",
            "Bullish on {symbol}! The fundamentals are incredibly strong right now.",
            "{symbol} is my top pick for 2025. Great management team and solid growth.",
            "Just bought more {symbol}. This dip is a gift for long-term investors!",
            "{symbol} has incredible potential. The market is undervaluing this gem.",
            "Love what {symbol} is doing in the {sector} space. Huge upside potential!",
            "{symbol} earnings beat expectations by a mile. Time to load up! 💎",
            "The future is bright for {symbol}. Revolutionary products coming soon.",
        ],
        "negative": [
            "{symbol} is overvalued at these levels. Time to take profits.",
            "Bearish on {symbol}. Too many red flags in their latest report.",
            "{symbol} has lost its competitive edge. Better opportunities elsewhere.",
            "Selling my {symbol} position. The growth story is over.",
            "{symbol} faces too much competition. Market share declining rapidly.",
            "Disappointed in {symbol}'s latest guidance. Lowering expectations.",
            "{symbol} is a value trap. Avoid at all costs right now.",
            "Technical analysis shows {symbol} is heading lower. Sell signal confirmed.",
        ],
        "neutral": [
            "{symbol} is fairly valued at current levels. Hold for dividends.",
            "Mixed feelings about {symbol}. Good company but expensive valuation.",
            "{symbol} is range-bound. Waiting for a clear breakout signal.",
            "Holding {symbol} for the long term. Not adding at these prices.",
            "{symbol} has both opportunities and risks. Proceed with caution.",
            "Watching {symbol} closely. Need to see more data before deciding.",
            "{symbol} is a solid company but no urgent rush to buy now.",
            "Neutral on {symbol}. Other sectors look more attractive currently.",
        ]
    }
    
    def __init__(self):
        self.session = None
        self.engine = None
        self.database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/rottenstocks')
        
    async def __aenter__(self):
        # Create async engine and session
        self.engine = create_async_engine(self.database_url, echo=False)
        AsyncSessionLocal = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.session = AsyncSessionLocal()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.engine:
            await self.engine.dispose()
    
    async def clear_database(self):
        """Clear all existing data."""
        print("🗑️  Clearing existing data...")
        await self.session.execute(text("DELETE FROM social_posts"))
        await self.session.execute(text("DELETE FROM ratings"))
        await self.session.execute(text("DELETE FROM experts"))
        await self.session.execute(text("DELETE FROM stocks"))
        await self.session.commit()
        print("✅ Database cleared")
    
    async def generate_stocks(self, count: int) -> List[Stock]:
        """Generate sample stocks."""
        print(f"📈 Generating {count} stocks...")
        
        stocks = []
        sample_data = random.sample(self.STOCK_DATA, min(count, len(self.STOCK_DATA)))
        
        for symbol, name, exchange, sector, base_price in sample_data:
            # Add some price variation
            current_price = Decimal(str(base_price * random.uniform(0.8, 1.2)))
            previous_close = current_price * Decimal(str(random.uniform(0.95, 1.05)))
            
            stock = Stock(
                symbol=symbol,
                name=name,
                exchange=exchange,
                sector=sector,
                current_price=current_price,
                previous_close=previous_close,
                market_cap=current_price * Decimal(str(random.randint(1000000, 10000000000))),
                shares_outstanding=random.randint(100000000, 5000000000),
                avg_volume=random.randint(1000000, 100000000),
                pe_ratio=Decimal(str(random.uniform(10.0, 50.0))) if random.random() > 0.2 else None,
                dividend_yield=Decimal(str(random.uniform(0.0, 5.0))) if random.random() > 0.3 else None,
            )
            stocks.append(stock)
            self.session.add(stock)
        
        await self.session.flush()
        print(f"✅ Created {len(stocks)} stocks")
        return stocks
    
    async def generate_experts(self, count: int) -> List[Expert]:
        """Generate sample experts."""
        print(f"👨‍💼 Generating {count} experts...")
        
        experts = []
        sample_data = random.sample(self.EXPERT_DATA, min(count, len(self.EXPERT_DATA)))
        
        for name, institution, specializations, years_exp in sample_data:
            expert = Expert(
                name=name,
                institution=institution,
                specializations=specializations,
                years_experience=years_exp,
                is_verified=random.choice([True, True, True, False]),  # 75% verified
                is_active=True,
                total_ratings=random.randint(10, 200),
                avg_accuracy=Decimal(str(random.uniform(0.6, 0.9))),
                bio=f"Senior analyst at {institution} with {years_exp} years of experience specializing in {specializations}.",
                email=f"{name.lower().replace(' ', '.')}@{institution.lower().replace(' ', '').replace(',', '')}example.com",
            )
            experts.append(expert)
            self.session.add(expert)
        
        await self.session.flush()
        print(f"✅ Created {len(experts)} experts")
        return experts
    
    async def generate_ratings(self, stocks: List[Stock], experts: List[Expert], 
                             ratings_per_stock: int = 3) -> List[Rating]:
        """Generate sample ratings."""
        total_ratings = len(stocks) * ratings_per_stock
        print(f"⭐ Generating {total_ratings} ratings...")
        
        ratings = []
        recommendations = list(RecommendationType)
        
        for stock in stocks:
            # Generate both expert and popular ratings
            selected_experts = random.sample(experts, min(ratings_per_stock - 1, len(experts)))
            
            # Expert ratings
            for expert in selected_experts:
                # Bias ratings based on market conditions
                if stock.sector in ["Technology", "Healthcare"]:
                    score_bias = 0.5  # Tech and healthcare tend to get higher ratings
                else:
                    score_bias = 0.0
                    
                score = max(1.0, min(5.0, random.normalvariate(3.5 + score_bias, 1.0)))
                
                # Choose recommendation based on score
                if score >= 4.5:
                    recommendation = RecommendationType.STRONG_BUY
                elif score >= 3.5:
                    recommendation = RecommendationType.BUY
                elif score >= 2.5:
                    recommendation = RecommendationType.HOLD
                elif score >= 1.5:
                    recommendation = RecommendationType.SELL
                else:
                    recommendation = RecommendationType.STRONG_SELL
                
                rating = Rating(
                    stock_id=stock.id,
                    expert_id=expert.id,
                    rating_type=RatingType.EXPERT,
                    score=Decimal(str(round(score, 2))),
                    recommendation=recommendation,
                    confidence=Decimal(str(random.uniform(0.6, 0.95))),
                    price_target=stock.current_price * Decimal(str(random.uniform(0.8, 1.4))),
                    price_at_rating=stock.current_price,
                    summary=f"{recommendation.value.replace('_', ' ').title()} recommendation based on {stock.sector} sector analysis",
                    rating_date=datetime.now() - timedelta(days=random.randint(0, 90)),
                )
                ratings.append(rating)
                self.session.add(rating)
            
            # Popular rating (aggregated sentiment)
            popular_score = random.uniform(2.0, 4.5)
            popular_rating = Rating(
                stock_id=stock.id,
                expert_id=None,
                rating_type=RatingType.POPULAR,
                score=Decimal(str(round(popular_score, 2))),
                recommendation=RecommendationType.HOLD if popular_score < 3.5 else RecommendationType.BUY,
                confidence=Decimal(str(random.uniform(0.5, 0.8))),
                sample_size=random.randint(50, 500),
                sentiment_sources="Reddit, Twitter, StockTwits",
                rating_date=datetime.now() - timedelta(days=random.randint(0, 7)),
            )
            ratings.append(popular_rating)
            self.session.add(popular_rating)
        
        await self.session.flush()
        print(f"✅ Created {len(ratings)} ratings")
        return ratings
    
    async def generate_social_posts(self, stocks: List[Stock], 
                                  posts_per_stock: int = 10) -> List[SocialPost]:
        """Generate sample social media posts."""
        total_posts = len(stocks) * posts_per_stock
        print(f"💬 Generating {total_posts} social posts...")
        
        posts = []
        platforms = list(Platform)
        sentiment_types = ["positive", "negative", "neutral"]
        
        for stock in stocks:
            for i in range(posts_per_stock):
                # Choose random sentiment with bias toward positive/neutral
                sentiment_type = random.choices(
                    sentiment_types, 
                    weights=[0.4, 0.2, 0.4]  # 40% positive, 20% negative, 40% neutral
                )[0]
                
                # Generate content based on sentiment
                content_template = random.choice(self.SOCIAL_CONTENT_TEMPLATES[sentiment_type])
                content = content_template.format(
                    symbol=stock.symbol,
                    sector=stock.sector
                )
                
                # Choose platform
                platform = random.choice(platforms)
                
                post = SocialPost(
                    stock_id=stock.id,
                    platform=platform,
                    platform_post_id=f"{platform.value}_{stock.symbol}_{i}_{random.randint(1000, 9999)}",
                    content=content,
                    author_username=f"investor_{random.randint(1000, 9999)}",
                    author_follower_count=random.randint(100, 50000),
                    score=random.randint(-10, 200),
                    upvotes=random.randint(0, 300) if platform == Platform.REDDIT else None,
                    downvotes=random.randint(0, 50) if platform == Platform.REDDIT else None,
                    comment_count=random.randint(0, 100),
                    share_count=random.randint(0, 50) if platform != Platform.REDDIT else None,
                    subreddit=random.choice(["wallstreetbets", "investing", "stocks", "SecurityAnalysis"]) if platform == Platform.REDDIT else None,
                    hashtags='["investing", "stocks", "finance"]' if platform == Platform.TWITTER else None,
                    posted_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                    collected_at=datetime.now() - timedelta(hours=random.randint(0, 24)),
                )
                
                # Add sentiment analysis
                if sentiment_type == "positive":
                    sentiment_score = Decimal(str(random.uniform(0.6, 0.95)))
                elif sentiment_type == "negative":
                    sentiment_score = Decimal(str(random.uniform(0.05, 0.4)))
                else:
                    sentiment_score = Decimal(str(random.uniform(0.4, 0.6)))
                
                post.update_sentiment(
                    sentiment_score=sentiment_score,
                    confidence=Decimal(str(random.uniform(0.6, 0.9)))
                )
                
                posts.append(post)
                self.session.add(post)
        
        await self.session.flush()
        print(f"✅ Created {len(posts)} social posts")
        return posts
    
    async def generate_all(self, stocks_count: int = 10, experts_count: int = 5, 
                          posts_per_stock: int = 20, ratings_per_stock: int = 3):
        """Generate a complete sample dataset."""
        print(f"🌱 Generating complete sample dataset...")
        print(f"   Stocks: {stocks_count}")
        print(f"   Experts: {experts_count}")
        print(f"   Ratings per stock: {ratings_per_stock}")
        print(f"   Posts per stock: {posts_per_stock}")
        print()
        
        stocks = await self.generate_stocks(stocks_count)
        experts = await self.generate_experts(experts_count)
        ratings = await self.generate_ratings(stocks, experts, ratings_per_stock)
        posts = await self.generate_social_posts(stocks, posts_per_stock)
        
        await self.session.commit()
        
        print()
        print("🎉 Sample data generation complete!")
        print(f"   📈 {len(stocks)} stocks created")
        print(f"   👨‍💼 {len(experts)} experts created") 
        print(f"   ⭐ {len(ratings)} ratings created")
        print(f"   💬 {len(posts)} social posts created")


async def main():
    parser = argparse.ArgumentParser(description="Generate sample data for RottenStocks database")
    parser.add_argument("--stocks", type=int, default=10, help="Number of stocks to generate")
    parser.add_argument("--experts", type=int, default=5, help="Number of experts to generate")
    parser.add_argument("--posts-per-stock", type=int, default=20, help="Number of social posts per stock")
    parser.add_argument("--ratings-per-stock", type=int, default=3, help="Number of ratings per stock")
    parser.add_argument("--clear-first", action="store_true", help="Clear existing data first")
    parser.add_argument("--social-only", action="store_true", help="Generate only social media posts")
    parser.add_argument("--posts", type=int, help="Total number of posts (for --social-only)")
    
    args = parser.parse_args()
    
    async with SampleDataGenerator() as generator:
        if args.clear_first:
            await generator.clear_database()
        
        if args.social_only:
            # Get existing stocks for social posts
            from sqlalchemy import select
            result = await generator.session.execute(select(Stock))
            stocks = list(result.scalars().all())
            
            if not stocks:
                print("❌ No stocks found. Create stocks first or run without --social-only")
                return
            
            posts_per_stock = (args.posts or 100) // len(stocks)
            await generator.generate_social_posts(stocks, posts_per_stock)
            await generator.session.commit()
        else:
            await generator.generate_all(
                stocks_count=args.stocks,
                experts_count=args.experts,
                posts_per_stock=args.posts_per_stock,
                ratings_per_stock=args.ratings_per_stock
            )


if __name__ == "__main__":
    asyncio.run(main())