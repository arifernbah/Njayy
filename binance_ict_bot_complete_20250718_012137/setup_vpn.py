#!/usr/bin/env python3
"""
VPN Setup Script for Binance Access
This script helps set up VPN to access Binance when blocked in your region
"""

import os
import subprocess
import requests
import time
from datetime import datetime

def check_binance_access():
    """Check if Binance is accessible"""
    try:
        response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=10)
        if response.status_code == 200:
            print("✅ Binance is accessible")
            return True
        else:
            print(f"❌ Binance access blocked: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Binance access error: {e}")
        return False

def install_openvpn():
    """Install OpenVPN if not present"""
    try:
        # Check if openvpn is installed
        result = subprocess.run(['which', 'openvpn'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ OpenVPN is already installed")
            return True
        
        print("📦 Installing OpenVPN...")
        # Try to install openvpn
        subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'openvpn'], check=True)
        print("✅ OpenVPN installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install OpenVPN: {e}")
        return False
    except Exception as e:
        print(f"❌ Installation error: {e}")
        return False

def download_vpn_config():
    """Download VPN configuration from VPNGate"""
    try:
        print("🌐 Downloading VPN configuration...")
        
        # Download VPNGate server list
        url = "https://www.vpngate.net/api/iphone/"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            print("❌ Failed to download VPN server list")
            return False
        
        # Parse CSV data
        lines = response.text.split('\n')
        if len(lines) < 3:
            print("❌ Invalid VPN server list")
            return False
        
        # Find Singapore servers (good for Binance)
        sg_servers = []
        for line in lines[2:]:  # Skip header lines
            if line.strip() and ',' in line:
                parts = line.split(',')
                if len(parts) >= 15 and parts[5] == 'Singapore':
                    sg_servers.append({
                        'hostname': parts[0],
                        'ip': parts[1],
                        'score': int(parts[2]) if parts[2].isdigit() else 0,
                        'ping': int(parts[3]) if parts[3].isdigit() else 9999,
                        'speed': int(parts[4]) if parts[4].isdigit() else 0,
                        'country': parts[5],
                        'config': parts[14]
                    })
        
        if not sg_servers:
            print("❌ No Singapore VPN servers found")
            return False
        
        # Sort by speed and select the best one
        sg_servers.sort(key=lambda x: x['speed'], reverse=True)
        best_server = sg_servers[0]
        
        print(f"✅ Selected server: {best_server['hostname']} ({best_server['country']})")
        print(f"   Speed: {best_server['speed']} Mbps, Ping: {best_server['ping']} ms")
        
        # Save VPN config
        import base64
        config_data = base64.b64decode(best_server['config'])
        
        with open('vpn_config.ovpn', 'wb') as f:
            f.write(config_data)
        
        print("✅ VPN configuration saved as vpn_config.ovpn")
        return True
        
    except Exception as e:
        print(f"❌ Failed to download VPN config: {e}")
        return False

def connect_vpn():
    """Connect to VPN"""
    try:
        if not os.path.exists('vpn_config.ovpn'):
            print("❌ VPN configuration file not found")
            return False
        
        print("🔌 Connecting to VPN...")
        
        # Start OpenVPN in background
        process = subprocess.Popen([
            'sudo', 'openvpn', '--config', 'vpn_config.ovpn',
            '--daemon', '--log', 'vpn.log'
        ])
        
        # Wait for connection
        time.sleep(10)
        
        # Check if connection is successful
        if process.poll() is None:
            print("✅ VPN connection established")
            return True
        else:
            print("❌ VPN connection failed")
            return False
            
    except Exception as e:
        print(f"❌ VPN connection error: {e}")
        return False

def disconnect_vpn():
    """Disconnect VPN"""
    try:
        subprocess.run(['sudo', 'pkill', 'openvpn'], check=True)
        print("✅ VPN disconnected")
        return True
    except Exception as e:
        print(f"❌ VPN disconnect error: {e}")
        return False

def main():
    """Main function"""
    print("🚀 VPN Setup for Binance Access")
    print("=" * 40)
    
    # Check current access
    print("\n🔍 Checking current Binance access...")
    if check_binance_access():
        print("✅ No VPN needed - Binance is accessible")
        return
    
    print("\n❌ Binance is blocked. Setting up VPN...")
    
    # Install OpenVPN
    if not install_openvpn():
        print("❌ Cannot proceed without OpenVPN")
        return
    
    # Download VPN config
    if not download_vpn_config():
        print("❌ Failed to download VPN configuration")
        return
    
    # Connect to VPN
    if not connect_vpn():
        print("❌ Failed to connect to VPN")
        return
    
    # Test access again
    print("\n🔍 Testing Binance access with VPN...")
    time.sleep(5)
    
    if check_binance_access():
        print("🎉 Success! Binance is now accessible via VPN")
        print("\n📝 Next steps:")
        print("1. Run: python3 test_connection.py")
        print("2. If successful, run: python3 bot.py")
        print("3. To disconnect VPN later: sudo pkill openvpn")
    else:
        print("❌ VPN connection didn't resolve the issue")
        disconnect_vpn()

if __name__ == "__main__":
    main()