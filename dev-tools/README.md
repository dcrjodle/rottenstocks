# RottenStocks Dev Tools

Development tools for testing and verification of the RottenStocks backend API with external integrations.

## Quick Start

```bash
# Start all services and activate environment
cd backend && source venv/bin/activate && cd .. && docker-compose up -d postgres redis && cd backend && uvicorn app.main:app --reload --port 8000 &

# Wait for services to start, then test Alpha Vantage integration
sleep 5 && cd dev-tools && python api_query_tool.py alpha-vantage quote AAPL && python api_query_tool.py health
```

## Manual Testing Guide

### 1. Start All Services

```bash
# Start database and Redis
docker-compose up -d postgres redis

# Activate backend environment and start API server
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

### 2. Verify External API Integration

Test Alpha Vantage integration to ensure external data is working:

```bash
cd dev-tools

# Test Alpha Vantage API directly
python api_query_tool.py alpha-vantage quote AAPL
python api_query_tool.py alpha-vantage quote GOOGL
python api_query_tool.py alpha-vantage quote TSLA

# Test Alpha Vantage company overview
python api_query_tool.py alpha-vantage overview AAPL
```

### 3. Verify Database Has Real Data

```bash
# Check if stocks exist in database
python api_query_tool.py db stocks --limit 10

# Create sample stocks with real data from Alpha Vantage
python api_query_tool.py sample

# Verify database statistics
python api_query_tool.py db stats
```

### 4. Test Core API Endpoints

```bash
# Test health endpoint
python api_query_tool.py health

# Test stock endpoints
python api_query_tool.py stocks list
python api_query_tool.py stocks get AAPL

# Test if API can fetch and return real stock data
curl http://localhost:8000/api/v1/stocks/symbol/AAPL/quote
curl http://localhost:8000/api/v1/stocks/symbol/GOOGL/quote
```

### 5. End-to-End Alpha Vantage Validation

```bash
# Complete workflow to verify Alpha Vantage integration
python api_query_tool.py alpha-vantage quote AAPL && \
python api_query_tool.py stocks create --symbol AAPL --name "Apple Inc." --exchange NASDAQ --sector Technology --current-price 150.0 && \
python api_query_tool.py stocks get AAPL && \
curl -s http://localhost:8000/api/v1/stocks/symbol/AAPL/quote | jq .
```

## API Testing Commands

### Stock Operations
```bash
# List all stocks
python api_query_tool.py stocks list

# Search for specific stocks
python api_query_tool.py stocks list --search Apple

# Get stock by symbol
python api_query_tool.py stocks get AAPL

# Create new stock
python api_query_tool.py stocks create --symbol MSFT --name "Microsoft Corporation" --exchange NASDAQ --sector Technology --current-price 300.0

# Update stock price
python api_query_tool.py stocks price AAPL 155.0
```

### Rating Operations
```bash
# List all ratings
python api_query_tool.py ratings list

# Create expert rating
python api_query_tool.py ratings create --stock-id 1 --type expert --score 4.5 --recommendation buy --confidence 0.8

# Get rating aggregation
python api_query_tool.py ratings aggregation 1
```

### Database Operations
```bash
# Get database statistics
python api_query_tool.py db stats

# Query stocks directly from database
python api_query_tool.py db stocks --limit 10

# Execute custom SQL
python api_query_tool.py db query "SELECT symbol, name, current_price FROM stocks WHERE is_active = true"
```

### External API Testing
```bash
# Test Alpha Vantage quote data
python api_query_tool.py alpha-vantage quote AAPL

# Test Alpha Vantage company overview
python api_query_tool.py alpha-vantage overview AAPL

# Test multiple symbols
python api_query_tool.py alpha-vantage quote AAPL && \
python api_query_tool.py alpha-vantage quote GOOGL && \
python api_query_tool.py alpha-vantage quote TSLA
```

## One-Command Testing Workflows

### Full Integration Test
```bash
# Test everything: services, external APIs, database, and core endpoints
python api_query_tool.py health && \
python api_query_tool.py alpha-vantage quote AAPL && \
python api_query_tool.py sample && \
python api_query_tool.py stocks list && \
python api_query_tool.py db stats && \
curl -s http://localhost:8000/api/v1/stocks/symbol/AAPL/quote | jq .
```

### Quick Alpha Vantage Validation
```bash
# Verify Alpha Vantage integration is working
python api_query_tool.py alpha-vantage quote AAPL && \
python api_query_tool.py alpha-vantage overview AAPL && \
echo "Alpha Vantage integration verified!"
```

### Database Verification
```bash
# Check database health and sample data
python api_query_tool.py db stats && \
python api_query_tool.py db stocks --limit 5 && \
python api_query_tool.py db ratings --limit 5
```

## Alpha Vantage Synchronization and Verification

The new background task system automatically syncs stock data from Alpha Vantage every 60 minutes (respecting the 25 requests/day limit). Here's how to manually sync and verify the data:

### 1. Manual Database Synchronization with Alpha Vantage

```bash
# Trigger immediate stock synchronization from Alpha Vantage to database
curl -X POST http://localhost:8000/api/v1/tasks/sync/stock

# Alternative: Seed test data with real Alpha Vantage data
curl -X POST "http://localhost:8000/api/v1/testing/seed-data?symbols=AAPL&symbols=GOOGL&symbols=MSFT&symbols=TSLA&symbols=AMZN"

# Force update existing stocks with fresh Alpha Vantage data
curl -X POST "http://localhost:8000/api/v1/testing/seed-data?symbols=AAPL&symbols=GOOGL&force_update=true"
```

### 2. Verify Database Contains Fresh Stock Data

```bash
# Check data freshness and see when stocks were last updated
curl http://localhost:8000/api/v1/testing/data-freshness | jq

# List all stocks in database with their current prices and update times
curl http://localhost:8000/api/v1/stocks/ | jq '.stocks[] | {symbol, name, current_price, last_updated}'

# Get specific stock data from database (not from Alpha Vantage)
curl http://localhost:8000/api/v1/stocks/symbol/AAPL | jq

# Check how many stocks need updating
curl http://localhost:8000/api/v1/tasks/sync/stock/status | jq
```

### 3. Comprehensive Sync Verification Workflow

```bash
# 1. Check current database state
echo "=== Current Database State ==="
curl -s http://localhost:8000/api/v1/testing/data-freshness | jq '.total_stocks, .updated_last_hour, .stale_stocks'

# 2. Trigger sync with Alpha Vantage
echo "=== Triggering Sync ==="
curl -X POST http://localhost:8000/api/v1/tasks/sync/stock

# 3. Wait a moment for sync to complete
sleep 3

# 4. Verify data was updated
echo "=== After Sync ==="
curl -s http://localhost:8000/api/v1/testing/data-freshness | jq '.total_stocks, .updated_last_hour, .stale_stocks'

# 5. Check specific stock data
echo "=== AAPL Stock Data ==="
curl -s http://localhost:8000/api/v1/stocks/symbol/AAPL | jq '{symbol, current_price, change, last_updated}'
```

### 4. Monitor Background Task System

```bash
# Check task scheduler status
curl http://localhost:8000/api/v1/tasks/ | jq

# View task execution statistics
curl http://localhost:8000/api/v1/tasks/stats | jq

# Check system health (includes API, database, and sync status)
curl http://localhost:8000/api/v1/testing/comprehensive | jq '.overall_health, .summary'

# Monitor Alpha Vantage API usage
curl http://localhost:8000/api/v1/tasks/sync/stock/status | jq '{requests_used_today, daily_limit, requests_remaining}'
```

### 5. Test End-to-End Data Flow

```bash
# Complete verification that data flows from Alpha Vantage → Database → API
echo "=== Testing Complete Data Flow ==="

# Step 1: Get current AAPL price from Alpha Vantage directly
echo "1. Direct Alpha Vantage API call:"
curl -X POST "http://localhost:8000/api/v1/testing/api/alpha-vantage?symbol=AAPL&test_type=quote" | jq '.sample_data.price'

# Step 2: Sync to database
echo "2. Syncing to database..."
curl -X POST "http://localhost:8000/api/v1/testing/seed-data?symbols=AAPL&force_update=true" > /dev/null

# Step 3: Verify database has the data
echo "3. Database now contains:"
curl -s http://localhost:8000/api/v1/stocks/symbol/AAPL | jq '{current_price, last_updated}'

# Step 4: Test frontend would get database data (fast response)
echo "4. API serving database data:"
curl -s http://localhost:8000/api/v1/stocks/symbol/AAPL | jq '.current_price'

echo "✅ Complete data flow verified!"
```

### 6. Troubleshooting Sync Issues

```bash
# Check if scheduler is running
curl http://localhost:8000/api/v1/tasks/health | jq '.scheduler_running'

# Check for sync errors
curl http://localhost:8000/api/v1/tasks/stats | jq '.stock_sync_stats'

# View recent task execution
curl http://localhost:8000/api/v1/tasks/ | jq '.tasks[] | select(.task_id=="stock_sync")'

# Test Alpha Vantage connectivity
curl -X POST "http://localhost:8000/api/v1/testing/api/alpha-vantage?symbol=AAPL&test_type=quote" | jq '.success'

# Check API rate limits
curl http://localhost:8000/api/v1/tasks/sync/stock/status | jq '{requests_used_today, daily_limit}'
```

### Key Differences: Database vs Direct API

```bash
# ⚡ FAST: Get data from database (cached, no external API call)
curl http://localhost:8000/api/v1/stocks/symbol/AAPL

# 🐌 SLOW: Get data directly from Alpha Vantage (live API call)
curl -X POST "http://localhost:8000/api/v1/testing/api/alpha-vantage?symbol=AAPL&test_type=quote"
```

The background sync system ensures your database always has fresh data while serving fast responses to users!

## Troubleshooting

### Services Not Starting
```bash
# Check if ports are available
lsof -i :8000  # API server
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Restart services
docker-compose down && docker-compose up -d postgres redis
```

### Alpha Vantage API Issues
```bash
# Test Alpha Vantage directly
python api_query_tool.py alpha-vantage quote AAPL

# Check if API key is configured
grep -r "ALPHA_VANTAGE_API_KEY" ../backend/.env
```

### Database Connection Issues
```bash
# Test database connection
python api_query_tool.py db stats

# Check database is running
docker-compose ps postgres
```

### API Endpoint Issues
```bash
# Test health endpoint
curl http://localhost:8000/health

# Check API logs
cd ../backend && tail -f logs/app.log
```

## Configuration

Default configuration:
- **API Base URL**: `http://localhost:8000/api/v1`
- **Database URL**: `postgresql://postgres:postgres@localhost:5432/rottenstocks`
- **Alpha Vantage API**: Configured via environment variables

## Dependencies

- **httpx**: Async HTTP client for API requests
- **asyncpg**: High-performance PostgreSQL adapter
- **rich**: Beautiful terminal formatting and tables