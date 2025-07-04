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
# Create a new stock
stock = create_stock("NVDA", "NVIDIA Corporation", "NASDAQ")

# Find stocks by sector
tech_stocks = find_stocks_by_sector("Technology")

# Get recent ratings
recent_ratings = get_recent_ratings(days=7)
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
```python
# Stock operations
create_stock(symbol, name, exchange, **kwargs)
find_stock(symbol)
find_stocks_by_sector(sector)
update_stock_price(symbol, new_price)

# Expert operations
create_expert(name, institution, **kwargs)
verify_expert(expert_id)
get_expert_ratings(expert_id)

# Rating operations
create_rating(stock_symbol, expert_name, score, recommendation)
get_recent_ratings(days=30)
get_ratings_by_score(min_score=4.0)

# Social media operations
create_social_post(stock_symbol, platform, content, **kwargs)
analyze_sentiment(post_id)
get_posts_by_sentiment(sentiment_type)

# Utility functions
reset_database()  # WARNING: Deletes all data
seed_sample_data()
export_data(table_name, format='csv')
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