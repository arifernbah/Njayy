#!/usr/bin/env python3
"""
Quick Fix for HTTP 451 Error - Real Trading Access
This script tries multiple methods to access real Binance Futures
"""

import os
import subprocess
import requests
import time
import socket
from datetime import datetime

def test_binance_access():
    """Test if Binance is accessible"""
    try:
        response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=10)
        if response.status_code == 200:
            print("✅ Binance main endpoint accessible!")
            return True
        else:
            print(f"❌ Binance blocked: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Binance access error: {e}")
        return False

def try_dns_override():
    """Try DNS override method"""
    print("\n🔧 Trying DNS override...")
    
    # Try to resolve with different DNS
    dns_servers = [
        ("8.8.8.8", "Google DNS"),
        ("1.1.1.1", "Cloudflare DNS"),
        ("208.67.222.222", "OpenDNS"),
    ]
    
    for dns_ip, dns_name in dns_servers:
        try:
            print(f"Testing with {dns_name} ({dns_ip})...")
            
            # Create a custom resolver
            resolver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            resolver.settimeout(5)
            
            # Try to resolve fapi.binance.com
            try:
                ip = socket.gethostbyname('fapi.binance.com')
                print(f"✅ Resolved fapi.binance.com to {ip}")
                
                # Test direct IP access
                response = requests.get(f'https://{ip}/fapi/v1/ping', 
                                      timeout=10, 
                                      headers={'Host': 'fapi.binance.com'})
                
                if response.status_code == 200:
                    print(f"✅ Direct IP access works!")
                    return True
                else:
                    print(f"❌ Direct IP failed: HTTP {response.status_code}")
                    
            except socket.gaierror:
                print(f"❌ DNS resolution failed with {dns_name}")
                
        except Exception as e:
            print(f"❌ Error with {dns_name}: {e}")
    
    return False

def try_proxy_methods():
    """Try different proxy methods"""
    print("\n🌐 Trying proxy methods...")
    
    # Try different Binance endpoints
    endpoints = [
        "https://api.binance.com",
        "https://fapi.binance.com", 
        "https://dapi.binance.com",
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing endpoint: {endpoint}")
            response = requests.get(f"{endpoint}/fapi/v1/ping", timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Endpoint works: {endpoint}")
                return endpoint
            else:
                print(f"❌ Endpoint failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Endpoint error: {e}")
    
    return None

def setup_hosts_file():
    """Setup hosts file override"""
    print("\n📝 Setting up hosts file override...")
    
    try:
        # Get current hosts content
        with open('/etc/hosts', 'r') as f:
            hosts_content = f.read()
        
        # Check if Binance entries already exist
        if 'fapi.binance.com' in hosts_content:
            print("✅ Binance entries already in hosts file")
            return True
        
        # Add Binance entries
        binance_entries = """
# Binance Futures API
185.199.108.153 fapi.binance.com
185.199.109.153 fapi.binance.com
185.199.110.153 fapi.binance.com
185.199.111.153 fapi.binance.com
"""
        
        # Backup original hosts file
        subprocess.run(['sudo', 'cp', '/etc/hosts', '/etc/hosts.backup'])
        
        # Add new entries
        with open('/etc/hosts', 'a') as f:
            f.write(binance_entries)
        
        print("✅ Hosts file updated")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update hosts file: {e}")
        return False

def try_curl_proxy():
    """Try using curl with different options"""
    print("\n🔄 Trying curl with different options...")
    
    curl_options = [
        ["curl", "-I", "https://fapi.binance.com/fapi/v1/ping"],
        ["curl", "-I", "--resolve", "fapi.binance.com:443:185.199.108.153", "https://fapi.binance.com/fapi/v1/ping"],
        ["curl", "-I", "--connect-timeout", "10", "https://fapi.binance.com/fapi/v1/ping"],
    ]
    
    for options in curl_options:
        try:
            print(f"Trying: {' '.join(options)}")
            result = subprocess.run(options, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and "200" in result.stdout:
                print("✅ Curl method works!")
                return True
            else:
                print(f"❌ Curl failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Curl error: {e}")
    
    return False

def main():
    """Main function"""
    print("🚀 Quick Fix for HTTP 451 Error - Real Trading Access")
    print("=" * 60)
    
    # Test current access
    print("\n🔍 Testing current Binance access...")
    if test_binance_access():
        print("🎉 Binance is already accessible! You can trade real.")
        return
    
    print("\n❌ Binance is blocked. Trying solutions...")
    
    # Try DNS override
    if try_dns_override():
        print("🎉 DNS override worked!")
        if test_binance_access():
            print("✅ Binance now accessible via DNS override")
            return
    
    # Try proxy methods
    working_endpoint = try_proxy_methods()
    if working_endpoint:
        print(f"🎉 Found working endpoint: {working_endpoint}")
        print("📝 Update your bot config to use this endpoint")
        return
    
    # Try hosts file override
    if setup_hosts_file():
        print("🔄 Hosts file updated, testing access...")
        time.sleep(2)
        if test_binance_access():
            print("✅ Binance accessible via hosts file override")
            return
    
    # Try curl methods
    if try_curl_proxy():
        print("🎉 Curl method worked!")
        if test_binance_access():
            print("✅ Binance now accessible")
            return
    
    print("\n❌ All automatic methods failed.")
    print("\n📋 Manual solutions to try:")
    print("1. 🔧 Setup VPN manually (see manual_vpn_setup.md)")
    print("2. 🌐 Use mobile hotspot")
    print("3. 🏢 Try from different network")
    print("4. 📱 Use Binance mobile app")
    print("5. 💻 Try from different location")
    
    print("\n⚠️  IMPORTANT:")
    print("- Testnet is for testing only (no real money)")
    print("- For real trading, you need main Binance access")
    print("- Consider using a paid VPN service")

if __name__ == "__main__":
    main()