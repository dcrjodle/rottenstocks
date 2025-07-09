from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import asyncio
from database import (
    init_database, 
    seed_data, 
    get_all_stocks, 
    get_stock_by_id, 
    get_stock_by_symbol,
    create_stock, 
    update_stock, 
    delete_stock
)
from stock_sync_service import stock_sync_service

app = FastAPI(title="Stock Management API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class StockCreate(BaseModel):
    symbol: str
    name: str
    price: float

class StockUpdate(BaseModel):
    symbol: str
    name: str
    price: float

class Stock(BaseModel):
    id: int
    symbol: str
    name: str
    price: float
    change_amount: Optional[float] = 0
    change_percent: Optional[str] = '0%'
    volume: Optional[int] = 0
    market_cap: Optional[str] = ''
    pe_ratio: Optional[str] = ''
    sector: Optional[str] = ''
    industry: Optional[str] = ''
    last_updated: Optional[str] = ''

class StockAddRequest(BaseModel):
    symbol: str

class StockSearchRequest(BaseModel):
    keywords: str

class StockSearchResult(BaseModel):
    symbol: str
    name: str
    type: str
    region: str
    market_open: str
    market_close: str
    timezone: str
    currency: str
    match_score: float

@app.on_event("startup")
async def startup_event():
    """Initialize database and seed data on startup."""
    init_database()
    seed_data()

@app.get("/", response_model=dict)
async def root():
    """Root endpoint for health check."""
    return {"message": "Stock Management API is running"}

@app.get("/stocks", response_model=List[Stock])
async def get_stocks():
    """Get all stocks."""
    stocks = get_all_stocks()
    return stocks

@app.get("/stocks/{stock_id}", response_model=Stock)
async def get_stock(stock_id: int):
    """Get a single stock by ID."""
    stock = get_stock_by_id(stock_id)
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock

@app.post("/stocks", response_model=Stock)
async def create_new_stock(stock: StockCreate):
    """Create a new stock."""
    try:
        new_stock = create_stock(stock.symbol, stock.name, stock.price)
        return new_stock
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/stocks/{stock_id}", response_model=Stock)
async def update_existing_stock(stock_id: int, stock: StockUpdate):
    """Update an existing stock."""
    updated_stock = update_stock(stock_id, stock.symbol, stock.name, stock.price)
    if updated_stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return updated_stock

@app.get("/stocks/symbol/{symbol}", response_model=Stock)
async def get_stock_by_symbol_endpoint(symbol: str):
    """Get a stock by symbol."""
    stock = get_stock_by_symbol(symbol.upper())
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock

@app.post("/stocks/add", response_model=Stock)
async def add_stock_from_alpha_vantage(request: StockAddRequest):
    """Add a stock from AlphaVantage API."""
    try:
        stock = await stock_sync_service.add_and_sync_stock(request.symbol.upper())
        return stock
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/stocks/search", response_model=List[StockSearchResult])
async def search_stocks(request: StockSearchRequest):
    """Search for stocks using AlphaVantage API."""
    try:
        results = await stock_sync_service.search_and_add_stock(request.keywords)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/stocks/sync", response_model=dict)
async def sync_all_stocks(background_tasks: BackgroundTasks):
    """Trigger background sync of all stocks."""
    if stock_sync_service.is_syncing:
        raise HTTPException(status_code=429, detail="Sync already in progress")
    
    # Skip overview data for bulk syncs to avoid double API calls
    background_tasks.add_task(stock_sync_service.sync_all_stocks, include_overview=False)
    return {"message": "Sync started in background"}

@app.get("/stocks/sync/status", response_model=dict)
async def get_sync_status():
    """Get current sync status."""
    return stock_sync_service.get_sync_status()

@app.post("/stocks/sync/now", response_model=dict)
async def sync_all_stocks_now():
    """Immediately sync all stocks (not background) - returns results."""
    if stock_sync_service.is_syncing:
        raise HTTPException(status_code=429, detail="Sync already in progress")
    
    try:
        # Skip overview data for bulk syncs to be fast
        synced_stocks = await stock_sync_service.sync_all_stocks(include_overview=False)
        return {
            "message": "Sync completed successfully",
            "synced_count": len(synced_stocks),
            "stocks": synced_stocks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.post("/stocks/sync/refresh", response_model=dict)
async def refresh_database():
    """Refresh entire database with latest AlphaVantage data."""
    if stock_sync_service.is_syncing:
        raise HTTPException(status_code=429, detail="Sync already in progress")
    
    try:
        # Get all current stocks
        all_stocks = get_all_stocks()
        
        if not all_stocks:
            return {"message": "No stocks to sync", "synced_count": 0}
        
        # Sync each stock with full data
        synced_stocks = []
        failed_stocks = []
        
        print(f"Refreshing {len(all_stocks)} stocks...")
        
        for stock in all_stocks:
            try:
                print(f"Syncing {stock['symbol']}...")
                synced_stock = await stock_sync_service.sync_stock_data(
                    stock['symbol'], 
                    include_overview=True
                )
                synced_stocks.append(synced_stock)
                print(f"✓ {stock['symbol']} synced successfully")
            except Exception as e:
                error_msg = str(e)
                failed_stocks.append({"symbol": stock['symbol'], "error": error_msg})
                print(f"✗ {stock['symbol']} failed: {error_msg}")
        
        # Return success even if some stocks failed
        success_message = f"Database refresh completed"
        if len(synced_stocks) > 0:
            success_message += f" - {len(synced_stocks)} stocks synced successfully"
        if len(failed_stocks) > 0:
            success_message += f", {len(failed_stocks)} stocks failed"
        
        # Only return error if ALL stocks failed AND there are stocks to sync
        if len(failed_stocks) == len(all_stocks) and len(all_stocks) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"All stocks failed to sync. First error: {failed_stocks[0]['error']}"
            )
        
        return {
            "message": success_message,
            "synced_count": len(synced_stocks),
            "failed_count": len(failed_stocks),
            "synced_stocks": synced_stocks,
            "failed_stocks": failed_stocks,
            "total_stocks": len(all_stocks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database refresh failed: {str(e)}")

@app.delete("/stocks/invalid", response_model=dict)
async def cleanup_invalid_stocks():
    """Remove stocks with invalid symbols or zero prices."""
    try:
        all_stocks = get_all_stocks()
        
        if not all_stocks:
            return {"message": "No stocks to check", "removed_count": 0}
        
        # Find invalid stocks
        invalid_stocks = []
        for stock in all_stocks:
            # Check for invalid symbols or zero prices
            if (not stock['symbol'] or 
                len(stock['symbol']) > 10 or 
                stock['price'] <= 0 or 
                stock['symbol'] in ['REFRESH', 'TEST', 'INVALID']):
                invalid_stocks.append(stock)
        
        if not invalid_stocks:
            return {"message": "No invalid stocks found", "removed_count": 0}
        
        # Remove invalid stocks
        removed_count = 0
        for stock in invalid_stocks:
            if delete_stock(stock['id']):
                removed_count += 1
        
        return {
            "message": f"Removed {removed_count} invalid stocks",
            "removed_count": removed_count,
            "removed_stocks": [{"symbol": s['symbol'], "name": s['name']} for s in invalid_stocks]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@app.post("/stocks/sync/{symbol}", response_model=Stock)
async def sync_single_stock(symbol: str):
    """Sync a single stock from AlphaVantage."""
    try:
        stock = await stock_sync_service.sync_stock_data(symbol.upper(), include_overview=True)
        return stock
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/stocks/{stock_id}", response_model=dict)
async def delete_existing_stock(stock_id: int):
    """Delete a stock by ID."""
    success = delete_stock(stock_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"message": "Stock deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)