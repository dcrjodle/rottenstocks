"""
Test script for AlphaVantage integration
"""
import os
import sys
sys.path.append('/Users/joel.bystedt/rottenstocks/backend/src')
from services.alphavantage_service import AlphaVantageService
from models.database import init_database

def test_alpha_vantage_integration():
    """Test AlphaVantage integration with demo key"""
    print("Testing AlphaVantage integration...")
    
    # Set demo API key for testing
    os.environ['ALPHA_VANTAGE_API_KEY'] = 'demo'
    
    try:
        # Initialize database
        init_database()
        print("✓ Database initialized")
        
        # Create AlphaVantage service
        av_service = AlphaVantageService()
        print("✓ AlphaVantage service created")
        
        # Test stock quote (using demo key with IBM)
        print("\nTesting stock quote for IBM...")
        quote = av_service.get_stock_quote('IBM')
        print(f"✓ Stock quote retrieved: {quote['symbol']} - ${quote['price']}")
        
        # Test stock search
        print("\nTesting stock search for 'Microsoft'...")
        search_results = av_service.search_stocks('Microsoft')
        print(f"✓ Search results: {len(search_results)} stocks found")
        if search_results:
            print(f"  First result: {search_results[0]['symbol']} - {search_results[0]['name']}")
        
        print("\n✓ All tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_alpha_vantage_integration()