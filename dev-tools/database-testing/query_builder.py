#!/usr/bin/env python3
"""
Database Query Builder for RottenStocks

This script provides pre-built queries and tools for analyzing
database data with options to export results.

Usage:
    python query_builder.py [options]
    
Examples:
    # List available query templates
    python query_builder.py --list-templates
    
    # Run a pre-built query
    python query_builder.py --template top_rated_stocks
    
    # Run custom SQL
    python query_builder.py --sql "SELECT symbol, current_price FROM stocks"
    
    # Export results to CSV
    python query_builder.py --template stock_performance --export results.csv
"""

import sys
import os
import asyncio
import argparse
import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from sqlalchemy import select, func, desc, asc, and_, or_, text, create_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import models directly
from app.db.models.stock import Stock
from app.db.models.expert import Expert
from app.db.models.rating import Rating, RatingType, RecommendationType
from app.db.models.social_post import SocialPost, Platform, SentimentType


class QueryBuilder:
    """Provides pre-built queries and analysis tools for the database."""
    
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
    
    # ==================== QUERY TEMPLATES ====================
    
    async def top_rated_stocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get stocks with highest average expert ratings."""
        query = (
            select(
                Stock.symbol,
                Stock.name,
                Stock.current_price,
                func.avg(Rating.score).label('avg_rating'),
                func.count(Rating.id).label('rating_count')
            )
            .join(Rating, Stock.id == Rating.stock_id)
            .where(Rating.rating_type == RatingType.EXPERT)
            .group_by(Stock.id, Stock.symbol, Stock.name, Stock.current_price)
            .having(func.count(Rating.id) >= 2)  # At least 2 ratings
            .order_by(desc('avg_rating'))
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return [
            {
                'symbol': row.symbol,
                'name': row.name,
                'price': float(row.current_price),
                'avg_rating': float(row.avg_rating),
                'rating_count': row.rating_count
            }
            for row in result
        ]
    
    async def expert_performance(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get expert analysts ranked by average rating accuracy."""
        query = (
            select(
                Expert.name,
                Expert.institution,
                Expert.avg_accuracy,
                Expert.total_ratings,
                func.avg(Rating.score).label('avg_score'),
                func.count(Rating.id).label('recent_ratings')
            )
            .join(Rating, Expert.id == Rating.expert_id)
            .where(and_(
                Expert.is_verified == True,
                Rating.rating_date >= datetime.utcnow() - timedelta(days=90)
            ))
            .group_by(Expert.id, Expert.name, Expert.institution, Expert.avg_accuracy, Expert.total_ratings)
            .order_by(desc(Expert.avg_accuracy))
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return [
            {
                'name': row.name,
                'institution': row.institution,
                'accuracy': float(row.avg_accuracy) if row.avg_accuracy else 0.0,
                'total_ratings': row.total_ratings,
                'avg_score': float(row.avg_score),
                'recent_ratings': row.recent_ratings
            }
            for row in result
        ]
    
    async def sentiment_analysis(self, days: int = 30) -> List[Dict[str, Any]]:
        """Analyze social media sentiment by stock."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(
                Stock.symbol,
                Stock.name,
                func.count(SocialPost.id).label('total_posts'),
                func.avg(SocialPost.sentiment_score).label('avg_sentiment'),
                func.sum(
                    func.case((SocialPost.sentiment_type.in_([
                        SentimentType.POSITIVE, 
                        SentimentType.VERY_POSITIVE
                    ]), 1), else_=0)
                ).label('positive_posts'),
                func.sum(
                    func.case((SocialPost.sentiment_type.in_([
                        SentimentType.NEGATIVE,
                        SentimentType.VERY_NEGATIVE
                    ]), 1), else_=0)
                ).label('negative_posts'),
                func.sum(SocialPost.score).label('total_engagement')
            )
            .join(SocialPost, Stock.id == SocialPost.stock_id)
            .where(SocialPost.posted_at >= cutoff_date)
            .group_by(Stock.id, Stock.symbol, Stock.name)
            .having(func.count(SocialPost.id) >= 5)  # At least 5 posts
            .order_by(desc('avg_sentiment'))
        )
        
        result = await self.session.execute(query)
        return [
            {
                'symbol': row.symbol,
                'name': row.name,
                'total_posts': row.total_posts,
                'avg_sentiment': float(row.avg_sentiment) if row.avg_sentiment else 0.0,
                'positive_posts': row.positive_posts or 0,
                'negative_posts': row.negative_posts or 0,
                'total_engagement': row.total_engagement or 0,
                'sentiment_ratio': (row.positive_posts or 0) / max(row.total_posts, 1)
            }
            for row in result
        ]
    
    async def market_overview(self) -> Dict[str, Any]:
        """Get overall market statistics and overview."""
        # Get sector distribution
        sector_query = (
            select(
                Stock.sector,
                func.count(Stock.id).label('stock_count'),
                func.avg(Stock.current_price).label('avg_price'),
                func.sum(Stock.market_cap).label('total_market_cap')
            )
            .group_by(Stock.sector)
            .order_by(desc('total_market_cap'))
        )
        sector_result = await self.session.execute(sector_query)
        
        # Get rating distribution
        rating_query = (
            select(
                Rating.recommendation,
                func.count(Rating.id).label('count')
            )
            .where(Rating.rating_type == RatingType.EXPERT)
            .group_by(Rating.recommendation)
        )
        rating_result = await self.session.execute(rating_query)
        
        # Get recent activity
        recent_ratings = await self.session.scalar(
            select(func.count(Rating.id))
            .where(Rating.rating_date >= datetime.utcnow() - timedelta(days=7))
        )
        
        recent_posts = await self.session.scalar(
            select(func.count(SocialPost.id))
            .where(SocialPost.posted_at >= datetime.utcnow() - timedelta(days=7))
        )
        
        return {
            'sectors': [
                {
                    'sector': row.sector,
                    'stock_count': row.stock_count,
                    'avg_price': float(row.avg_price) if row.avg_price else 0.0,
                    'total_market_cap': float(row.total_market_cap) if row.total_market_cap else 0.0
                }
                for row in sector_result
            ],
            'rating_distribution': [
                {
                    'recommendation': row.recommendation.value,
                    'count': row.count
                }
                for row in rating_result
            ],
            'recent_activity': {
                'ratings_last_7_days': recent_ratings or 0,
                'posts_last_7_days': recent_posts or 0
            }
        }
    
    async def stock_performance(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get stock performance metrics with price changes."""
        query = select(Stock)
        
        if symbol:
            query = query.where(Stock.symbol == symbol.upper())
        
        result = await self.session.execute(query)
        stocks = result.scalars().all()
        
        return [
            {
                'symbol': stock.symbol,
                'name': stock.name,
                'current_price': float(stock.current_price),
                'previous_close': float(stock.previous_close) if stock.previous_close else None,
                'price_change': float(stock.price_change) if stock.price_change else 0.0,
                'price_change_percent': float(stock.price_change_percent) if stock.price_change_percent else 0.0,
                'market_cap': float(stock.market_cap) if stock.market_cap else None,
                'pe_ratio': float(stock.pe_ratio) if stock.pe_ratio else None,
                'dividend_yield': float(stock.dividend_yield) if stock.dividend_yield else None,
                'sector': stock.sector
            }
            for stock in stocks
        ]
    
    async def social_media_trends(self, platform: Optional[str] = None, 
                                days: int = 7) -> List[Dict[str, Any]]:
        """Get trending stocks on social media platforms."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(
                Stock.symbol,
                SocialPost.platform,
                func.count(SocialPost.id).label('post_count'),
                func.sum(SocialPost.score).label('total_score'),
                func.avg(SocialPost.sentiment_score).label('avg_sentiment')
            )
            .join(Stock, SocialPost.stock_id == Stock.id)
            .where(SocialPost.posted_at >= cutoff_date)
        )
        
        if platform:
            query = query.where(SocialPost.platform == Platform(platform.lower()))
        
        query = (
            query
            .group_by(Stock.symbol, SocialPost.platform)
            .order_by(desc('post_count'))
        )
        
        result = await self.session.execute(query)
        return [
            {
                'symbol': row.symbol,
                'platform': row.platform.value,
                'post_count': row.post_count,
                'total_score': row.total_score or 0,
                'avg_sentiment': float(row.avg_sentiment) if row.avg_sentiment else 0.0
            }
            for row in result
        ]
    
    async def rating_distribution(self) -> List[Dict[str, Any]]:
        """Get distribution of ratings by score ranges."""
        query = (
            select(
                func.floor(Rating.score).label('score_floor'),
                func.count(Rating.id).label('count'),
                Rating.rating_type
            )
            .group_by('score_floor', Rating.rating_type)
            .order_by(asc('score_floor'))
        )
        
        result = await self.session.execute(query)
        return [
            {
                'score_range': f"{int(row.score_floor)}-{int(row.score_floor) + 1}",
                'count': row.count,
                'rating_type': row.rating_type.value
            }
            for row in result
        ]
    
    # ==================== UTILITY METHODS ====================
    
    async def execute_custom_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute custom SQL query and return results."""
        try:
            result = await self.session.execute(text(sql))
            rows = result.fetchall()
            columns = result.keys()
            
            return [
                {col: self._serialize_value(getattr(row, col)) for col in columns}
                for row in rows
            ]
        except Exception as e:
            raise ValueError(f"SQL execution error: {e}")
    
    def _serialize_value(self, value: Any) -> Any:
        """Convert database values to JSON-serializable types."""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif hasattr(value, 'value'):  # Enum
            return value.value
        return value
    
    def get_available_templates(self) -> List[str]:
        """Get list of available query templates."""
        return [
            'top_rated_stocks',
            'expert_performance',
            'sentiment_analysis',
            'market_overview',
            'stock_performance',
            'social_media_trends',
            'rating_distribution'
        ]
    
    async def run_template(self, template_name: str, **kwargs) -> Any:
        """Run a query template by name."""
        method = getattr(self, template_name, None)
        if not method:
            raise ValueError(f"Unknown template: {template_name}")
        
        return await method(**kwargs)


def export_to_csv(data: List[Dict[str, Any]], filename: str):
    """Export query results to CSV file."""
    if not data:
        print("No data to export")
        return
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ Exported {len(data)} rows to {filename}")


def export_to_json(data: Any, filename: str):
    """Export query results to JSON file."""
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, default=str)
    
    print(f"✅ Exported data to {filename}")


def print_table(data: List[Dict[str, Any]], max_rows: int = 20):
    """Print query results in a formatted table."""
    if not data:
        print("No results found")
        return
    
    # Get column widths
    columns = list(data[0].keys())
    widths = {col: max(len(col), max(len(str(row.get(col, ''))) for row in data[:max_rows])) 
              for col in columns}
    
    # Print header
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    print(header)
    print("-" * len(header))
    
    # Print rows
    for i, row in enumerate(data[:max_rows]):
        row_str = " | ".join(str(row.get(col, '')).ljust(widths[col]) for col in columns)
        print(row_str)
    
    if len(data) > max_rows:
        print(f"... and {len(data) - max_rows} more rows")


async def main():
    parser = argparse.ArgumentParser(description="Query RottenStocks database")
    parser.add_argument("--template", help="Query template to run")
    parser.add_argument("--sql", help="Custom SQL query to execute")
    parser.add_argument("--list-templates", action="store_true", help="List available templates")
    parser.add_argument("--export", help="Export results to file (CSV or JSON)")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of results")
    parser.add_argument("--symbol", help="Filter by stock symbol")
    parser.add_argument("--platform", help="Filter by social media platform")
    parser.add_argument("--days", type=int, default=30, help="Number of days for time-based queries")
    
    args = parser.parse_args()
    
    async with QueryBuilder() as qb:
        if args.list_templates:
            print("📋 Available query templates:")
            for template in qb.get_available_templates():
                print(f"  • {template}")
            return
        
        start_time = datetime.now()
        
        if args.sql:
            print(f"🔍 Executing custom SQL...")
            results = await qb.execute_custom_sql(args.sql)
        elif args.template:
            print(f"🔍 Running template: {args.template}")
            kwargs = {
                'limit': args.limit,
                'symbol': args.symbol,
                'platform': args.platform,
                'days': args.days
            }
            # Remove None values and filter by method signature
            kwargs = {k: v for k, v in kwargs.items() if v is not None}
            
            # Get method signature to filter kwargs
            import inspect
            method = getattr(qb, args.template)
            sig = inspect.signature(method)
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            
            results = await qb.run_template(args.template, **filtered_kwargs)
        else:
            print("❌ Please specify --template or --sql")
            return
        
        execution_time = (datetime.now() - start_time).total_seconds()
        print(f"⏱️  Query executed in {execution_time:.2f} seconds")
        print()
        
        if args.export:
            if args.export.endswith('.json'):
                export_to_json(results, args.export)
            else:
                export_to_csv(results, args.export)
        else:
            if isinstance(results, list):
                print_table(results)
            else:
                print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())