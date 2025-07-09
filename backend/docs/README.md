# Stock Management Backend with AlphaVantage Integration

This backend provides a comprehensive stock management system with real-time data from AlphaVantage API.

## Features

- **Real-time Stock Data**: Fetch live stock quotes from AlphaVantage API
- **Stock Search**: Search for stocks by keywords
- **Company Overview**: Get detailed company information
- **Background Sync**: Automatically sync stock data in the background
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Error Handling**: Comprehensive error handling for API failures

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. AlphaVantage API Key

1. Sign up for a free API key at [AlphaVantage](https://www.alphavantage.co/support/#api-key)
2. Create a `.env` file in the backend directory:

```bash
cp .env.example .env
```

3. Add your API key to the `.env` file:

```
ALPHA_VANTAGE_API_KEY=your_actual_api_key_here
```

### 3. Run the Server

```bash
source venv/bin/activate
python main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Stock Management

- `GET /stocks` - Get all stocks
- `GET /stocks/{id}` - Get stock by ID
- `GET /stocks/symbol/{symbol}` - Get stock by symbol
- `POST /stocks` - Create new stock manually
- `PUT /stocks/{id}` - Update stock
- `DELETE /stocks/{id}` - Delete stock

### AlphaVantage Integration

- `POST /stocks/add` - Add stock from AlphaVantage API
  ```json
  {"symbol": "AAPL"}
  ```

- `POST /stocks/search` - Search stocks
  ```json
  {"keywords": "Apple"}
  ```

- `POST /stocks/sync` - Sync all stocks (background task)
- `POST /stocks/sync/{symbol}` - Sync single stock
- `GET /stocks/sync/status` - Get sync status

## Database Schema

The stocks table includes:

- `id` - Primary key
- `symbol` - Stock symbol (e.g., "AAPL")
- `name` - Company name
- `price` - Current price
- `change_amount` - Price change amount
- `change_percent` - Price change percentage
- `volume` - Trading volume
- `market_cap` - Market capitalization
- `pe_ratio` - Price-to-earnings ratio
- `sector` - Company sector
- `industry` - Company industry
- `last_updated` - Last update timestamp

## Rate Limiting

The AlphaVantage free tier allows:
- 5 requests per minute
- 500 requests per day

The service implements automatic rate limiting with 12-second delays between requests.

## Error Handling

The system handles:
- Network errors
- API rate limits
- Invalid symbols
- Missing API keys
- Database errors

## Testing

Run the integration test:

```bash
python test_integration.py
```

This uses the demo API key to test basic functionality.

## Production Considerations

1. **API Key Security**: Never commit your API key to version control
2. **Rate Limiting**: Monitor API usage to avoid exceeding limits
3. **Error Logging**: Implement proper logging for production
4. **Database Backups**: Regular backups of the SQLite database
5. **Monitoring**: Set up monitoring for API failures and sync status

## Troubleshooting

### Common Issues

1. **"API key required" error**: Check that your `.env` file exists and contains a valid API key
2. **Rate limit exceeded**: Wait for the rate limit to reset (1 minute)
3. **Invalid symbol**: Verify the stock symbol exists and is correctly formatted
4. **Database locked**: Ensure only one process is accessing the database at a time

### Debug Mode

Set environment variable for debug logging:

```bash
export LOG_LEVEL=DEBUG
```