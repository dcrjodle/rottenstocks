#!/usr/bin/env python3
"""
Quick Demo Script for RottenStocks API Query Tool

Demonstrates the working functionality of the API query tool.
"""

import asyncio
import sys
from api_query_tool import APIQueryTool

async def main():
    """Run a quick demo of the API query tool functionality."""
    print("🚀 RottenStocks API Query Tool Demo")
    print("=" * 50)
    
    async with APIQueryTool() as tool:
        try:
            # 1. Health Check
            print("\n1. 🏥 API Health Check")
            health = await tool.health_check()
            print(f"   Status: {health['status']}")
            print(f"   Service: {health['service']}")
            print(f"   Environment: {health['environment']}")
            
            # 2. Database Statistics
            print("\n2. 📊 Database Statistics")
            stats = await tool.db_stats()
            print(f"   Active Stocks: {stats['active_stocks']}")
            print(f"   Total Ratings: {stats['total_ratings']}")
            print(f"   Expert Ratings: {stats['expert_ratings']}")
            print(f"   Popular Ratings: {stats['popular_ratings']}")
            
            # 3. Stock Listing
            print("\n3. 📈 Recent Stocks")
            stocks_result = await tool.stocks_list(page=1, limit=3)
            for stock in stocks_result['stocks']:
                print(f"   {stock['symbol']}: {stock['name']} - ${stock['current_price']}")
            
            # 4. Direct Database Query
            print("\n4. 🗄️  Direct Database Access")
            recent_stocks = await tool.db_stocks(limit=3)
            for stock in recent_stocks:
                print(f"   {stock['symbol']}: {stock['name']} ({stock['exchange']})")
            
            # 5. Stock Creation Test
            print("\n5. ➕ Create New Stock Test")
            try:
                new_stock = await tool.stocks_create(
                    symbol="TEST", 
                    name="Test Company",
                    exchange="NASDAQ",
                    current_price=100.0
                )
                print(f"   ✅ Created: {new_stock['symbol']} - {new_stock['name']}")
                
                # Get the stock we just created
                retrieved = await tool.stocks_get_by_symbol("TEST")
                print(f"   ✅ Retrieved: {retrieved['symbol']} - ${retrieved['current_price']}")
                
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Stock TEST already exists")
                    # Try to get existing stock
                    existing = await tool.stocks_get_by_symbol("TEST")
                    print(f"   📊 Existing: {existing['symbol']} - ${existing['current_price']}")
                else:
                    print(f"   ❌ Error: {e}")
            
            # 6. Price Update Test
            print("\n6. 💰 Price Update Test")
            try:
                updated = await tool.stocks_update_price("TEST", 105.0)
                print(f"   ✅ Updated price for {updated['symbol']}: ${updated['current_price']}")
            except Exception as e:
                print(f"   ❌ Price update error: {e}")
            
            # 7. Rating Aggregation (if we have stocks with ratings)
            print("\n7. 📊 Rating Aggregation Example")
            try:
                # Get a stock with ratings
                stocks_with_ratings = await tool.db_query("""
                    SELECT DISTINCT s.id, s.symbol 
                    FROM stocks s 
                    JOIN ratings r ON s.id = r.stock_id 
                    LIMIT 1
                """)
                
                if stocks_with_ratings:
                    stock = stocks_with_ratings[0]
                    aggregation = await tool.ratings_aggregation(stock['id'])
                    print(f"   Stock: {stock['symbol']}")
                    print(f"   Total Ratings: {aggregation['total_ratings']}")
                    print(f"   Overall Score: {float(aggregation['overall_score']):.2f}")
                    print(f"   Recommendation: {aggregation['overall_recommendation']}")
                else:
                    print("   No stocks with ratings found")
                    
            except Exception as e:
                print(f"   ❌ Aggregation error: {e}")
            
            # 8. Custom Query Example
            print("\n8. 🔍 Custom Database Query")
            try:
                top_stocks = await tool.db_query("""
                    SELECT symbol, name, current_price, sector
                    FROM stocks 
                    WHERE current_price IS NOT NULL 
                    ORDER BY current_price DESC 
                    LIMIT 3
                """)
                
                print("   Top stocks by price:")
                for stock in top_stocks:
                    print(f"   {stock['symbol']}: ${stock['current_price']} ({stock['sector']})")
                    
            except Exception as e:
                print(f"   ❌ Query error: {e}")
                
            print("\n✅ Demo completed successfully!")
            print("\nTo run individual commands, use:")
            print("   python api_query_tool.py health")
            print("   python api_query_tool.py stocks list")
            print("   python api_query_tool.py db stats")
            print("   python api_query_tool.py --help")
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())