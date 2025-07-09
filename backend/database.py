import sqlite3
import os
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

DATABASE_URL = "stocks.db"

def init_database():
    """Initialize the database with stocks table."""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Create stocks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL
        )
    ''')
    
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
        cursor.execute("SELECT id, name, price FROM stocks")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_stock_by_id(stock_id: int) -> Optional[Dict[str, Any]]:
    """Get a single stock by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM stocks WHERE id = ?", (stock_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_stock(name: str, price: float) -> Dict[str, Any]:
    """Create a new stock."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO stocks (name, price) VALUES (?, ?)", (name, price))
        conn.commit()
        stock_id = cursor.lastrowid
        return {"id": stock_id, "name": name, "price": price}

def update_stock(stock_id: int, name: str, price: float) -> Optional[Dict[str, Any]]:
    """Update an existing stock."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE stocks SET name = ?, price = ? WHERE id = ?", (name, price, stock_id))
        conn.commit()
        if cursor.rowcount > 0:
            return {"id": stock_id, "name": name, "price": price}
        return None

def delete_stock(stock_id: int) -> bool:
    """Delete a stock by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))
        conn.commit()
        return cursor.rowcount > 0

def seed_data():
    """Seed the database with initial stock data."""
    stocks = [
        {"name": "Apple Inc.", "price": 189.25},
        {"name": "Microsoft Corporation", "price": 339.12},
        {"name": "NVIDIA Corporation", "price": 432.67}
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for stock in stocks:
            cursor.execute(
                "INSERT OR IGNORE INTO stocks (name, price) VALUES (?, ?)",
                (stock["name"], stock["price"])
            )
        conn.commit()