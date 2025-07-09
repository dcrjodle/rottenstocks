"""
Database migration script to update existing database schema for AlphaVantage integration
"""

import sqlite3
import os
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

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_database():
    """Migrate existing database to new schema."""
    print("Starting database migration...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if migration is needed
        if check_column_exists(cursor, 'stocks', 'symbol'):
            print("Database already migrated. No action needed.")
            return
        
        print("Migrating database schema...")
        
        # Create new table with updated schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks_new (
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
        
        # Check if old table exists and has data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stocks'")
        old_table_exists = cursor.fetchone() is not None
        
        if old_table_exists:
            # Copy data from old table to new table
            cursor.execute("SELECT * FROM stocks")
            old_data = cursor.fetchall()
            
            print(f"Migrating {len(old_data)} existing records...")
            
            for row in old_data:
                # Generate symbol from name (fallback)
                symbol = row['name'].upper().replace(' ', '').replace('.', '').replace(',', '')[:10]
                if symbol == 'APPLE INC':
                    symbol = 'AAPL'
                elif symbol == 'MICROSOFT CORPORATION':
                    symbol = 'MSFT'
                elif symbol == 'NVIDIA CORPORATION':
                    symbol = 'NVDA'
                
                cursor.execute('''
                    INSERT INTO stocks_new (id, symbol, name, price, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (row['id'], symbol, row['name'], row['price']))
            
            # Drop old table
            cursor.execute("DROP TABLE stocks")
        
        # Rename new table to stocks
        cursor.execute("ALTER TABLE stocks_new RENAME TO stocks")
        
        conn.commit()
        print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()