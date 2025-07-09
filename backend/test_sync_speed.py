"""
Test sync speed optimization
"""
import time
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from stock_sync_service import StockSyncService

async def test_sync_speed():
    print("🚀 Testing Sync Speed Optimization")
    print("="*50)
    
    service = StockSyncService()
    
    # Test 1: Single stock sync
    print("\n1. Single Stock Sync:")
    start_time = time.time()
    try:
        result = await service.sync_stock_data('AAPL', include_overview=False)
        elapsed = time.time() - start_time
        print(f"   ✅ AAPL sync: {elapsed:.2f}s - ${result['price']}")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ AAPL sync failed: {elapsed:.2f}s - {e}")
    
    # Test 2: Bulk sync without overview
    print("\n2. Bulk Sync (no overview):")
    start_time = time.time()
    try:
        results = await service.sync_all_stocks(include_overview=False)
        elapsed = time.time() - start_time
        print(f"   ✅ Synced {len(results)} stocks in {elapsed:.2f}s")
        print(f"   Average: {elapsed/len(results):.2f}s per stock")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Bulk sync failed: {elapsed:.2f}s - {e}")
    
    # Test 3: Single stock with overview
    print("\n3. Single Stock with Overview:")
    start_time = time.time()
    try:
        result = await service.sync_stock_data('MSFT', include_overview=True)
        elapsed = time.time() - start_time
        print(f"   ✅ MSFT sync with overview: {elapsed:.2f}s")
        print(f"   Sector: {result.get('sector', 'N/A')}, PE: {result.get('pe_ratio', 'N/A')}")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ MSFT sync failed: {elapsed:.2f}s - {e}")

if __name__ == "__main__":
    asyncio.run(test_sync_speed())