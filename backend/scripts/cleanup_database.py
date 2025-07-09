"""
Clean up duplicate entries in the database
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

def cleanup_database():
    """Remove duplicate entries and keep only the proper symbols."""
    print("Cleaning up database...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get all stocks
        cursor.execute("SELECT * FROM stocks ORDER BY id")
        all_stocks = cursor.fetchall()
        
        print(f"Found {len(all_stocks)} stocks")
        
        # Keep only the proper symbols (AAPL, MSFT, NVDA)
        proper_symbols = ['AAPL', 'MSFT', 'NVDA']
        
        # Delete all records first
        cursor.execute("DELETE FROM stocks")
        
        # Insert only the correct ones
        stocks_to_insert = [
            {"symbol": "AAPL", "name": "Apple Inc.", "price": 189.25},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 339.12},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "price": 432.67}
        ]
        
        for stock in stocks_to_insert:
            cursor.execute("""
                INSERT INTO stocks (symbol, name, price, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (stock["symbol"], stock["name"], stock["price"]))
        
        conn.commit()
        print("Database cleaned up successfully!")
        
        # Verify cleanup
        cursor.execute("SELECT * FROM stocks")
        final_stocks = cursor.fetchall()
        print(f"Final database has {len(final_stocks)} stocks:")
        for stock in final_stocks:
            print(f"  - {stock['symbol']}: {stock['name']}")

if __name__ == "__main__":
    cleanup_database()