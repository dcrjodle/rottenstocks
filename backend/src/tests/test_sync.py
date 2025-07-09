"""
Test sync functionality with valid and invalid symbols
"""
import asyncio
import os
import sys
sys.path.append('/Users/joel.bystedt/rottenstocks/backend/src')
from services.stock_sync_service import StockSyncService

async def test_sync():
    # Set demo API key
    os.environ['ALPHA_VANTAGE_API_KEY'] = 'demo'
    
    service = StockSyncService()
    
    print("Testing valid symbol (IBM)...")
    try:
        result = await service.sync_stock_data('IBM', include_overview=True)
        print(f"✓ Success: {result['symbol']} - ${result['price']}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\nTesting invalid symbol (REFRESH)...")
    try:
        result = await service.sync_stock_data('REFRESH', include_overview=True)
        print(f"✓ Success: {result['symbol']} - ${result['price']}")
    except Exception as e:
        print(f"✓ Expected error: {e}")
    
    print("\nTesting invalid symbol (empty)...")
    try:
        result = await service.sync_stock_data('', include_overview=True)
        print(f"✓ Success: {result['symbol']} - ${result['price']}")
    except Exception as e:
        print(f"✓ Expected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sync())