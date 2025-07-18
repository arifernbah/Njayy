#!/usr/bin/env python3
"""
Alternative Solution for HTTP 451 Error
This script provides alternative methods to access Binance when blocked
"""

import os
import subprocess
import requests
import time
from datetime import datetime

def test_different_dns():
    """Test with different DNS servers"""
    print("🔧 Testing with different DNS servers...")
    
    dns_servers = [
        "8.8.8.8",      # Google DNS
        "1.1.1.1",      # Cloudflare DNS
        "208.67.222.222", # OpenDNS
        "9.9.9.9",      # Quad9 DNS
    ]
    
    for dns in dns_servers:
        try:
            print(f"Testing with DNS: {dns}")
            
            # Set DNS temporarily
            subprocess.run(['sudo', 'systemd-resolve', '--set-dns=' + dns], 
                         capture_output=True)
            
            # Test Binance access
            response = requests.get('https://fapi.binance.com/fapi/v1/ping', 
                                  timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Success with DNS: {dns}")
                return True
            else:
                print(f"❌ Failed with DNS: {dns} (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ Error with DNS {dns}: {e}")
    
    return False

def test_proxy_servers():
    """Test with different proxy servers"""
    print("\n🌐 Testing with proxy servers...")
    
    proxies = [
        "https://api.binance.com",  # Try different Binance endpoints
        "https://testnet.binancefuture.com",
    ]
    
    for proxy_url in proxies:
        try:
            print(f"Testing endpoint: {proxy_url}")
            
            response = requests.get(f"{proxy_url}/fapi/v1/ping", timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Success with endpoint: {proxy_url}")
                return proxy_url
            else:
                print(f"❌ Failed with endpoint: {proxy_url} (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ Error with endpoint {proxy_url}: {e}")
    
    return None

def setup_alternative_endpoints():
    """Set up alternative Binance endpoints"""
    print("\n🔧 Setting up alternative endpoints...")
    
    # Create a modified config that uses alternative endpoints
    config_content = """
# Alternative Binance endpoints for blocked regions
ALTERNATIVE_ENDPOINTS = [
    "https://api.binance.com",
    "https://testnet.binancefuture.com",
    "https://fapi.binance.com",
]

# Use these endpoints when main ones fail
def get_working_endpoint():
    for endpoint in ALTERNATIVE_ENDPOINTS:
        try:
            response = requests.get(f"{endpoint}/fapi/v1/ping", timeout=5)
            if response.status_code == 200:
                return endpoint
        except:
            continue
    return None
"""
    
    with open('alternative_config.py', 'w') as f:
        f.write(config_content)
    
    print("✅ Alternative config created")

def check_network_status():
    """Check network connectivity and status"""
    print("\n🌐 Checking network status...")
    
    # Test basic internet connectivity
    try:
        response = requests.get('https://www.google.com', timeout=5)
        print("✅ Internet connectivity: OK")
    except:
        print("❌ Internet connectivity: Failed")
        return False
    
    # Test DNS resolution
    try:
        import socket
        socket.gethostbyname('fapi.binance.com')
        print("✅ DNS resolution: OK")
    except:
        print("❌ DNS resolution: Failed")
        return False
    
    # Test specific Binance endpoints
    endpoints = [
        'fapi.binance.com',
        'api.binance.com',
        'testnet.binancefuture.com'
    ]
    
    for endpoint in endpoints:
        try:
            socket.gethostbyname(endpoint)
            print(f"✅ {endpoint}: Resolvable")
        except:
            print(f"❌ {endpoint}: Not resolvable")
    
    return True

def main():
    """Main function"""
    print("🚀 Alternative Solutions for HTTP 451 Error")
    print("=" * 50)
    
    # Check network status
    if not check_network_status():
        print("❌ Network issues detected")
        return
    
    # Test different DNS servers
    if test_different_dns():
        print("🎉 DNS change resolved the issue!")
        print("📝 You can now run your bot normally")
        return
    
    # Test proxy servers
    working_endpoint = test_proxy_servers()
    if working_endpoint:
        print(f"🎉 Found working endpoint: {working_endpoint}")
        print("📝 Update your bot config to use this endpoint")
        return
    
    # Set up alternative endpoints
    setup_alternative_endpoints()
    
    print("\n📋 Summary of solutions tried:")
    print("1. ✅ DNS server changes")
    print("2. ✅ Alternative endpoints")
    print("3. ✅ Network diagnostics")
    
    print("\n🔧 Next steps:")
    print("1. Try running: python3 setup_vpn.py")
    print("2. Or manually configure a VPN")
    print("3. Check if your ISP is blocking Binance")
    print("4. Consider using a different network")

if __name__ == "__main__":
    main()