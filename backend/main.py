from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from database import (
    init_database, 
    seed_data, 
    get_all_stocks, 
    get_stock_by_id, 
    create_stock, 
    update_stock, 
    delete_stock
)

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
    name: str
    price: float

class StockUpdate(BaseModel):
    name: str
    price: float

class Stock(BaseModel):
    id: int
    name: str
    price: float

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
        new_stock = create_stock(stock.name, stock.price)
        return new_stock
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/stocks/{stock_id}", response_model=Stock)
async def update_existing_stock(stock_id: int, stock: StockUpdate):
    """Update an existing stock."""
    updated_stock = update_stock(stock_id, stock.name, stock.price)
    if updated_stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return updated_stock

@app.delete("/stocks/{stock_id}", response_model=dict)
async def delete_existing_stock(stock_id: int):
    """Delete a stock by ID."""
    success = delete_stock(stock_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"message": "Stock deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)