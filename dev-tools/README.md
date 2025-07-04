# RottenStocks Dev Tools

Development tools for testing and verification of the RottenStocks backend API.

## Setup

1. Use the backend's virtual environment (all dependencies are already installed):
```bash
cd ../backend
source venv/bin/activate
cd ../dev-tools
```

2. Ensure the backend is running:
```bash
cd ../backend
uvicorn app.main:app --reload
```

3. Ensure the database is running (via Docker):
```bash
cd ..
docker-compose up -d postgres redis
```

## API Query Tool

The `api_query_tool.py` provides a comprehensive interface for testing API endpoints and querying the database directly.

### Usage Examples

#### Health Check
```bash
python api_query_tool.py health
```

#### Stock Operations
```bash
# List stocks
python api_query_tool.py stocks list

# List stocks with pagination and search
python api_query_tool.py stocks list --page 2 --limit 5 --search Apple

# Create a new stock
python api_query_tool.py stocks create --symbol AAPL --name "Apple Inc." --exchange NASDAQ --sector Technology --current-price 150.0

# Get stock by symbol
python api_query_tool.py stocks get AAPL

# Update stock price
python api_query_tool.py stocks price AAPL 155.0

## Quick Demo

For a comprehensive demonstration of all features:
```bash
python quick_demo.py
```

This will run through all major functionality and show you what the tool can do.

#### Rating Operations
```bash
# List all ratings
python api_query_tool.py ratings list

# List ratings for a specific stock
python api_query_tool.py ratings list --stock-id <stock_id>

# Create a new rating
python api_query_tool.py ratings create --stock-id <stock_id> --type expert --score 4.5 --recommendation buy --confidence 0.8

# Get rating aggregation for a stock
python api_query_tool.py ratings aggregation <stock_id>
```

#### Database Operations
```bash
# Get stocks directly from database
python api_query_tool.py db stocks --limit 10

# Get ratings directly from database
python api_query_tool.py db ratings --limit 10

# Get database statistics
python api_query_tool.py db stats

# Execute custom SQL query
python api_query_tool.py db query "SELECT symbol, name, current_price FROM stocks WHERE is_active = true"
```

#### Sample Data Creation
```bash
# Create sample stocks and ratings for testing
python api_query_tool.py sample
```

## Features

### API Testing
- Complete CRUD operations for stocks and ratings
- Pagination and filtering support
- Error handling with detailed HTTP status codes
- JSON response formatting with syntax highlighting

### Database Access
- Direct database queries for verification
- Statistics and analytics queries
- Custom SQL execution
- Connection pooling for performance

### Data Display
- Rich tables for structured data
- JSON formatting with syntax highlighting
- Color-coded output for better readability
- Progress indicators and status messages

### Sample Data
- Automated creation of test stocks (AAPL, GOOGL, TSLA)
- Sample ratings for different types (expert, popular)
- Handles existing data gracefully
- Verification of created data

## Configuration

The tool uses the following default configuration:

- **API Base URL**: `http://localhost:8000/api/v1`
- **Database URL**: `postgresql://postgres:postgres@localhost:5432/rottenstocks`

These can be modified in the script if your setup differs.

## Workflow Examples

### Complete Testing Workflow
```bash
# 1. Check API health
python api_query_tool.py health

# 2. Create sample data
python api_query_tool.py sample

# 3. Verify stocks were created
python api_query_tool.py stocks list

# 4. Check database directly
python api_query_tool.py db stats

# 5. Test rating aggregation
python api_query_tool.py ratings aggregation <stock_id>

# 6. Test search functionality
python api_query_tool.py stocks list --search Apple
```

### Price Update Testing
```bash
# 1. Get current stock info
python api_query_tool.py stocks get AAPL

# 2. Update price
python api_query_tool.py stocks price AAPL 160.0

# 3. Verify update
python api_query_tool.py stocks get AAPL
```

### Rating Analysis
```bash
# 1. List all ratings
python api_query_tool.py ratings list

# 2. Get aggregation for specific stock
python api_query_tool.py ratings aggregation <stock_id>

# 3. Check database ratings
python api_query_tool.py db ratings
```

## Error Handling

The tool provides detailed error messages for:
- HTTP errors with status codes and response details
- Database connection issues
- Invalid parameters or missing data
- Network connectivity problems

## Dependencies

- **httpx**: Async HTTP client for API requests
- **asyncpg**: High-performance PostgreSQL adapter
- **rich**: Beautiful terminal formatting and tables

## Database Testing Tools

This directory also contains the comprehensive database testing tools from previous development. See `database-testing/` directory for:
- Interactive database shell
- Query builder utilities
- Health check scripts
- Sample data generators