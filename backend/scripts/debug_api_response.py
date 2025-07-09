"""
Debug Alpha Vantage API response to see what we're actually getting
"""
import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load from the parent directory .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def debug_api_response():
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    print(f"Using API key: {api_key[:10]}...{api_key[-4:] if api_key else 'None'}")
    
    if not api_key:
        print("❌ No API key found")
        return
    
    # Direct API call
    url = "https://www.alphavantage.co/query"
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': 'AAPL',
        'apikey': api_key
    }
    
    print(f"\n🔍 Making request to: {url}")
    print(f"📋 Parameters: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"\n📋 Raw JSON Response:")
            print(json.dumps(data, indent=2))
            
            # Check for specific keys
            print(f"\n🔍 Response Analysis:")
            print(f"  - Keys in response: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if 'Global Quote' in data:
                print(f"  - Global Quote found: {data['Global Quote']}")
            elif 'Error Message' in data:
                print(f"  - Error Message: {data['Error Message']}")
            elif 'Note' in data:
                print(f"  - Note (Rate limit?): {data['Note']}")
            else:
                print(f"  - Unexpected response structure")
                
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON:")
            print(response.text[:500])
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    debug_api_response()