"""
Test refresh endpoint
"""
import asyncio
import os
from main import refresh_database

async def test_refresh():
    os.environ['ALPHA_VANTAGE_API_KEY'] = 'demo'
    
    print("Testing refresh endpoint...")
    try:
        result = await refresh_database()
        print("✓ Refresh successful:")
        print(f"  Synced: {result['synced_count']}")
        print(f"  Failed: {result['failed_count']}")
        if result['failed_stocks']:
            print("  Failed stocks:")
            for failed in result['failed_stocks']:
                print(f"    - {failed['symbol']}: {failed['error']}")
    except Exception as e:
        print(f"✗ Refresh failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_refresh())