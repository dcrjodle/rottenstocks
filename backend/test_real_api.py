"""
Test Alpha Vantage with real API key from .env file
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load from the parent directory .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from alphavantage_service import AlphaVantageService

def test_real_api():
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    print(f"Using API key: {api_key[:10]}...{api_key[-4:] if api_key else 'None'}")
    
    if not api_key:
        print("❌ No API key found in .env file")
        return
    
    service = AlphaVantageService()
    
    # Test various stocks
    test_symbols = ['AAPL', 'MSFT', 'NVDA', 'IBM', 'TSLA']
    
    for symbol in test_symbols:
        try:
            print(f"\n🧪 Testing {symbol}...")
            quote = service.get_stock_quote(symbol)
            print(f"✅ Success: {symbol} - ${quote['price']} ({quote['change_percent']})")
        except Exception as e:
            print(f"❌ Failed: {symbol} - {e}")

if __name__ == "__main__":
    test_real_api()