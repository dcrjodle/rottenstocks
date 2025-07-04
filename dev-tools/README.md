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