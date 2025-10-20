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
DHAN_API_KEY = "your_dhan_api_key_here"  # This will be used as access token
DHAN_API_SECRET = "your_dhan_api_secret_here"  # Not used in v2 API
DHAN_BASE_URL = "https://api.dhan.co/v2"  # Dhan API v2 base URL
ACCESS_TOKEN = "your_dhan_access_token_here"  # Your access token (same as API key)

async def test_dhan_authentication():
    """Test Dhan authentication."""
    print("🔐 Testing Dhan Authentication...")
    
    # Dhan v2 API doesn't have separate auth endpoint
    # We test by calling fund limit API
    fund_url = f"{DHAN_BASE_URL}/fundlimit"
    
    headers = {
        "access-token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(fund_url, headers=headers) as response:
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
    
    # Use Dhan's intraday charts API for NIFTY50
    market_url = f"{DHAN_BASE_URL}/charts/intraday"
    
    headers = {
        "access-token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Test with NIFTY50 index data
    chart_data = {
        "securityId": "99992000000000",  # NIFTY50 security ID
        "exchangeSegment": "IDX_I",
        "instrument": "INDEX",
        "interval": "1",
        "fromDate": datetime.now().strftime("%Y-%m-%d"),
        "toDate": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(market_url, json=chart_data, headers=headers) as response:
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
    
    # Use Dhan's historical charts API
    historical_url = f"{DHAN_BASE_URL}/charts/historical"
    
    headers = {
        "access-token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Test with NIFTY50 for last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    chart_data = {
        "securityId": "99992000000000",  # NIFTY50 security ID
        "exchangeSegment": "IDX_I",
        "instrument": "INDEX",
        "fromDate": start_date.strftime("%Y-%m-%d"),
        "toDate": end_date.strftime("%Y-%m-%d")
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(historical_url, json=chart_data, headers=headers) as response:
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