import sqlite3
import os
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

DATABASE_URL = "stocks.db"

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def init_database():
    """Initialize the database with stocks table."""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Create stocks table with AlphaVantage fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            change_amount REAL DEFAULT 0,
            change_percent TEXT DEFAULT '0%',
            volume INTEGER DEFAULT 0,
            market_cap TEXT DEFAULT '',
            pe_ratio TEXT DEFAULT '',
            sector TEXT DEFAULT '',
            industry TEXT DEFAULT '',
            last_updated TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if we need to migrate existing data
    if not check_column_exists(cursor, 'stocks', 'symbol'):
        print("Warning: Database schema is outdated. Please run 'python migrate_database.py'")
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    try:
        yield conn
    finally:
        conn.close()

def get_all_stocks() -> List[Dict[str, Any]]:
    """Get all stocks from database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, name, price, change_amount, change_percent, 
                   volume, market_cap, pe_ratio, sector, industry, last_updated
            FROM stocks
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_stock_by_id(stock_id: int) -> Optional[Dict[str, Any]]:
    """Get a single stock by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, name, price, change_amount, change_percent, 
                   volume, market_cap, pe_ratio, sector, industry, last_updated
            FROM stocks WHERE id = ?
        """, (stock_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_stock(symbol: str, name: str, price: float, **kwargs) -> Dict[str, Any]:
    """Create a new stock with AlphaVantage data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stocks (symbol, name, price, change_amount, change_percent, 
                               volume, market_cap, pe_ratio, sector, industry, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, name, price,
            kwargs.get('change_amount', 0),
            kwargs.get('change_percent', '0%'),
            kwargs.get('volume', 0),
            kwargs.get('market_cap', ''),
            kwargs.get('pe_ratio', ''),
            kwargs.get('sector', ''),
            kwargs.get('industry', ''),
            kwargs.get('last_updated', '')
        ))
        conn.commit()
        stock_id = cursor.lastrowid
        return get_stock_by_id(stock_id)

def update_stock(stock_id: int, symbol: str, name: str, price: float, **kwargs) -> Optional[Dict[str, Any]]:
    """Update an existing stock with AlphaVantage data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE stocks SET symbol = ?, name = ?, price = ?, change_amount = ?, 
                             change_percent = ?, volume = ?, market_cap = ?, 
                             pe_ratio = ?, sector = ?, industry = ?, last_updated = ?
            WHERE id = ?
        """, (
            symbol, name, price,
            kwargs.get('change_amount', 0),
            kwargs.get('change_percent', '0%'),
            kwargs.get('volume', 0),
            kwargs.get('market_cap', ''),
            kwargs.get('pe_ratio', ''),
            kwargs.get('sector', ''),
            kwargs.get('industry', ''),
            kwargs.get('last_updated', ''),
            stock_id
        ))
        conn.commit()
        if cursor.rowcount > 0:
            return get_stock_by_id(stock_id)
        return None

def delete_stock(stock_id: int) -> bool:
    """Delete a stock by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_stock_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Get a stock by symbol."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, name, price, change_amount, change_percent, 
                   volume, market_cap, pe_ratio, sector, industry, last_updated
            FROM stocks WHERE symbol = ?
        """, (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_or_update_stock_from_alpha_vantage(symbol: str, quote_data: Dict[str, Any], overview_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create or update a stock with AlphaVantage data."""
    existing_stock = get_stock_by_symbol(symbol)
    
    stock_data = {
        'change_amount': quote_data.get('change', 0),
        'change_percent': quote_data.get('change_percent', '0%'),
        'volume': quote_data.get('volume', 0),
        'last_updated': quote_data.get('updated_at', '')
    }
    
    if overview_data:
        stock_data.update({
            'market_cap': overview_data.get('market_cap', ''),
            'pe_ratio': overview_data.get('pe_ratio', ''),
            'sector': overview_data.get('sector', ''),
            'industry': overview_data.get('industry', '')
        })
    
    if existing_stock:
        return update_stock(
            existing_stock['id'],
            symbol,
            overview_data.get('name', existing_stock['name']) if overview_data else existing_stock['name'],
            quote_data.get('price', existing_stock['price']),
            **stock_data
        )
    else:
        return create_stock(
            symbol,
            overview_data.get('name', symbol) if overview_data else symbol,
            quote_data.get('price', 0),
            **stock_data
        )

def seed_data():
    """Seed the database with initial stock data."""
    stocks = [
        {"symbol": "AAPL", "name": "Apple Inc.", "price": 189.25},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 339.12},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "price": 432.67}
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if database already has data
        cursor.execute("SELECT COUNT(*) FROM stocks")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Database already has {count} stocks. Skipping seed data.")
            return
        
        print("Seeding database with initial stock data...")
        for stock in stocks:
            cursor.execute(
                "INSERT OR IGNORE INTO stocks (symbol, name, price, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (stock["symbol"], stock["name"], stock["price"])
            )
        conn.commit()
        print("Database seeded successfully!")