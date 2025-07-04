#!/usr/bin/env python3
"""
Database Health Check Tool for RottenStocks

This script performs comprehensive health checks on the database,
including connectivity, data integrity, performance, and migration status.

Usage:
    python health_check.py [options]
    
Examples:
    # Quick connection test
    python health_check.py --quick
    
    # Full comprehensive health check
    python health_check.py --full
    
    # Check specific table
    python health_check.py --table stocks
    
    # Performance benchmark
    python health_check.py --benchmark
"""

import sys
import os
import asyncio
import argparse
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

# Import new database utilities
from app.db.utils import DatabaseManager
from app.db.config import get_database_config
from app.db.exceptions import DatabaseError, handle_database_error
from app.db.repositories import StockRepository, ExpertRepository, RatingRepository, SocialPostRepository

# Import models for type checking
from app.db.models.stock import Stock
from app.db.models.expert import Expert
from app.db.models.rating import Rating
from app.db.models.social_post import SocialPost


class HealthCheck:
    """Database health check and diagnostics tool using new database utilities."""
    
    def __init__(self):
        self.db_manager = None
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'overall_status': 'UNKNOWN',
            'critical_issues': [],
            'warnings': [],
            'info': []
        }
        
        # Get database configuration using new utilities
        self.db_config = get_database_config()
        
    async def __aenter__(self):
        # Create database manager using new utilities
        self.db_manager = DatabaseManager(
            self.db_config.database_url,
            **self.db_config.get_engine_kwargs()
        )
        await self.db_manager.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.db_manager:
            await self.db_manager.shutdown()
    
    def add_check(self, name: str, status: str, details: str = "", 
                  duration: float = 0.0, data: Any = None):
        """Add a health check result."""
        check = {
            'name': name,
            'status': status,
            'details': details,
            'duration_ms': round(duration * 1000, 2),
            'data': data
        }
        self.results['checks'].append(check)
        
        if status == 'CRITICAL':
            self.results['critical_issues'].append(f"{name}: {details}")
        elif status == 'WARNING':
            self.results['warnings'].append(f"{name}: {details}")
        elif status == 'INFO':
            self.results['info'].append(f"{name}: {details}")
    
    async def check_connection(self) -> bool:
        """Test basic database connectivity using new utilities."""
        start_time = time.time()
        try:
            # Use the database manager's health check
            health_result = await self.db_manager.health_check()
            duration = time.time() - start_time
            
            if health_result["status"] == "healthy":
                self.add_check(
                    "Database Connection",
                    "PASS", 
                    "Successfully connected to database using DatabaseManager",
                    duration,
                    health_result
                )
                return True
            else:
                self.add_check(
                    "Database Connection",
                    "CRITICAL",
                    f"Database health check failed: {health_result.get('error', 'Unknown error')}",
                    duration,
                    health_result
                )
                return False
        except DatabaseError as e:
            duration = time.time() - start_time
            self.add_check(
                "Database Connection",
                "CRITICAL",
                f"Database error: {e.message}",
                duration
            )
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.add_check(
                "Database Connection", 
                "CRITICAL",
                f"Unexpected error: {handle_database_error(e).message}",
                duration
            )
            return False
    
    async def check_tables_exist(self) -> bool:
        """Verify all required tables exist."""
        start_time = time.time()
        try:
            required_tables = ['stocks', 'experts', 'ratings', 'social_posts']
            existing_tables = []
            
            for table in required_tables:
                try:
                    await self.session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                    existing_tables.append(table)
                except Exception:
                    pass
            
            duration = time.time() - start_time
            
            if len(existing_tables) == len(required_tables):
                self.add_check(
                    "Table Existence",
                    "PASS",
                    f"All {len(required_tables)} required tables exist",
                    duration,
                    existing_tables
                )
                return True
            else:
                missing_tables = set(required_tables) - set(existing_tables)
                self.add_check(
                    "Table Existence",
                    "CRITICAL",
                    f"Missing tables: {', '.join(missing_tables)}",
                    duration,
                    {'existing': existing_tables, 'missing': list(missing_tables)}
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_check(
                "Table Existence",
                "CRITICAL",
                f"Error checking tables: {e}",
                duration
            )
            return False
    
    async def check_data_counts(self) -> Dict[str, int]:
        """Check record counts in all tables using new utilities."""
        start_time = time.time()
        try:
            # Use the database manager's table stats method
            counts = await self.db_manager.get_table_stats()
            
            duration = time.time() - start_time
            total_records = sum(counts.values())
            
            if total_records > 0:
                self.add_check(
                    "Data Count",
                    "PASS",
                    f"Found {total_records} total records using DatabaseManager",
                    duration,
                    counts
                )
            else:
                self.add_check(
                    "Data Count", 
                    "WARNING",
                    "No data found in any tables",
                    duration,
                    counts
                )
            
            return counts
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_check(
                "Data Count",
                "CRITICAL",
                f"Error counting records: {e}",
                duration
            )
            return {}
    
    async def check_foreign_key_integrity(self) -> bool:
        """Check foreign key relationships integrity."""
        start_time = time.time()
        try:
            issues = []
            
            # Check ratings with invalid stock_id
            invalid_stock_ratings = await self.session.scalar(
                select(func.count(Rating.id))
                .outerjoin(Stock, Rating.stock_id == Stock.id)
                .where(Stock.id.is_(None))
            )
            if invalid_stock_ratings > 0:
                issues.append(f"{invalid_stock_ratings} ratings with invalid stock_id")
            
            # Check ratings with invalid expert_id (excluding popular ratings)
            invalid_expert_ratings = await self.session.scalar(
                select(func.count(Rating.id))
                .outerjoin(Expert, Rating.expert_id == Expert.id)
                .where(and_(Expert.id.is_(None), Rating.expert_id.is_not(None)))
            )
            if invalid_expert_ratings > 0:
                issues.append(f"{invalid_expert_ratings} ratings with invalid expert_id")
            
            # Check social posts with invalid stock_id
            invalid_stock_posts = await self.session.scalar(
                select(func.count(SocialPost.id))
                .outerjoin(Stock, SocialPost.stock_id == Stock.id)
                .where(Stock.id.is_(None))
            )
            if invalid_stock_posts > 0:
                issues.append(f"{invalid_stock_posts} social posts with invalid stock_id")
            
            duration = time.time() - start_time
            
            if not issues:
                self.add_check(
                    "Foreign Key Integrity",
                    "PASS",
                    "All foreign key relationships are valid",
                    duration
                )
                return True
            else:
                self.add_check(
                    "Foreign Key Integrity",
                    "CRITICAL",
                    f"Found integrity issues: {'; '.join(issues)}",
                    duration,
                    issues
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_check(
                "Foreign Key Integrity",
                "CRITICAL",
                f"Error checking integrity: {e}",
                duration
            )
            return False
    
    async def check_data_quality(self) -> List[str]:
        """Check for data quality issues."""
        start_time = time.time()
        try:
            issues = []
            
            # Check for stocks with invalid prices
            negative_prices = await self.session.scalar(
                select(func.count(Stock.id))
                .where(Stock.current_price <= 0)
            )
            if negative_prices > 0:
                issues.append(f"{negative_prices} stocks with negative/zero prices")
            
            # Check for ratings outside valid range
            invalid_ratings = await self.session.scalar(
                select(func.count(Rating.id))
                .where(or_(Rating.score < 0, Rating.score > 5))
            )
            if invalid_ratings > 0:
                issues.append(f"{invalid_ratings} ratings outside 0-5 range")
            
            # Check for sentiment scores outside valid range
            invalid_sentiment = await self.session.scalar(
                select(func.count(SocialPost.id))
                .where(or_(
                    SocialPost.sentiment_score < 0,
                    SocialPost.sentiment_score > 1
                ))
            )
            if invalid_sentiment > 0:
                issues.append(f"{invalid_sentiment} social posts with invalid sentiment scores")
            
            # Check for future dates
            future_ratings = await self.session.scalar(
                select(func.count(Rating.id))
                .where(Rating.rating_date > datetime.now())
            )
            if future_ratings > 0:
                issues.append(f"{future_ratings} ratings with future dates")
            
            duration = time.time() - start_time
            
            if not issues:
                self.add_check(
                    "Data Quality",
                    "PASS",
                    "No data quality issues found",
                    duration
                )
            else:
                self.add_check(
                    "Data Quality",
                    "WARNING",
                    f"Found quality issues: {'; '.join(issues)}",
                    duration,
                    issues
                )
            
            return issues
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_check(
                "Data Quality",
                "CRITICAL",
                f"Error checking data quality: {e}",
                duration
            )
            return [f"Error: {e}"]
    
    async def check_recent_activity(self, days: int = 7) -> Dict[str, int]:
        """Check for recent activity in the database."""
        start_time = time.time()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            recent_ratings = await self.session.scalar(
                select(func.count(Rating.id))
                .where(Rating.created_at >= cutoff_date)
            )
            
            recent_posts = await self.session.scalar(
                select(func.count(SocialPost.id))
                .where(SocialPost.created_at >= cutoff_date)
            )
            
            recent_stocks = await self.session.scalar(
                select(func.count(Stock.id))
                .where(Stock.created_at >= cutoff_date)
            )
            
            recent_experts = await self.session.scalar(
                select(func.count(Expert.id))
                .where(Expert.created_at >= cutoff_date)
            )
            
            activity = {
                'ratings': recent_ratings or 0,
                'social_posts': recent_posts or 0,
                'stocks': recent_stocks or 0,
                'experts': recent_experts or 0
            }
            
            total_activity = sum(activity.values())
            duration = time.time() - start_time
            
            if total_activity > 0:
                self.add_check(
                    f"Recent Activity ({days} days)",
                    "INFO",
                    f"Found {total_activity} recent records",
                    duration,
                    activity
                )
            else:
                self.add_check(
                    f"Recent Activity ({days} days)",
                    "WARNING",
                    f"No activity in the last {days} days",
                    duration,
                    activity
                )
            
            return activity
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_check(
                f"Recent Activity ({days} days)",
                "CRITICAL",
                f"Error checking recent activity: {e}",
                duration
            )
            return {}
    
    async def performance_benchmark(self) -> Dict[str, float]:
        """Run performance benchmarks on common queries."""
        benchmarks = {}
        
        # Simple select benchmark
        start_time = time.time()
        await self.session.execute(select(Stock).limit(100))
        benchmarks['simple_select'] = time.time() - start_time
        
        # Join query benchmark
        start_time = time.time()
        await self.session.execute(
            select(Stock, Rating)
            .join(Rating, Stock.id == Rating.stock_id)
            .limit(100)
        )
        benchmarks['join_query'] = time.time() - start_time
        
        # Aggregation benchmark
        start_time = time.time()
        await self.session.execute(
            select(Stock.sector, func.count(Stock.id))
            .group_by(Stock.sector)
        )
        benchmarks['aggregation'] = time.time() - start_time
        
        # Complex query benchmark
        start_time = time.time()
        await self.session.execute(
            select(
                Stock.symbol,
                func.avg(Rating.score),
                func.count(SocialPost.id)
            )
            .outerjoin(Rating, Stock.id == Rating.stock_id)
            .outerjoin(SocialPost, Stock.id == SocialPost.stock_id)
            .group_by(Stock.id, Stock.symbol)
            .having(func.count(Rating.id) > 0)
        )
        benchmarks['complex_query'] = time.time() - start_time
        
        # Determine performance status
        max_time = max(benchmarks.values())
        if max_time < 0.1:
            status = "PASS"
            details = "All queries performed well (< 100ms)"
        elif max_time < 1.0:
            status = "WARNING"
            details = f"Some queries are slow (max: {max_time:.3f}s)"
        else:
            status = "CRITICAL"
            details = f"Slow query performance detected (max: {max_time:.3f}s)"
        
        self.add_check(
            "Performance Benchmark",
            status,
            details,
            sum(benchmarks.values()),
            {k: round(v * 1000, 2) for k, v in benchmarks.items()}  # Convert to ms
        )
        
        return benchmarks
    
    async def check_migration_status(self) -> Optional[str]:
        """Check Alembic migration status."""
        start_time = time.time()
        try:
            # Check if alembic_version table exists
            result = await self.session.execute(
                text("SELECT version_num FROM alembic_version")
            )
            current_version = result.scalar()
            
            duration = time.time() - start_time
            
            if current_version:
                self.add_check(
                    "Migration Status",
                    "PASS",
                    f"Database is at migration version: {current_version}",
                    duration,
                    {'current_version': current_version}
                )
                return current_version
            else:
                self.add_check(
                    "Migration Status",
                    "WARNING",
                    "No migration version found",
                    duration
                )
                return None
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_check(
                "Migration Status",
                "WARNING",
                f"Could not check migration status: {e}",
                duration
            )
            return None
    
    def calculate_overall_status(self):
        """Calculate overall health status based on individual checks."""
        critical_count = len(self.results['critical_issues'])
        warning_count = len(self.results['warnings'])
        
        if critical_count > 0:
            self.results['overall_status'] = 'CRITICAL'
        elif warning_count > 0:
            self.results['overall_status'] = 'WARNING'
        else:
            self.results['overall_status'] = 'HEALTHY'
    
    async def run_quick_check(self):
        """Run basic health checks for quick verification."""
        print("🏥 Running quick health check...")
        
        await self.check_connection()
        await self.check_tables_exist()
        await self.check_data_counts()
        
        self.calculate_overall_status()
    
    async def run_full_check(self):
        """Run comprehensive health check."""
        print("🏥 Running comprehensive health check...")
        
        await self.check_connection()
        await self.check_tables_exist()
        await self.check_data_counts()
        await self.check_foreign_key_integrity()
        await self.check_data_quality()
        await self.check_recent_activity()
        await self.check_migration_status()
        
        self.calculate_overall_status()
    
    async def run_benchmark(self):
        """Run performance benchmarks."""
        print("⚡ Running performance benchmarks...")
        
        await self.check_connection()
        await self.performance_benchmark()
        
        self.calculate_overall_status()
    
    def print_results(self, verbose: bool = False):
        """Print health check results in a formatted way."""
        status_emoji = {
            'HEALTHY': '✅',
            'WARNING': '⚠️',
            'CRITICAL': '❌'
        }
        
        print(f"\n{status_emoji.get(self.results['overall_status'], '❓')} Overall Status: {self.results['overall_status']}")
        print(f"📅 Check Time: {self.results['timestamp']}")
        print()
        
        # Print individual checks
        for check in self.results['checks']:
            status_symbol = {
                'PASS': '✅',
                'WARNING': '⚠️',
                'CRITICAL': '❌',
                'INFO': 'ℹ️'
            }.get(check['status'], '❓')
            
            print(f"{status_symbol} {check['name']}: {check['details']}")
            if verbose and check.get('data'):
                print(f"   Data: {check['data']}")
            if check['duration_ms'] > 0:
                print(f"   Duration: {check['duration_ms']}ms")
        
        # Print summary
        if self.results['critical_issues']:
            print(f"\n❌ Critical Issues ({len(self.results['critical_issues'])}):")
            for issue in self.results['critical_issues']:
                print(f"   • {issue}")
        
        if self.results['warnings']:
            print(f"\n⚠️  Warnings ({len(self.results['warnings'])}):")
            for warning in self.results['warnings']:
                print(f"   • {warning}")
        
        if self.results['info']:
            print(f"\nℹ️  Information ({len(self.results['info'])}):")
            for info in self.results['info']:
                print(f"   • {info}")


async def main():
    parser = argparse.ArgumentParser(description="Database health check for RottenStocks")
    parser.add_argument("--quick", action="store_true", help="Run quick health check")
    parser.add_argument("--full", action="store_true", help="Run comprehensive health check")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--table", help="Check specific table health")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    async with HealthCheck() as health:
        if args.benchmark:
            await health.run_benchmark()
        elif args.full:
            await health.run_full_check()
        elif args.table:
            print(f"🔍 Checking table: {args.table}")
            await health.check_connection()
            # Add specific table checks here
        else:
            await health.run_quick_check()
        
        health.print_results(verbose=args.verbose)


if __name__ == "__main__":
    asyncio.run(main())