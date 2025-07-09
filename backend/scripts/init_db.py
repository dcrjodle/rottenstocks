#!/usr/bin/env python3
"""Database initialization script for the stock management system."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from models.database import init_database, seed_data

def main():
    """Initialize the database and seed with initial data."""
    print("Initializing database...")
    init_database()
    print("Database initialized successfully!")
    
    print("Seeding database with initial stock data...")
    seed_data()
    print("Database seeded successfully!")
    
    print("Setup complete. Database is ready to use.")

if __name__ == "__main__":
    main()