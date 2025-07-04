#!/usr/bin/env python3
"""
Interactive Database Shell for RottenStocks

This script provides an interactive Python shell with database models
pre-loaded and helper functions for testing and exploring the database.

Usage:
    python interactive_db.py

Features:
    - All models imported and ready to use
    - Database session automatically created
    - Helper functions for common operations
    - Tab completion and syntax highlighting (if available)
"""

import sys
import os
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Optional

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add backend to path so we can import models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from sqlalchemy import select, func, desc, and_, or_, create_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import models directly
from app.db.models.stock import Stock
from app.db.models.expert import Expert
from app.db.models.rating import Rating, RatingType, RecommendationType
from app.db.models.social_post import SocialPost, Platform, SentimentType


class DatabaseShell:
    """Interactive database shell with helper methods."""
    
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
    
    # ==================== STOCK OPERATIONS ====================
    
    async def create_stock(self, symbol: str, name: str, exchange: str, **kwargs) -> Stock:
        """Create a new stock with the given parameters."""
        stock = Stock(
            symbol=symbol.upper(),
            name=name,
            exchange=exchange,
            **kwargs
        )
        self.session.add(stock)
        await self.session.flush()
        await self.session.refresh(stock)
        print(f"✅ Created stock: {stock}")
        return stock
    
    async def find_stock(self, symbol: str) -> Optional[Stock]:
        """Find a stock by symbol."""
        stock = await self.session.scalar(
            select(Stock).where(Stock.symbol == symbol.upper())
        )
        if stock:
            print(f"📈 Found: {stock}")
        else:
            print(f"❌ Stock {symbol} not found")
        return stock
    
    async def find_stocks_by_sector(self, sector: str) -> List[Stock]:
        """Find all stocks in a specific sector."""
        result = await self.session.execute(
            select(Stock).where(Stock.sector.ilike(f"%{sector}%"))
        )
        stocks = result.scalars().all()
        print(f"📊 Found {len(stocks)} stocks in {sector} sector:")
        for stock in stocks:
            print(f"  • {stock.symbol}: {stock.name}")
        return stocks
    
    async def update_stock_price(self, symbol: str, new_price: Decimal) -> bool:
        """Update stock price and calculate price change."""
        stock = await self.find_stock(symbol)
        if not stock:
            return False
            
        old_price = stock.current_price
        stock.previous_close = old_price
        stock.current_price = new_price
        
        await self.session.commit()
        print(f"💰 Updated {symbol}: ${old_price} → ${new_price} ({stock.price_change_percent:+.2f}%)")
        return True
    
    # ==================== EXPERT OPERATIONS ====================
    
    async def create_expert(self, name: str, institution: str, **kwargs) -> Expert:
        """Create a new expert analyst."""
        expert = Expert(
            name=name,
            institution=institution,
            **kwargs
        )
        self.session.add(expert)
        await self.session.flush()
        await self.session.refresh(expert)
        print(f"✅ Created expert: {expert}")
        return expert
    
    async def verify_expert(self, expert_id: str) -> bool:
        """Verify an expert and update their status."""
        expert = await self.session.get(Expert, expert_id)
        if not expert:
            print(f"❌ Expert {expert_id} not found")
            return False
            
        expert.verify_expert()
        await self.session.commit()
        print(f"✅ Verified expert: {expert.name}")
        return True
    
    async def get_expert_ratings(self, expert_id: str) -> List[Rating]:
        """Get all ratings by a specific expert."""
        result = await self.session.execute(
            select(Rating)
            .where(Rating.expert_id == expert_id)
            .options(selectinload(Rating.stock))
            .order_by(desc(Rating.rating_date))
        )
        ratings = result.scalars().all()
        print(f"⭐ Expert has {len(ratings)} ratings:")
        for rating in ratings:
            print(f"  • {rating.stock.symbol}: {rating.score}/5.0 ({rating.recommendation.value})")
        return ratings
    
    # ==================== RATING OPERATIONS ====================
    
    async def create_rating(self, stock_symbol: str, expert_name: str, 
                          score: float, recommendation: str, **kwargs) -> Rating:
        """Create a new rating for a stock by an expert."""
        # Find stock
        stock = await self.find_stock(stock_symbol)
        if not stock:
            raise ValueError(f"Stock {stock_symbol} not found")
        
        # Find expert
        expert = await self.session.scalar(
            select(Expert).where(Expert.name.ilike(f"%{expert_name}%"))
        )
        if not expert:
            raise ValueError(f"Expert {expert_name} not found")
        
        # Create rating
        rating = Rating(
            stock_id=stock.id,
            expert_id=expert.id,
            rating_type=RatingType.EXPERT,
            score=Decimal(str(score)),
            recommendation=RecommendationType(recommendation.lower().replace(' ', '_')),
            rating_date=datetime.utcnow(),
            **kwargs
        )
        self.session.add(rating)
        await self.session.flush()
        await self.session.refresh(rating)
        print(f"✅ Created rating: {rating}")
        return rating
    
    async def get_recent_ratings(self, days: int = 30) -> List[Rating]:
        """Get ratings from the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(Rating)
            .where(Rating.rating_date >= cutoff_date)
            .options(selectinload(Rating.stock), selectinload(Rating.expert))
            .order_by(desc(Rating.rating_date))
        )
        ratings = result.scalars().all()
        print(f"📅 Found {len(ratings)} ratings in the last {days} days:")
        for rating in ratings:
            print(f"  • {rating.stock.symbol} by {rating.expert.name}: {rating.score}/5.0")
        return ratings
    
    async def get_ratings_by_score(self, min_score: float = 4.0) -> List[Rating]:
        """Get ratings above a certain score threshold."""
        result = await self.session.execute(
            select(Rating)
            .where(Rating.score >= Decimal(str(min_score)))
            .options(selectinload(Rating.stock), selectinload(Rating.expert))
            .order_by(desc(Rating.score))
        )
        ratings = result.scalars().all()
        print(f"🌟 Found {len(ratings)} ratings with score >= {min_score}:")
        for rating in ratings:
            print(f"  • {rating.stock.symbol}: {rating.score}/5.0 ({rating.recommendation.value})")
        return ratings
    
    # ==================== SOCIAL MEDIA OPERATIONS ====================
    
    async def create_social_post(self, stock_symbol: str, platform: str, 
                               content: str, **kwargs) -> SocialPost:
        """Create a new social media post."""
        # Find stock
        stock = await self.find_stock(stock_symbol)
        if not stock:
            raise ValueError(f"Stock {stock_symbol} not found")
        
        post = SocialPost(
            stock_id=stock.id,
            platform=Platform(platform.lower()),
            platform_post_id=f"test_{datetime.utcnow().timestamp()}",
            content=content,
            posted_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            **kwargs
        )
        self.session.add(post)
        await self.session.flush()
        await self.session.refresh(post)
        print(f"✅ Created social post: {post}")
        return post
    
    async def analyze_sentiment(self, post_id: str) -> bool:
        """Analyze sentiment for a social post (mock analysis)."""
        post = await self.session.get(SocialPost, post_id)
        if not post:
            print(f"❌ Post {post_id} not found")
            return False
        
        # Mock sentiment analysis based on content keywords
        content_lower = post.content.lower()
        if any(word in content_lower for word in ['great', 'excellent', 'bullish', 'buy', 'strong']):
            sentiment_score = Decimal('0.8')
        elif any(word in content_lower for word in ['bad', 'terrible', 'bearish', 'sell', 'weak']):
            sentiment_score = Decimal('0.2')
        else:
            sentiment_score = Decimal('0.5')
        
        post.update_sentiment(sentiment_score, Decimal('0.75'))
        await self.session.commit()
        print(f"🤖 Analyzed sentiment: {post.sentiment_type.value} ({sentiment_score})")
        return True
    
    async def get_posts_by_sentiment(self, sentiment_type: str) -> List[SocialPost]:
        """Get posts by sentiment type."""
        sentiment = SentimentType(sentiment_type.lower().replace(' ', '_'))
        result = await self.session.execute(
            select(SocialPost)
            .where(SocialPost.sentiment_type == sentiment)
            .options(selectinload(SocialPost.stock))
            .order_by(desc(SocialPost.posted_at))
        )
        posts = result.scalars().all()
        print(f"💬 Found {len(posts)} {sentiment_type} posts:")
        for post in posts:
            print(f"  • {post.stock.symbol} on {post.platform.value}: {post.content[:50]}...")
        return posts
    
    # ==================== UTILITY FUNCTIONS ====================
    
    async def get_database_stats(self):
        """Get overview statistics of the database."""
        stats = {}
        for model, name in [(Stock, 'stocks'), (Expert, 'experts'), 
                           (Rating, 'ratings'), (SocialPost, 'social_posts')]:
            count = await self.session.scalar(select(func.count(model.id)))
            stats[name] = count
        
        print("📊 Database Statistics:")
        for table, count in stats.items():
            print(f"  • {table.title()}: {count}")
        
        return stats
    
    async def reset_database(self, confirm: str = None):
        """Reset the database (DELETE ALL DATA)."""
        if confirm != "YES_DELETE_ALL_DATA":
            print("⚠️  WARNING: This will delete ALL data!")
            print("To confirm, call: reset_database('YES_DELETE_ALL_DATA')")
            return False
        
        # Delete in reverse dependency order
        await self.session.execute("DELETE FROM social_posts")
        await self.session.execute("DELETE FROM ratings")
        await self.session.execute("DELETE FROM experts")
        await self.session.execute("DELETE FROM stocks")
        await self.session.commit()
        
        print("🗑️  Database reset complete - all data deleted!")
        return True
    
    async def seed_sample_data(self):
        """Create some sample data for testing."""
        print("🌱 Seeding sample data...")
        
        # Create sample stocks
        stocks = [
            await self.create_stock("AAPL", "Apple Inc.", "NASDAQ", 
                                  current_price=Decimal("150.00"), sector="Technology"),
            await self.create_stock("GOOGL", "Alphabet Inc.", "NASDAQ", 
                                  current_price=Decimal("2500.00"), sector="Technology"),
            await self.create_stock("TSLA", "Tesla Inc.", "NASDAQ", 
                                  current_price=Decimal("800.00"), sector="Automotive"),
        ]
        
        # Create sample experts
        experts = [
            await self.create_expert("John Smith", "Goldman Sachs", 
                                   specializations="Technology", is_verified=True),
            await self.create_expert("Jane Doe", "Morgan Stanley", 
                                   specializations="Automotive, Clean Energy", is_verified=True),
        ]
        
        # Create sample ratings
        await self.create_rating("AAPL", "John Smith", 4.5, "buy",
                               confidence=Decimal("0.9"), price_target=Decimal("180.00"))
        await self.create_rating("TSLA", "Jane Doe", 4.0, "strong_buy",
                               confidence=Decimal("0.85"), price_target=Decimal("1000.00"))
        
        # Create sample social posts
        await self.create_social_post("AAPL", "reddit", 
                                    "Apple's latest iPhone sales are incredible! Bullish on AAPL 🚀")
        await self.create_social_post("TSLA", "twitter", 
                                    "Tesla's FSD is getting better every day. Long term hold!")
        
        await self.session.commit()
        print("✅ Sample data created successfully!")
    
    # Helper methods for sync wrappers
    async def _get_stocks_sync(self):
        """Helper to get all stocks"""
        result = await self.session.execute(select(Stock))
        return result.scalars().all()
    
    async def _get_experts_sync(self):
        """Helper to get all experts"""
        result = await self.session.execute(select(Expert))
        return result.scalars().all()
    
    async def _get_ratings_sync(self):
        """Helper to get all ratings"""
        result = await self.session.execute(select(Rating))
        return result.scalars().all()
    
    async def _get_posts_sync(self):
        """Helper to get all social posts"""
        result = await self.session.execute(select(SocialPost))
        return result.scalars().all()
    
    async def _execute_query_sync(self, sql_text):
        """Helper to execute raw SQL"""
        from sqlalchemy import text
        result = await self.session.execute(text(sql_text))
        return result.fetchall()


async def interactive_session():
    """Start an interactive database session."""
    print("🚀 Starting RottenStocks Database Interactive Shell")
    print("=" * 50)
    
    async with DatabaseShell() as db:
        # Show current database stats
        await db.get_database_stats()
        print()
        
        # Pre-fetch data once to avoid async issues in interactive console
        _stocks_cache = await db._get_stocks_sync()
        _experts_cache = await db._get_experts_sync()
        _ratings_cache = await db._get_ratings_sync()
        _posts_cache = await db._get_posts_sync()
        
        def get_stocks():
            """Get all stocks from database (cached)"""
            return _stocks_cache
        
        def get_experts():
            """Get all experts from database (cached)"""
            return _experts_cache
        
        def get_ratings():
            """Get all ratings from database (cached)"""
            return _ratings_cache
        
        def get_posts():
            """Get all social posts from database (cached)"""
            return _posts_cache
        
        def refresh_data():
            """Refresh cached data - use this after making changes"""
            print("Note: To refresh data, restart the interactive shell")
            print("      (The console is read-only to avoid async issues)")
        
        def query(sql_text):
            """Execute raw SQL query (limited functionality in interactive mode)"""
            print(f"SQL Query: {sql_text}")
            print("Note: Use query_builder.py for executing SQL queries")
            print("      Interactive mode focuses on data exploration")
        
        # Make common objects available in global scope
        globals().update({
            'db': db,
            'session': db.session,
            'get_stocks': get_stocks,
            'get_experts': get_experts,
            'get_ratings': get_ratings,
            'get_posts': get_posts,
            'refresh_data': refresh_data,
            'query': query,
            'Stock': Stock,
            'Expert': Expert,
            'Rating': Rating,
            'SocialPost': SocialPost,
            'RatingType': RatingType,
            'RecommendationType': RecommendationType,
            'Platform': Platform,
            'SentimentType': SentimentType,
            'select': select,
            'func': func,
            'desc': desc,
            'and_': and_,
            'or_': or_,
            'Decimal': Decimal,
            'datetime': datetime,
            'timedelta': timedelta,
        })
        
        print("📋 Available objects and functions:")
        print("  • db - Database shell with helper methods")
        print("  • session - SQLAlchemy async session")
        print("  • get_stocks(), get_experts(), get_ratings(), get_posts() - Data access (cached)")
        print("  • refresh_data() - Info about refreshing cached data")
        print("  • Stock, Expert, Rating, SocialPost - Model classes")
        print("  • RatingType, RecommendationType, Platform, SentimentType - Enums")
        print("  • select, func, desc, and_, or_ - SQLAlchemy query functions")
        print("  • Decimal, datetime, timedelta - Utility classes")
        print()
        print("🔧 Quick data exploration (data is pre-loaded):")
        print("  • stocks = get_stocks()")
        print("  • experts = get_experts()")
        print("  • ratings = get_ratings()")
        print("  • posts = get_posts()")
        print()
        print("💡 Example usage:")
        print("  • for stock in get_stocks(): print(stock.symbol, stock.current_price)")
        print("  • apple = [s for s in get_stocks() if s.symbol == 'AAPL'][0]")
        print("  • high_ratings = [r for r in get_ratings() if r.score >= 4.0]")
        print()
        print("ℹ️  Note: Data is cached for performance. Restart shell to see latest changes.")
        print()
        print("Type 'exit()' or Ctrl+C to quit")
        print("=" * 50)
        
        # Try to start IPython if available, fall back to regular Python
        try:
            from IPython import embed
            embed()
        except ImportError:
            import code
            code.interact(local=globals())


if __name__ == "__main__":
    # Run the interactive session
    asyncio.run(interactive_session())