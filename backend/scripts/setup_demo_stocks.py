"""
Set up database with only symbols that work with Alpha Vantage demo key
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

def setup_demo_stocks():
    """Set up database with demo-compatible stocks."""
    print("Setting up database with demo-compatible stocks...")
    
    # Symbols that work with demo key
    demo_stocks = [
        {"symbol": "IBM", "name": "International Business Machines", "price": 290.42},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 496.62}
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing stocks
        cursor.execute("DELETE FROM stocks")
        
        # Add demo stocks
        for stock in demo_stocks:
            cursor.execute("""
                INSERT INTO stocks (symbol, name, price, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (stock["symbol"], stock["name"], stock["price"]))
        
        conn.commit()
        print(f"✓ Added {len(demo_stocks)} demo stocks")
        
        # Verify
        cursor.execute("SELECT * FROM stocks")
        final_stocks = cursor.fetchall()
        print(f"Final database has {len(final_stocks)} stocks:")
        for stock in final_stocks:
            print(f"  - {stock['symbol']}: {stock['name']}")

if __name__ == "__main__":
    setup_demo_stocks()