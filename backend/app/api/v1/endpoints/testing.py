"""
Testing and verification endpoints for development and QA.

Provides endpoints for testing API integrations, verifying data freshness,
and validating system components.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel

from app.db.session import get_managed_session
from app.core.logging import get_logger
from app.db.models.stock import Stock
from app.services.stock_service import StockService
from app.external_apis.providers import get_alpha_vantage_client
from app.external_apis.alpha_vantage.service import AlphaVantageService
from app.tasks.stock_sync import get_task_manager
from app.core.config import get_settings

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class DataFreshnessReport(BaseModel):
    """Report on data freshness and update status."""
    total_stocks: int
    updated_last_hour: int
    updated_last_day: int
    stale_stocks: int
    oldest_update: Optional[datetime]
    newest_update: Optional[datetime]
    average_age_minutes: float
    stocks_needing_update: List[str]


class APITestResult(BaseModel):
    """Result of API integration test."""
    api_name: str
    endpoint: str
    success: bool
    response_time_ms: float
    status_code: Optional[int] = None
    data_received: bool
    error_message: Optional[str] = None
    sample_data: Optional[Dict[str, Any]] = None


class SystemValidationResult(BaseModel):
    """Result of system validation."""
    component: str
    healthy: bool
    details: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]


class ComprehensiveTestReport(BaseModel):
    """Comprehensive test report."""
    timestamp: datetime
    data_freshness: DataFreshnessReport
    api_tests: List[APITestResult]
    system_validation: List[SystemValidationResult]
    overall_health: bool
    summary: str


@router.get("/data-freshness", response_model=DataFreshnessReport)
async def check_data_freshness():
    """Check the freshness of stock data in the database."""
    try:
        async with get_managed_session() as session:
            # Get total stocks
            total_stocks_result = await session.execute(select(func.count(Stock.id)))
            total_stocks = total_stocks_result.scalar()
            
            # Get stocks updated in last hour
            hour_ago = datetime.now() - timedelta(hours=1)
            recent_stocks_result = await session.execute(
                select(func.count(Stock.id)).where(Stock.last_updated >= hour_ago)
            )
            updated_last_hour = recent_stocks_result.scalar()
            
            # Get stocks updated in last day
            day_ago = datetime.now() - timedelta(days=1)
            daily_stocks_result = await session.execute(
                select(func.count(Stock.id)).where(Stock.last_updated >= day_ago)
            )
            updated_last_day = daily_stocks_result.scalar()
            
            # Get stale stocks (older than 2 hours)
            stale_cutoff = datetime.now() - timedelta(hours=2)
            stale_stocks_result = await session.execute(
                select(func.count(Stock.id)).where(Stock.last_updated < stale_cutoff)
            )
            stale_stocks = stale_stocks_result.scalar()
            
            # Get oldest and newest updates
            oldest_result = await session.execute(
                select(Stock.last_updated).order_by(Stock.last_updated.asc()).limit(1)
            )
            oldest_update = oldest_result.scalar()
            
            newest_result = await session.execute(
                select(Stock.last_updated).order_by(Stock.last_updated.desc()).limit(1)
            )
            newest_update = newest_result.scalar()
            
            # Calculate average age
            if total_stocks > 0:
                avg_age_result = await session.execute(
                    select(func.avg(func.extract('epoch', datetime.now() - Stock.last_updated)))
                )
                avg_age_seconds = avg_age_result.scalar() or 0
                average_age_minutes = avg_age_seconds / 60
            else:
                average_age_minutes = 0.0
            
            # Get stocks needing update
            needs_update_result = await session.execute(
                select(Stock.symbol)
                .where(Stock.last_updated < stale_cutoff)
                .where(Stock.is_active == True)
                .limit(10)
            )
            stocks_needing_update = [row[0] for row in needs_update_result.fetchall()]
        
        return DataFreshnessReport(
            total_stocks=total_stocks,
            updated_last_hour=updated_last_hour,
            updated_last_day=updated_last_day,
            stale_stocks=stale_stocks,
            oldest_update=oldest_update,
            newest_update=newest_update,
            average_age_minutes=average_age_minutes,
            stocks_needing_update=stocks_needing_update
        )
        
    except Exception as e:
        logger.error(f"Failed to check data freshness: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/alpha-vantage", response_model=APITestResult)
async def test_alpha_vantage_api(
    symbol: str = Query("AAPL", description="Stock symbol to test"),
    test_type: str = Query("quote", description="Type of test: quote, overview, search")
):
    """Test Alpha Vantage API integration."""
    import time
    
    start_time = time.time()
    
    try:
        async with get_managed_session() as session:
            client = get_alpha_vantage_client()
            alpha_vantage = AlphaVantageService(client=client, db=session)
            
            if test_type == "quote":
                data = await alpha_vantage.get_stock_quote(symbol)
                if data:
                    sample_data = {
                        "symbol": data.symbol,
                        "price": float(data.price) if data.price else None,
                        "change": float(data.change) if data.change else None,
                        "volume": int(data.volume) if data.volume else None
                    }
                else:
                    sample_data = {"error": "No data returned"}
            elif test_type == "overview":
                data = await alpha_vantage.get_company_overview(symbol)
                if data:
                    sample_data = {
                        "symbol": data.symbol,
                        "name": data.name,
                        "market_cap": str(data.market_capitalization) if data.market_capitalization else None,
                        "pe_ratio": str(data.pe_ratio) if data.pe_ratio else None
                    }
                else:
                    sample_data = {"error": "No data returned"}
            elif test_type == "search":
                data = await alpha_vantage.search_symbols(symbol)
                if data:
                    sample_data = {
                        "matches": len(data),
                        "first_match": data[0].symbol if data else None
                    }
                else:
                    sample_data = {"matches": 0, "first_match": None}
            else:
                raise ValueError(f"Invalid test type: {test_type}")
        
        response_time = (time.time() - start_time) * 1000
        
        return APITestResult(
            api_name="Alpha Vantage",
            endpoint=f"/{test_type}",
            success=True,
            response_time_ms=response_time,
            status_code=200,
            data_received=True,
            sample_data=sample_data
        )
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        
        return APITestResult(
            api_name="Alpha Vantage",
            endpoint=f"/{test_type}",
            success=False,
            response_time_ms=response_time,
            status_code=None,
            data_received=False,
            error_message=str(e),
            sample_data=None
        )


@router.post("/database/verify", response_model=SystemValidationResult)
async def verify_database_integration():
    """Verify database integration and data consistency."""
    try:
        async with get_managed_session() as session:
            issues = []
            recommendations = []
            details = {}
            
            # Test basic connectivity
            await session.execute(select(1))
            details["connectivity"] = "OK"
            
            # Check stock table
            stock_count = await session.execute(select(func.count(Stock.id)))
            total_stocks = stock_count.scalar()
            details["total_stocks"] = total_stocks
            
            if total_stocks == 0:
                issues.append("No stocks found in database")
                recommendations.append("Add some stocks to test with")
            
            # Check for NULL values in critical fields
            null_price_count = await session.execute(
                select(func.count(Stock.id)).where(Stock.current_price.is_(None))
            )
            null_prices = null_price_count.scalar()
            details["null_prices"] = null_prices
            
            if null_prices > 0:
                issues.append(f"{null_prices} stocks have NULL prices")
                recommendations.append("Update stock prices")
            
            # Check for very old data
            week_ago = datetime.now() - timedelta(days=7)
            old_data_count = await session.execute(
                select(func.count(Stock.id)).where(Stock.last_updated < week_ago)
            )
            old_data = old_data_count.scalar()
            details["old_data_count"] = old_data
            
            if old_data > total_stocks * 0.5:  # More than 50% old data
                issues.append(f"{old_data} stocks have data older than 1 week")
                recommendations.append("Run stock synchronization")
            
            # Check indexes and performance
            # This is a simplified check - in production you'd want more comprehensive checks
            details["indexes_exist"] = True  # Placeholder
            
            healthy = len(issues) == 0
        
        return SystemValidationResult(
            component="Database",
            healthy=healthy,
            details=details,
            issues=issues,
            recommendations=recommendations
        )
        
    except Exception as e:
        return SystemValidationResult(
            component="Database",
            healthy=False,
            details={"error": str(e)},
            issues=[f"Database connection failed: {str(e)}"],
            recommendations=["Check database server and connection settings"]
        )


@router.post("/sync/validate", response_model=SystemValidationResult)
async def validate_sync_system():
    """Validate the stock synchronization system."""
    try:
        issues = []
        recommendations = []
        details = {}
        
        # Check task manager
        task_manager = get_task_manager()
        sync_stats = await task_manager.get_sync_stats()
        
        details["requests_used_today"] = sync_stats["requests_used_today"]
        details["daily_limit"] = sync_stats["daily_limit"]
        details["requests_remaining"] = sync_stats["requests_remaining"]
        details["active_stocks"] = sync_stats["active_stocks"]
        details["needs_update"] = sync_stats["needs_update"]
        
        # Check if we're hitting rate limits
        if sync_stats["requests_used_today"] >= sync_stats["daily_limit"]:
            issues.append("Daily API request limit reached")
            recommendations.append("Wait for limit reset or upgrade API plan")
        
        # Check if there are stocks needing updates
        if sync_stats["needs_update"] > sync_stats["active_stocks"] * 0.8:
            issues.append("Most stocks need updating")
            recommendations.append("Check if sync task is running properly")
        
        # Check scheduler
        from app.tasks.scheduler import get_scheduler
        scheduler = get_scheduler()
        
        details["scheduler_running"] = scheduler.is_running
        if not scheduler.is_running:
            issues.append("Task scheduler is not running")
            recommendations.append("Start the task scheduler")
        
        healthy = len(issues) == 0
        
        return SystemValidationResult(
            component="Sync System",
            healthy=healthy,
            details=details,
            issues=issues,
            recommendations=recommendations
        )
        
    except Exception as e:
        return SystemValidationResult(
            component="Sync System",
            healthy=False,
            details={"error": str(e)},
            issues=[f"Sync system validation failed: {str(e)}"],
            recommendations=["Check task scheduler and background services"]
        )


@router.get("/comprehensive", response_model=ComprehensiveTestReport)
async def comprehensive_test_report():
    """Generate a comprehensive test report."""
    try:
        # Get data freshness
        data_freshness = await check_data_freshness()
        
        # Test Alpha Vantage API
        api_tests = []
        for test_type in ["quote", "overview"]:
            api_result = await test_alpha_vantage_api("AAPL", test_type)
            api_tests.append(api_result)
        
        # Validate systems
        system_validation = []
        db_validation = await verify_database_integration()
        system_validation.append(db_validation)
        
        sync_validation = await validate_sync_system()
        system_validation.append(sync_validation)
        
        # Determine overall health
        api_healthy = all(test.success for test in api_tests)
        system_healthy = all(validation.healthy for validation in system_validation)
        data_healthy = data_freshness.stale_stocks < data_freshness.total_stocks * 0.5
        
        overall_health = api_healthy and system_healthy and data_healthy
        
        # Generate summary
        if overall_health:
            summary = "All systems operational"
        else:
            issues = []
            if not api_healthy:
                issues.append("API integration issues")
            if not system_healthy:
                issues.append("System validation issues")
            if not data_healthy:
                issues.append("Data freshness issues")
            summary = f"Issues detected: {', '.join(issues)}"
        
        return ComprehensiveTestReport(
            timestamp=datetime.now(),
            data_freshness=data_freshness,
            api_tests=api_tests,
            system_validation=system_validation,
            overall_health=overall_health,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Failed to generate comprehensive test report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed-data", response_model=Dict[str, Any])
async def seed_test_data(
    symbols: List[str] = Query(["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]),
    force_update: bool = Query(False, description="Force update even if data exists")
):
    """Seed the database with test stock data."""
    try:
        async with get_managed_session() as session:
            stock_service = StockService(session)
            results = {
                "symbols_processed": 0,
                "successful_updates": 0,
                "failed_updates": 0,
                "errors": []
            }
            
            for symbol in symbols:
                try:
                    # Check if stock exists
                    existing_stock = await session.execute(
                        select(Stock).where(Stock.symbol == symbol)
                    )
                    stock = existing_stock.scalar_one_or_none()
                    
                    if stock and not force_update:
                        results["symbols_processed"] += 1
                        continue
                    
                    # Sync stock data - note: this method might not exist
                    # We'll need to use the external API service directly
                    client = get_alpha_vantage_client()
                    alpha_vantage = AlphaVantageService(client=client, db=session)
                    
                    # Get quote data
                    quote_data = await alpha_vantage.get_stock_quote(symbol)
                    
                    # Create or update stock
                    if stock:
                        stock.current_price = quote_data.price
                        stock.previous_close = quote_data.previous_close
                        stock.change = quote_data.change
                        stock.change_percent = quote_data.change_percent
                        stock.volume = quote_data.volume
                        stock.last_updated = datetime.now()
                    else:
                        stock = Stock(
                            symbol=symbol,
                            current_price=quote_data.price,
                            previous_close=quote_data.previous_close,
                            change=quote_data.change,
                            change_percent=quote_data.change_percent,
                            volume=quote_data.volume,
                            last_updated=datetime.now(),
                            is_active=True
                        )
                        session.add(stock)
                    
                    await session.commit()
                    results["successful_updates"] += 1
                    
                except Exception as e:
                    results["failed_updates"] += 1
                    results["errors"].append(f"{symbol}: {str(e)}")
                
                results["symbols_processed"] += 1
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to seed test data: {e}")
        raise HTTPException(status_code=500, detail=str(e))