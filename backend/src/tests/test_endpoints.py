"""
Test all sync endpoints to show correct usage
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("🧪 Testing Sync Endpoints")
    print("="*50)
    
    # Test 1: Get current stocks
    print("\n1. GET /stocks - Current stocks in database:")
    try:
        response = requests.get(f"{BASE_URL}/stocks")
        if response.status_code == 200:
            stocks = response.json()
            for stock in stocks:
                print(f"   {stock['symbol']}: {stock['name']} - ${stock['price']}")
        else:
            print(f"   Error: {response.status_code}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    # Test 2: Sync single stock (valid symbol)
    print("\n2. POST /stocks/sync/AAPL - Sync single stock:")
    try:
        response = requests.post(f"{BASE_URL}/stocks/sync/AAPL")
        if response.status_code == 200:
            stock = response.json()
            print(f"   ✓ Success: {stock['symbol']} - ${stock['price']}")
        else:
            print(f"   ✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    # Test 3: Sync single stock (invalid symbol)
    print("\n3. POST /stocks/sync/REFRESH - Sync invalid symbol:")
    try:
        response = requests.post(f"{BASE_URL}/stocks/sync/REFRESH")
        if response.status_code == 200:
            print(f"   ✓ Success: {response.json()}")
        else:
            print(f"   ✗ Expected error: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    # Test 4: Refresh all stocks
    print("\n4. POST /stocks/sync/refresh - Refresh all stocks:")
    try:
        response = requests.post(f"{BASE_URL}/stocks/sync/refresh")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Success: Synced {result['synced_count']} stocks")
            if result['failed_count'] > 0:
                print(f"   ⚠️  Failed: {result['failed_count']} stocks")
        else:
            print(f"   ✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    print("\n" + "="*50)
    print("📋 Endpoint Summary:")
    print("   POST /stocks/sync/refresh    - Refresh ALL stocks")
    print("   POST /stocks/sync/{symbol}   - Sync ONE stock")
    print("   POST /stocks/add             - Add new stock")
    print("   GET  /stocks/sync/status     - Check sync status")

if __name__ == "__main__":
    test_endpoints()