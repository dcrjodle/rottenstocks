# Database Testing Environment

This folder provides simple tools for developers to test and interact with the RottenStocks database.

## 🚀 Quick Start

1. **Start the database services:**
   ```bash
   cd /path/to/rottenstocks
   docker-compose up -d
   ```

2. **Activate the Python environment:**
   ```bash
   cd backend
   source venv/bin/activate
   ```

3. **Run the interactive database shell:**
   ```bash
   cd dev-tools/database-testing
   python interactive_db.py
   ```

## 🛠️ Available Tools

### 1. Interactive Database Shell (`interactive_db.py`)
**Best for:** Quick queries, testing relationships, exploring data

**Features:**
- Pre-loaded database session
- All models imported and ready to use
- Helper functions for common operations
- Tab completion and syntax highlighting

**Example Usage:**
```python
# Simple data access (no await needed - data is pre-loaded for performance)
stocks = get_stocks()
experts = get_experts()
ratings = get_ratings()
posts = get_posts()

# Loop through data
for stock in get_stocks():
    print(stock.symbol, stock.current_price)

# Filter data
apple_stocks = [s for s in get_stocks() if s.symbol == 'AAPL']
high_ratings = [r for r in get_ratings() if r.score >= 4.0]

# Access model properties and relationships
for rating in get_ratings():
    print(f"{rating.stock.symbol}: {rating.score}/5 by {rating.expert.name}")

# Note: Data is cached when shell starts. Restart to see latest changes.
```

### 2. Database Sample Data Generator (`generate_samples.py`)
**Best for:** Creating test data, populating development database

**Features:**
- Generates realistic sample data
- Configurable data volume
- Maintains referential integrity
- Includes various scenarios (bull/bear markets, different sentiments)

**Example Usage:**
```bash
# Generate 10 stocks with ratings and social posts
python generate_samples.py --stocks 10 --experts 5 --posts-per-stock 20

# Generate only social media data
python generate_samples.py --social-only --posts 100
```

### 3. Database Query Tool (`query_builder.py`)
**Best for:** Complex queries, data analysis, reporting

**Features:**
- Pre-built query templates
- SQL and SQLAlchemy query builder
- Export results to CSV/JSON
- Performance timing

**Example Usage:**
```bash
# Get top-rated stocks
python query_builder.py --template top_rated_stocks --limit 10

# Custom SQL query
python query_builder.py --sql "SELECT symbol, current_price FROM stocks WHERE sector = 'Technology'"

# Export to CSV
python query_builder.py --template stock_performance --export stocks_performance.csv
```

### 4. Database Health Checker (`health_check.py`)
**Best for:** Verifying database state, debugging issues

**Features:**
- Connection testing
- Data integrity checks
- Performance benchmarks
- Migration status verification

**Example Usage:**
```bash
# Full health check
python health_check.py --full

# Quick connection test
python health_check.py --quick

# Check specific table
python health_check.py --table stocks
```

## 📋 Common Use Cases

### Testing New Features
```bash
# 1. Generate test data
python generate_samples.py --stocks 5

# 2. Test your feature interactively
python interactive_db.py

# 3. Verify results
python health_check.py --table your_new_table
```

### Data Analysis
```bash
# Get market sentiment overview
python query_builder.py --template sentiment_analysis

# Export rating data for analysis
python query_builder.py --template expert_ratings --export ratings.csv
```

### Debugging Database Issues
```bash
# Check database health
python health_check.py --full

# Interactive debugging session
python interactive_db.py
# Then use: debug_relationships(), check_constraints(), etc.
```

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rottenstocks
DB_ECHO=true  # Enable SQL logging for debugging
```

### Custom Configuration
Edit `config.py` to customize:
- Default query limits
- Sample data parameters
- Export formats
- Logging levels

## 📚 API Reference

### Interactive Shell Functions

**Simple Data Access (No await needed):**
```python
# Basic data retrieval
get_stocks()          # Get all stocks
get_experts()         # Get all experts  
get_ratings()         # Get all ratings
get_posts()           # Get all social posts
query('SQL')          # Execute raw SQL queries

# Example filtering and access
stocks = get_stocks()
apple = [s for s in stocks if s.symbol == 'AAPL'][0]
tech_stocks = [s for s in stocks if s.sector == 'Technology']
high_ratings = [r for r in get_ratings() if r.score >= 4.0]
```

**Advanced Database Operations (Require await - use in async context):**
```python
# Stock operations
await db.create_stock(symbol, name, exchange, **kwargs)
await db.find_stock(symbol)
await db.find_stocks_by_sector(sector)
await db.update_stock_price(symbol, new_price)

# Expert operations
await db.create_expert(name, institution, **kwargs)
await db.verify_expert(expert_id)
await db.get_expert_ratings(expert_id)

# Rating operations
await db.create_rating(stock_symbol, expert_name, score, recommendation)
await db.get_recent_ratings(days=30)
await db.get_ratings_by_score(min_score=4.0)

# Social media operations
await db.create_social_post(stock_symbol, platform, content, **kwargs)
await db.analyze_sentiment(post_id)
await db.get_posts_by_sentiment(sentiment_type)

# Utility functions
await db.seed_sample_data()
await db.get_database_stats()
```

### Query Templates
```python
# Available in query_builder.py
templates = [
    'top_rated_stocks',
    'expert_performance',
    'sentiment_analysis', 
    'market_overview',
    'stock_performance',
    'social_media_trends',
    'rating_distribution'
]
```

## ⚠️ Safety Notes

- **Development Only:** These tools are for development/testing environments
- **Data Reset:** Some tools can delete data - use with caution
- **Performance:** Large data operations may take time
- **Backups:** Always backup before running destructive operations

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error:**
```bash
# Check if services are running
docker-compose ps

# Restart services
docker-compose down && docker-compose up -d
```

**Import Errors:**
```bash
# Make sure you're in the right directory and venv
cd backend && source venv/bin/activate
cd ../dev-tools/database-testing
```

**Permission Errors:**
```bash
# Check file permissions
chmod +x *.py
```

### Getting Help

1. Check the logs: `docker-compose logs postgres`
2. Run health check: `python health_check.py --full`
3. Check the main documentation: `../../docs/`
4. Ask in team chat with specific error messages

## 📝 Contributing

To add new testing tools:

1. Create your script in this directory
2. Follow the existing patterns (async/await, proper error handling)
3. Add documentation to this README
4. Test with sample data
5. Submit PR with examples

---

*Happy database testing! 🎉*