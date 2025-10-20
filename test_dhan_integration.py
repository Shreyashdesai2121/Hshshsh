#!/usr/bin/env python3
"""
Test script for Dhan API integration.
Run this to test your Dhan API credentials and endpoints.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

# Configuration - Update these with your actual values
DHAN_API_KEY = "your_dhan_api_key_here"
DHAN_API_SECRET = "your_dhan_api_secret_here"
DHAN_BASE_URL = "https://api.dhan.co"  # Update with actual Dhan base URL
ACCESS_TOKEN = "your_dhan_access_token_here"  # Your access token

async def test_dhan_authentication():
    """Test Dhan authentication."""
    print("🔐 Testing Dhan Authentication...")
    
    # Update this URL with actual Dhan auth endpoint
    auth_url = f"{DHAN_BASE_URL}/auth/login"  # This might be different
    
    auth_data = {
        "api_key": DHAN_API_KEY,
        "api_secret": DHAN_API_SECRET
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json=auth_data, headers=headers) as response:
                print(f"Auth Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ Authentication successful!")
                    print(f"Response: {json.dumps(data, indent=2)}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Authentication failed: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

async def test_dhan_market_data():
    """Test Dhan market data."""
    print("\n📊 Testing Dhan Market Data...")
    
    # Update this URL with actual Dhan market data endpoint
    market_url = f"{DHAN_BASE_URL}/market/quote"  # This might be different
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test with NIFTY50
    params = {"symbol": "NIFTY50"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(market_url, headers=headers, params=params) as response:
                print(f"Market Data Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ Market data successful!")
                    print(f"Response: {json.dumps(data, indent=2)}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Market data failed: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Market data error: {e}")
        return False

async def test_dhan_historical_data():
    """Test Dhan historical data."""
    print("\n📈 Testing Dhan Historical Data...")
    
    # Update this URL with actual Dhan historical data endpoint
    historical_url = f"{DHAN_BASE_URL}/market/historical"  # This might be different
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test with NIFTY50 for last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    params = {
        "symbol": "NIFTY50",
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "interval": "1D"  # Daily data
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(historical_url, headers=headers, params=params) as response:
                print(f"Historical Data Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ Historical data successful!")
                    print(f"Response: {json.dumps(data, indent=2)}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Historical data failed: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Historical data error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing Dhan API Integration")
    print("=" * 50)
    
    # Test authentication
    auth_success = await test_dhan_authentication()
    
    if auth_success:
        # Test market data
        market_success = await test_dhan_market_data()
        
        # Test historical data
        historical_success = await test_dhan_historical_data()
        
        print("\n" + "=" * 50)
        print("📋 Test Results:")
        print(f"Authentication: {'✅' if auth_success else '❌'}")
        print(f"Market Data: {'✅' if market_success else '❌'}")
        print(f"Historical Data: {'✅' if historical_success else '❌'}")
        
        if auth_success and market_success:
            print("\n🎉 Dhan integration is working! You can now run the trading system.")
        else:
            print("\n⚠️  Some tests failed. Check the Dhan API documentation for correct endpoints.")
    else:
        print("\n❌ Authentication failed. Please check your API credentials and endpoints.")

if __name__ == "__main__":
    print("⚠️  IMPORTANT: Update the configuration variables at the top of this file!")
    print("1. Set your DHAN_API_KEY")
    print("2. Set your DHAN_API_SECRET") 
    print("3. Set your ACCESS_TOKEN")
    print("4. Set the correct DHAN_BASE_URL")
    print("5. Update the endpoint URLs based on Dhan documentation")
    print()
    
    asyncio.run(main())