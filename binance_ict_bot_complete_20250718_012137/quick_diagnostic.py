#!/usr/bin/env python3
"""
Quick Diagnostic - Check what changed
"""

import requests
import time
from datetime import datetime

def check_binance_status():
    """Check current Binance status"""
    print("🔍 Checking Binance status...")
    
    endpoints = [
        "https://fapi.binance.com/fapi/v1/ping",
        "https://fapi.binance.com/fapi/v1/time",
        "https://fapi.binance.com/fapi/v1/exchangeInfo",
        "https://api.binance.com/api/v3/ping",
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing: {endpoint}")
            response = requests.get(endpoint, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ OK")
            elif response.status_code == 451:
                print("❌ BLOCKED (HTTP 451)")
            else:
                print(f"❌ ERROR: {response.status_code}")
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
        print()

def check_network_info():
    """Check network information"""
    print("🌐 Checking network info...")
    
    try:
        # Check current IP
        ip_response = requests.get('https://api.ipify.org', timeout=5)
        print(f"Current IP: {ip_response.text}")
    except:
        print("Could not get IP")
    
    try:
        # Check DNS resolution
        import socket
        binance_ip = socket.gethostbyname('fapi.binance.com')
        print(f"Binance IP: {binance_ip}")
    except:
        print("Could not resolve Binance IP")

def check_rate_limits():
    """Check if we're rate limited"""
    print("⏱️ Checking rate limits...")
    
    try:
        # Make multiple requests to test rate limiting
        for i in range(5):
            response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=5)
            print(f"Request {i+1}: {response.status_code}")
            if response.status_code == 429:
                print("⚠️ Rate limited!")
                break
            time.sleep(1)
    except Exception as e:
        print(f"Rate limit test error: {e}")

def check_binance_status_page():
    """Check Binance status page"""
    print("📊 Checking Binance status page...")
    
    try:
        # Check if Binance is having issues
        response = requests.get('https://status.binance.com', timeout=10)
        if response.status_code == 200:
            print("✅ Binance status page accessible")
            if "maintenance" in response.text.lower():
                print("⚠️ Maintenance detected")
        else:
            print(f"❌ Status page: {response.status_code}")
    except Exception as e:
        print(f"❌ Status page error: {e}")

def main():
    """Main diagnostic function"""
    print("🚀 Quick Diagnostic - What Changed?")
    print("=" * 40)
    print(f"Time: {datetime.now()}")
    print()
    
    # Run all checks
    check_binance_status()
    check_network_info()
    check_rate_limits()
    check_binance_status_page()
    
    print("\n📋 Possible Solutions:")
    print("1. Wait 10-15 minutes (rate limit)")
    print("2. Check Binance status page")
    print("3. Try different network")
    print("4. Restart Web Horizon")
    print("5. Check if IP changed")

if __name__ == "__main__":
    main()