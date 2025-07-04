#!/usr/bin/env python3
"""
API Query Tool for RottenStocks Backend

Simple tool for querying API endpoints and fetching data from the locally running database.
Useful for testing and verification of backend functionality.

Usage:
    python api_query_tool.py --help
    python api_query_tool.py stocks list
    python api_query_tool.py stocks create --symbol AAPL --name "Apple Inc."
    python api_query_tool.py ratings list --stock-id <stock_id>
    python api_query_tool.py db stocks --limit 5
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import asyncpg
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich.panel import Panel

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
DB_URL = "postgresql://postgres:postgres@localhost:5432/rottenstocks"

console = Console()


class APIQueryTool:
    """Main API query tool class."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(base_url=API_BASE_URL)
        self.db_pool = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.db_pool = await asyncpg.create_pool(DB_URL)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http_client.aclose()
        if self.db_pool:
            await self.db_pool.close()

    # API Methods
    async def stocks_list(self, page: int = 1, limit: int = 10, search: str = None) -> Dict[str, Any]:
        """List stocks via API."""
        params = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        
        response = await self.http_client.get("/stocks/", params=params)
        response.raise_for_status()
        return response.json()
    
    async def stocks_create(self, symbol: str, name: str, exchange: str = "NASDAQ", **kwargs) -> Dict[str, Any]:
        """Create a stock via API."""
        data = {
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            **kwargs
        }
        
        response = await self.http_client.post("/stocks/", json=data)
        response.raise_for_status()
        return response.json()
    
    async def stocks_get_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """Get stock by symbol via API."""
        response = await self.http_client.get(f"/stocks/symbol/{symbol}")
        response.raise_for_status()
        return response.json()
    
    async def stocks_update_price(self, symbol: str, current_price: float, **kwargs) -> Dict[str, Any]:
        """Update stock price via API."""
        data = {"current_price": current_price, **kwargs}
        
        response = await self.http_client.patch(f"/stocks/symbol/{symbol}/price", json=data)
        response.raise_for_status()
        return response.json()
    
    async def ratings_list(self, stock_id: str = None, expert_id: str = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """List ratings via API."""
        params = {"page": page, "limit": limit}
        if stock_id:
            params["stock_id"] = stock_id
        if expert_id:
            params["expert_id"] = expert_id
        
        response = await self.http_client.get("/ratings/", params=params)
        response.raise_for_status()
        return response.json()
    
    async def ratings_create(self, stock_id: str, rating_type: str, score: float, recommendation: str, expert_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create a rating via API."""
        data = {
            "stock_id": stock_id,
            "rating_type": rating_type,
            "score": score,
            "recommendation": recommendation,
            "rating_date": datetime.now().isoformat(),
            **kwargs
        }
        if expert_id:
            data["expert_id"] = expert_id
        
        response = await self.http_client.post("/ratings/", json=data)
        response.raise_for_status()
        return response.json()
    
    async def ratings_aggregation(self, stock_id: str) -> Dict[str, Any]:
        """Get rating aggregation for a stock."""
        response = await self.http_client.get(f"/ratings/stock/{stock_id}/aggregation")
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = await self.http_client.get("/health/")
        response.raise_for_status()
        return response.json()

    # Database Methods
    async def db_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a database query directly."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def db_stocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get stocks directly from database."""
        query = """
            SELECT id, symbol, name, exchange, sector, current_price, is_active, created_at
            FROM stocks 
            ORDER BY created_at DESC 
            LIMIT $1
        """
        return await self.db_query(query, limit)
    
    async def db_ratings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get ratings directly from database."""
        query = """
            SELECT r.id, r.stock_id, s.symbol, r.rating_type, r.score, 
                   r.recommendation, r.rating_date, r.created_at
            FROM ratings r
            JOIN stocks s ON r.stock_id = s.id
            ORDER BY r.created_at DESC 
            LIMIT $1
        """
        return await self.db_query(query, limit)
    
    async def db_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        
        # Stock count
        result = await self.db_query("SELECT COUNT(*) as count FROM stocks WHERE is_active = true")
        stats["active_stocks"] = result[0]["count"]
        
        # Total ratings count
        result = await self.db_query("SELECT COUNT(*) as count FROM ratings")
        stats["total_ratings"] = result[0]["count"]
        
        # Expert ratings count
        result = await self.db_query("SELECT COUNT(*) as count FROM ratings WHERE rating_type = 'EXPERT'")
        stats["expert_ratings"] = result[0]["count"]
        
        # Popular ratings count
        result = await self.db_query("SELECT COUNT(*) as count FROM ratings WHERE rating_type = 'POPULAR'")
        stats["popular_ratings"] = result[0]["count"]
        
        return stats

    # Display Methods
    def display_json(self, data: Any, title: str = "Result"):
        """Display JSON data with syntax highlighting."""
        json_obj = JSON(json.dumps(data, indent=2, default=str))
        console.print(Panel(json_obj, title=title))
    
    def display_table(self, data: List[Dict[str, Any]], title: str = "Results"):
        """Display data as a table."""
        if not data:
            console.print(f"[yellow]No data found for {title}[/yellow]")
            return
        
        table = Table(title=title)
        
        # Add columns based on first row
        for key in data[0].keys():
            table.add_column(key.replace("_", " ").title(), style="cyan")
        
        # Add rows
        for row in data:
            values = []
            for value in row.values():
                if isinstance(value, datetime):
                    values.append(value.strftime("%Y-%m-%d %H:%M"))
                else:
                    values.append(str(value) if value is not None else "")
            table.add_row(*values)
        
        console.print(table)


async def create_sample_data(tool: APIQueryTool):
    """Create sample data for testing."""
    console.print("[bold blue]Creating sample data...[/bold blue]")
    
    try:
        # Create sample stocks
        stocks = [
            {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "sector": "Technology", "current_price": 150.0},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ", "sector": "Technology", "current_price": 2500.0},
            {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ", "sector": "Automotive", "current_price": 800.0},
        ]
        
        created_stocks = []
        for stock_data in stocks:
            try:
                stock = await tool.stocks_create(**stock_data)
                created_stocks.append(stock)
                console.print(f"✅ Created stock: {stock['symbol']}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    console.print(f"⚠️  Stock {stock_data['symbol']} already exists")
                    # Get existing stock
                    stock = await tool.stocks_get_by_symbol(stock_data['symbol'])
                    created_stocks.append(stock)
                else:
                    raise
        
        # Create sample ratings
        rating_data = [
            {"rating_type": "expert", "score": 4.5, "recommendation": "buy", "confidence": 0.8},
            {"rating_type": "popular", "score": 4.0, "recommendation": "buy", "confidence": 0.7},
            {"rating_type": "expert", "score": 3.5, "recommendation": "hold", "confidence": 0.6},
        ]
        
        for i, stock in enumerate(created_stocks[:2]):  # Only create ratings for first 2 stocks
            for j, rating in enumerate(rating_data):
                try:
                    rating_response = await tool.ratings_create(
                        stock_id=stock["id"],
                        **rating
                    )
                    console.print(f"✅ Created rating for {stock['symbol']}: {rating['score']}")
                except httpx.HTTPStatusError as e:
                    console.print(f"⚠️  Error creating rating: {e}")
        
        console.print("[bold green]Sample data creation completed![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error creating sample data: {e}[/bold red]")


async def main():
    parser = argparse.ArgumentParser(description="RottenStocks API Query Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Health command
    parser_health = subparsers.add_parser("health", help="Check API health")
    
    # Stocks commands
    parser_stocks = subparsers.add_parser("stocks", help="Stock operations")
    stocks_subparsers = parser_stocks.add_subparsers(dest="stocks_action")
    
    stocks_list_parser = stocks_subparsers.add_parser("list", help="List stocks")
    stocks_list_parser.add_argument("--page", type=int, default=1, help="Page number")
    stocks_list_parser.add_argument("--limit", type=int, default=10, help="Items per page")
    stocks_list_parser.add_argument("--search", help="Search query")
    
    stocks_create_parser = stocks_subparsers.add_parser("create", help="Create stock")
    stocks_create_parser.add_argument("--symbol", required=True, help="Stock symbol")
    stocks_create_parser.add_argument("--name", required=True, help="Company name")
    stocks_create_parser.add_argument("--exchange", default="NASDAQ", help="Exchange")
    stocks_create_parser.add_argument("--sector", help="Sector")
    stocks_create_parser.add_argument("--current-price", type=float, help="Current price")
    
    stocks_get_parser = stocks_subparsers.add_parser("get", help="Get stock by symbol")
    stocks_get_parser.add_argument("symbol", help="Stock symbol")
    
    stocks_price_parser = stocks_subparsers.add_parser("price", help="Update stock price")
    stocks_price_parser.add_argument("symbol", help="Stock symbol")
    stocks_price_parser.add_argument("price", type=float, help="New price")
    
    # Ratings commands
    parser_ratings = subparsers.add_parser("ratings", help="Rating operations")
    ratings_subparsers = parser_ratings.add_subparsers(dest="ratings_action")
    
    ratings_list_parser = ratings_subparsers.add_parser("list", help="List ratings")
    ratings_list_parser.add_argument("--stock-id", help="Filter by stock ID")
    ratings_list_parser.add_argument("--expert-id", help="Filter by expert ID")
    ratings_list_parser.add_argument("--page", type=int, default=1, help="Page number")
    ratings_list_parser.add_argument("--limit", type=int, default=10, help="Items per page")
    
    ratings_create_parser = ratings_subparsers.add_parser("create", help="Create rating")
    ratings_create_parser.add_argument("--stock-id", required=True, help="Stock ID")
    ratings_create_parser.add_argument("--type", choices=["expert", "popular"], default="expert", help="Rating type")
    ratings_create_parser.add_argument("--score", type=float, required=True, help="Rating score (0-5)")
    ratings_create_parser.add_argument("--recommendation", choices=["buy", "sell", "hold"], required=True, help="Recommendation")
    ratings_create_parser.add_argument("--confidence", type=float, default=0.5, help="Confidence (0-1)")
    ratings_create_parser.add_argument("--expert-id", help="Expert ID (for expert ratings)")
    
    ratings_agg_parser = ratings_subparsers.add_parser("aggregation", help="Get rating aggregation")
    ratings_agg_parser.add_argument("stock_id", help="Stock ID")
    
    # Database commands
    parser_db = subparsers.add_parser("db", help="Direct database operations")
    db_subparsers = parser_db.add_subparsers(dest="db_action")
    
    db_stocks_parser = db_subparsers.add_parser("stocks", help="Get stocks from DB")
    db_stocks_parser.add_argument("--limit", type=int, default=10, help="Limit results")
    
    db_ratings_parser = db_subparsers.add_parser("ratings", help="Get ratings from DB")
    db_ratings_parser.add_argument("--limit", type=int, default=10, help="Limit results")
    
    db_stats_parser = db_subparsers.add_parser("stats", help="Get database statistics")
    
    db_query_parser = db_subparsers.add_parser("query", help="Execute custom query")
    db_query_parser.add_argument("query", help="SQL query to execute")
    
    # Sample data command
    parser_sample = subparsers.add_parser("sample", help="Create sample data")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    async with APIQueryTool() as tool:
        try:
            if args.command == "health":
                result = await tool.health_check()
                tool.display_json(result, "Health Check")
            
            elif args.command == "stocks":
                if args.stocks_action == "list":
                    result = await tool.stocks_list(args.page, args.limit, args.search)
                    tool.display_table(result["stocks"], f"Stocks (Page {args.page})")
                    console.print(f"Total: {result['total']}, Page: {result['page']}/{result['pages']}")
                
                elif args.stocks_action == "create":
                    kwargs = {}
                    if args.sector:
                        kwargs["sector"] = args.sector
                    if args.current_price:
                        kwargs["current_price"] = args.current_price
                    
                    result = await tool.stocks_create(args.symbol, args.name, args.exchange, **kwargs)
                    tool.display_json(result, "Created Stock")
                
                elif args.stocks_action == "get":
                    result = await tool.stocks_get_by_symbol(args.symbol)
                    tool.display_json(result, f"Stock: {args.symbol}")
                
                elif args.stocks_action == "price":
                    result = await tool.stocks_update_price(args.symbol, args.price)
                    tool.display_json(result, f"Updated Price for {args.symbol}")
            
            elif args.command == "ratings":
                if args.ratings_action == "list":
                    result = await tool.ratings_list(args.stock_id, args.expert_id, args.page, args.limit)
                    tool.display_table(result["ratings"], f"Ratings (Page {args.page})")
                    console.print(f"Total: {result['total']}, Page: {result['page']}/{result['pages']}")
                
                elif args.ratings_action == "create":
                    result = await tool.ratings_create(
                        args.stock_id, args.type, args.score, args.recommendation, 
                        expert_id=getattr(args, 'expert_id', None), confidence=args.confidence
                    )
                    tool.display_json(result, "Created Rating")
                
                elif args.ratings_action == "aggregation":
                    result = await tool.ratings_aggregation(args.stock_id)
                    tool.display_json(result, "Rating Aggregation")
            
            elif args.command == "db":
                if args.db_action == "stocks":
                    result = await tool.db_stocks(args.limit)
                    tool.display_table(result, "Database Stocks")
                
                elif args.db_action == "ratings":
                    result = await tool.db_ratings(args.limit)
                    tool.display_table(result, "Database Ratings")
                
                elif args.db_action == "stats":
                    result = await tool.db_stats()
                    tool.display_json(result, "Database Statistics")
                
                elif args.db_action == "query":
                    result = await tool.db_query(args.query)
                    tool.display_table(result, "Query Results")
            
            elif args.command == "sample":
                await create_sample_data(tool)
        
        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]HTTP Error {e.response.status_code}:[/bold red] {e.response.text}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())