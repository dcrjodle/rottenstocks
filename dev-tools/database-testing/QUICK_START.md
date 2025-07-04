# Quick Start Guide - Database Testing Environment

This guide gets you up and running with the RottenStocks database testing tools in 5 minutes.

## 🚀 Quick Setup (30 seconds)

1. **Start database services:**
   ```bash
   cd /path/to/rottenstocks
   docker-compose up -d
   ```

2. **Activate Python environment:**
   ```bash
   cd backend
   source venv/bin/activate
   ```

3. **Test database connection:**
   ```bash
   cd ../dev-tools/database-testing
   python health_check.py --quick
   ```

## 🎯 Common Tasks (2 minutes)

### Generate Test Data
```bash
# Generate 10 stocks with ratings and social posts
python generate_samples.py --stocks 10 --experts 5 --posts-per-stock 20
```

### Interactive Database Testing
```bash
# Launch interactive shell
python interactive_db.py

# In the shell, try:
await db.get_database_stats()
await db.find_stock('AAPL')
await db.create_stock('NVDA', 'NVIDIA Corp', 'NASDAQ')
```

### Quick Data Analysis
```bash
# Get top-rated stocks
python query_builder.py --template top_rated_stocks

# Market overview
python query_builder.py --template market_overview

# Export sentiment analysis to CSV
python query_builder.py --template sentiment_analysis --export sentiment.csv
```

### Database Health Check
```bash
# Quick health check
python health_check.py --quick

# Full comprehensive check
python health_check.py --full

# Performance benchmark
python health_check.py --benchmark
```

## 🎮 Easy Mode - Menu Launcher

For a user-friendly menu interface:

```bash
python launcher.py
```

This gives you a simple menu to access all tools without remembering commands.

## 📊 Example Workflow (2 minutes)

Here's a complete workflow to test the database:

```bash
# 1. Check if everything is working
python health_check.py --quick

# 2. Generate sample data (if database is empty)
python generate_samples.py --stocks 5 --experts 3

# 3. Analyze the data
python query_builder.py --template top_rated_stocks
python query_builder.py --template sentiment_analysis

# 4. Interactive exploration
python interactive_db.py
# Then in the shell:
# await db.get_database_stats()
# stocks = await db.find_stocks_by_sector('Technology')
# exit()
```

## 🔧 Troubleshooting

**Database connection error?**
```bash
docker-compose ps  # Check if services are running
docker-compose up -d  # Start services if needed
```

**Import errors?**
```bash
# Make sure you're in the right directory
cd backend
source venv/bin/activate
cd ../dev-tools/database-testing
```

**No data in database?**
```bash
python generate_samples.py  # Generate sample data
```

## 📋 Tool Reference

| Tool | Purpose | Quick Command |
|------|---------|---------------|
| `health_check.py` | Verify database health | `python health_check.py --quick` |
| `generate_samples.py` | Create test data | `python generate_samples.py` |
| `interactive_db.py` | Interactive shell | `python interactive_db.py` |
| `query_builder.py` | Pre-built queries | `python query_builder.py --template market_overview` |
| `launcher.py` | Menu interface | `python launcher.py` |

## 🎉 You're Ready!

That's it! You now have a full database testing environment. Use these tools to:

- ✅ Test new database features
- ✅ Generate realistic test data  
- ✅ Analyze data with pre-built queries
- ✅ Debug database issues
- ✅ Verify database health
- ✅ Benchmark performance

For detailed documentation, see `README.md` in this directory.

Happy testing! 🧪