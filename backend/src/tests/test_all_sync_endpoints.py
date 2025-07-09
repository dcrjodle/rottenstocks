"""
Test all sync endpoints with mock data
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_all_sync_endpoints():
    print("🧪 Testing All Sync Endpoints with Mock Data")
    print("="*60)
    
    # Test 1: Get current stocks
    print("\n1. GET /stocks - Current stocks:")
    try:
        response = requests.get(f"{BASE_URL}/stocks")
        if response.status_code == 200:
            stocks = response.json()
            print(f"   ✅ Found {len(stocks)} stocks:")
            for stock in stocks[:3]:  # Show first 3
                print(f"      - {stock['symbol']}: {stock['name']} - ${stock['price']}")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 2: Sync single stock
    print("\n2. POST /stocks/sync/AAPL - Sync single stock:")
    try:
        response = requests.post(f"{BASE_URL}/stocks/sync/AAPL")
        if response.status_code == 200:
            stock = response.json()
            print(f"   ✅ Success: {stock['symbol']} - ${stock['price']} ({stock.get('change_percent', 'N/A')})")
            print(f"      Volume: {stock.get('volume', 'N/A'):,}, Sector: {stock.get('sector', 'N/A')}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 3: Background sync
    print("\n3. POST /stocks/sync - Background sync:")
    try:
        response = requests.post(f"{BASE_URL}/stocks/sync")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result['message']}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 4: Immediate sync with results
    print("\n4. POST /stocks/sync/now - Immediate sync:")
    try:
        response = requests.post(f"{BASE_URL}/stocks/sync/now")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result['message']}")
            print(f"      Synced: {result['synced_count']} stocks")
            if result.get('stocks'):
                print(f"      Sample: {result['stocks'][0]['symbol']} - ${result['stocks'][0]['price']}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 5: Database refresh
    print("\n5. POST /stocks/sync/refresh - Database refresh:")
    try:
        response = requests.post(f"{BASE_URL}/stocks/sync/refresh")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result['message']}")
            print(f"      Total: {result['total_stocks']}, Synced: {result['synced_count']}, Failed: {result['failed_count']}")
            if result.get('synced_stocks'):
                print(f"      Sample synced stock: {result['synced_stocks'][0]['symbol']} - ${result['synced_stocks'][0]['price']}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 6: Sync status
    print("\n6. GET /stocks/sync/status - Sync status:")
    try:
        response = requests.get(f"{BASE_URL}/stocks/sync/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Success:")
            print(f"      Is syncing: {status['is_syncing']}")
            print(f"      Last sync: {status['last_sync_time']}")
            print(f"      Should sync: {status['should_sync']}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 7: Add new stock
    print("\n7. POST /stocks/add - Add new stock:")
    try:
        response = requests.post(
            f"{BASE_URL}/stocks/add",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"symbol": "AMZN"})
        )
        if response.status_code == 200:
            stock = response.json()
            print(f"   ✅ Success: Added {stock['symbol']} - {stock['name']} - ${stock['price']}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 8: Search stocks
    print("\n8. POST /stocks/search - Search stocks:")
    try:
        response = requests.post(
            f"{BASE_URL}/stocks/search",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"keywords": "Apple"})
        )
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Success: Found {len(results)} results")
            if results:
                print(f"      First result: {results[0]['symbol']} - {results[0]['name']}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    print("\n" + "="*60)
    print("🎉 All endpoint tests completed!")
    print("\n📋 Available Endpoints Summary:")
    print("   GET  /stocks                  - List all stocks")
    print("   POST /stocks/sync             - Background sync all")
    print("   POST /stocks/sync/now         - Immediate sync all")
    print("   POST /stocks/sync/refresh     - Refresh database")
    print("   POST /stocks/sync/{symbol}    - Sync single stock")
    print("   GET  /stocks/sync/status      - Check sync status")
    print("   POST /stocks/add              - Add new stock")
    print("   POST /stocks/search           - Search stocks")

if __name__ == "__main__":
    time.sleep(3)  # Wait for server to start
    test_all_sync_endpoints()