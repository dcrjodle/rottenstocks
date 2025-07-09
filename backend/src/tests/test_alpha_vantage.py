"""
Test Alpha Vantage API directly to see what's happening
"""
import os
import sys
sys.path.append('/Users/joel.bystedt/rottenstocks/backend/src')
from services.alphavantage_service import AlphaVantageService

def test_alpha_vantage():
    os.environ['ALPHA_VANTAGE_API_KEY'] = 'demo'
    
    service = AlphaVantageService()
    
    print("Testing Alpha Vantage API...")
    
    # Test with IBM (demo key default)
    try:
        print("\n1. Testing IBM (demo default):")
        quote = service.get_stock_quote('IBM')
        print(f"   ✓ Success: {quote}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test with AAPL
    try:
        print("\n2. Testing AAPL:")
        quote = service.get_stock_quote('AAPL')
        print(f"   ✓ Success: {quote}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test with MSFT
    try:
        print("\n3. Testing MSFT:")
        quote = service.get_stock_quote('MSFT')
        print(f"   ✓ Success: {quote}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

if __name__ == "__main__":
    test_alpha_vantage()