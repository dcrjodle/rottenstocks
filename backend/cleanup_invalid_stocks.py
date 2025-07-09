"""
Remove invalid stock entries from database
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

def cleanup_invalid_stocks():
    """Remove invalid stock entries."""
    print("Cleaning up invalid stocks...")
    
    # List of valid stock symbols to keep
    valid_symbols = ['AAPL', 'MSFT', 'NVDA', 'IBM']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get all stocks
        cursor.execute("SELECT * FROM stocks")
        all_stocks = cursor.fetchall()
        
        print(f"Found {len(all_stocks)} stocks in database:")
        for stock in all_stocks:
            print(f"  {stock['id']}: {stock['symbol']} - {stock['name']}")
        
        # Remove invalid stocks
        invalid_stocks = [stock for stock in all_stocks if stock['symbol'] not in valid_symbols]
        
        if invalid_stocks:
            print(f"\nRemoving {len(invalid_stocks)} invalid stocks:")
            for stock in invalid_stocks:
                print(f"  Removing: {stock['symbol']} - {stock['name']}")
                cursor.execute("DELETE FROM stocks WHERE id = ?", (stock['id'],))
            
            conn.commit()
            print("✓ Invalid stocks removed")
        else:
            print("✓ No invalid stocks found")
        
        # Show final state
        cursor.execute("SELECT * FROM stocks")
        final_stocks = cursor.fetchall()
        print(f"\nFinal database has {len(final_stocks)} stocks:")
        for stock in final_stocks:
            print(f"  {stock['id']}: {stock['symbol']} - {stock['name']}")

if __name__ == "__main__":
    cleanup_invalid_stocks()