"""
Set up database with test stocks for mock API testing
"""
import sqlite3
from contextlib import contextmanager

DATABASE_URL = "stocks.db"

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def setup_test_stocks():
    """Set up database with test stocks."""
    print("Setting up database with test stocks...")
    
    # Test stocks with variety
    test_stocks = [
        {"symbol": "AAPL", "name": "Apple Inc.", "price": 195.89},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 378.85},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "price": 489.75},
        {"symbol": "TSLA", "name": "Tesla Inc.", "price": 248.42},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "price": 142.56}
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing stocks
        cursor.execute("DELETE FROM stocks")
        
        # Add test stocks
        for stock in test_stocks:
            cursor.execute("""
                INSERT INTO stocks (symbol, name, price, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (stock["symbol"], stock["name"], stock["price"]))
        
        conn.commit()
        print(f"✓ Added {len(test_stocks)} test stocks")
        
        # Verify
        cursor.execute("SELECT * FROM stocks")
        final_stocks = cursor.fetchall()
        print(f"Final database has {len(final_stocks)} stocks:")
        for stock in final_stocks:
            print(f"  - {stock['symbol']}: {stock['name']}")

if __name__ == "__main__":
    setup_test_stocks()