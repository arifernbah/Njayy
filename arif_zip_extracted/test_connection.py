#!/usr/bin/env python3
"""
Binance API Connection Test Script
This script helps diagnose connection issues with Binance API
"""

import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from binance.client import Client

def test_basic_connectivity():
    """Test basic connectivity to Binance"""
    print("🔍 Testing basic connectivity...")
    
    try:
        # Test 1: Public endpoint (no auth)
        response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=10)
        if response.status_code == 200:
            print("✅ Public endpoint test passed")
        else:
            print(f"❌ Public endpoint test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Public endpoint test failed: {e}")
        return False
    
    try:
        # Test 2: Server time
        response = requests.get('https://fapi.binance.com/fapi/v1/time', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'serverTime' in data:
                server_time = datetime.fromtimestamp(data['serverTime'] / 1000)
                print(f"✅ Server time test passed: {server_time}")
            else:
                print("❌ Server time test failed: Invalid response")
                return False
        else:
            print(f"❌ Server time test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server time test failed: {e}")
        return False
    
    return True

def test_api_credentials():
    """Test API credentials"""
    print("\n🔑 Testing API credentials...")
    
    load_dotenv()
    
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET')
    
    if not api_key or not api_secret:
        print("❌ API credentials not found in .env file")
        return False
    
    print("✅ API credentials found in .env file")
    
    try:
        client = Client(api_key, api_secret)
        
        # Test account balance
        balance = client.futures_account_balance()
        if isinstance(balance, list):
            usdt_balance = next((b for b in balance if b['asset'] == 'USDT'), None)
            if usdt_balance:
                print(f"✅ Account balance test passed: {usdt_balance['balance']} USDT")
            else:
                print("⚠️ Account balance test passed but no USDT balance found")
        else:
            print("❌ Account balance test failed: Invalid response format")
            return False
            
    except Exception as e:
        print(f"❌ API credentials test failed: {e}")
        return False
    
    return True

def test_specific_endpoints():
    """Test specific endpoints that might be causing issues"""
    print("\n🔧 Testing specific endpoints...")
    
    load_dotenv()
    client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET'))
    
    endpoints = [
        ('Exchange Info', client.futures_exchange_info),
        ('Position Info', client.futures_position_information),
        ('Account Balance', client.futures_account_balance),
        ('Open Orders', lambda: client.futures_get_open_orders()),
        ('24hr Ticker', lambda: client.futures_ticker(symbol='BTCUSDT')),
    ]
    
    for name, func in endpoints:
        try:
            print(f"Testing {name}...", end=" ")
            result = func()
            
            # Check for HTML response
            if isinstance(result, str) and ('<html>' in result.lower() or 'doctype' in result.lower()):
                print(f"❌ HTML error response received")
                print(f"Response preview: {result[:200]}...")
                return False
            else:
                print("✅ Passed")
                
        except Exception as e:
            print(f"❌ Failed: {e}")
            return False
    
    return True

def main():
    """Main test function"""
    print("🚀 Binance API Connection Test")
    print("=" * 40)
    
    # Test 1: Basic connectivity
    if not test_basic_connectivity():
        print("\n❌ Basic connectivity test failed. Check your internet connection.")
        return
    
    # Test 2: API credentials
    if not test_api_credentials():
        print("\n❌ API credentials test failed. Check your .env file.")
        return
    
    # Test 3: Specific endpoints
    if not test_specific_endpoints():
        print("\n❌ Specific endpoints test failed. There might be an issue with your API setup.")
        return
    
    print("\n🎉 All tests passed! Your Binance API connection is working correctly.")
    print("\nIf you're still getting HTML errors in the bot, try:")
    print("1. Restart the bot")
    print("2. Check if you're hitting rate limits")
    print("3. Use the /test command in Telegram")
    print("4. Check Binance server status")

if __name__ == "__main__":
    main()