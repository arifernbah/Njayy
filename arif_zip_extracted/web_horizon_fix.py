#!/usr/bin/env python3
"""
Web Horizon Fix for HTTP 451 Error
This script provides solutions specifically for Web Horizon hosting
"""

import os
import requests
import time
import json
from datetime import datetime

def test_web_horizon_access():
    """Test what's accessible from Web Horizon"""
    print("🔍 Testing Web Horizon access to Binance...")
    
    # Test public endpoints
    public_endpoints = [
        "https://fapi.binance.com/fapi/v1/ping",
        "https://fapi.binance.com/fapi/v1/time",
        "https://fapi.binance.com/fapi/v1/exchangeInfo",
        "https://fapi.binance.com/fapi/v1/ticker/24hr",
    ]
    
    working_public = []
    for endpoint in public_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                working_public.append(endpoint)
                print(f"✅ {endpoint}")
            else:
                print(f"❌ {endpoint} - HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - {e}")
    
    # Test authenticated endpoints
    auth_endpoints = [
        "https://fapi.binance.com/fapi/v2/account",
        "https://fapi.binance.com/fapi/v2/balance",
    ]
    
    working_auth = []
    for endpoint in auth_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                working_auth.append(endpoint)
                print(f"✅ {endpoint}")
            else:
                print(f"❌ {endpoint} - HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - {e}")
    
    return working_public, working_auth

def create_web_horizon_config():
    """Create Web Horizon specific configuration"""
    print("\n🔧 Creating Web Horizon configuration...")
    
    config_content = """
# Web Horizon Configuration for HTTP 451 Error
# This config handles blocked authenticated endpoints

import os
import requests
import time
from datetime import datetime

class WebHorizonConfig:
    def __init__(self):
        self.public_working = True
        self.auth_blocked = True
        self.alternative_methods = []
        
    def test_connectivity(self):
        \"\"\"Test what's accessible from Web Horizon\"\"\"
        try:
            # Test public endpoint
            response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=5)
            if response.status_code == 200:
                print("✅ Public endpoints accessible")
                return True
            else:
                print(f"❌ Public endpoints blocked: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connectivity error: {e}")
            return False
    
    def get_working_endpoint(self):
        \"\"\"Get working endpoint for Web Horizon\"\"\"
        # Try main endpoint first
        try:
            response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=5)
            if response.status_code == 200:
                return "https://fapi.binance.com"
        except:
            pass
        
        # Fallback to testnet if main is blocked
        try:
            response = requests.get('https://testnet.binancefuture.com/fapi/v1/ping', timeout=5)
            if response.status_code == 200:
                print("⚠️ Using testnet endpoint (for testing only)")
                return "https://testnet.binancefuture.com"
        except:
            pass
        
        return None

# Global instance
web_horizon_config = WebHorizonConfig()
"""
    
    with open('web_horizon_config.py', 'w') as f:
        f.write(config_content)
    
    print("✅ Web Horizon config created")

def create_alternative_trader():
    """Create alternative trader for Web Horizon"""
    print("\n🔧 Creating alternative trader...")
    
    trader_content = """
# Alternative Trader for Web Horizon
# Handles HTTP 451 error for authenticated endpoints

import requests
import time
import json
from datetime import datetime

class WebHorizonTrader:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.binance.com"
        self.session = requests.Session()
        
    def get_public_data(self, endpoint):
        \"\"\"Get public data (should work)\"\"\"
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Public endpoint failed: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Public endpoint error: {e}")
            return None
    
    def get_account_balance(self):
        \"\"\"Get account balance with error handling\"\"\"
        try:
            # Try authenticated endpoint
            url = f"{self.base_url}/fapi/v2/balance"
            headers = {
                'X-MBX-APIKEY': self.api_key
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 451:
                print("⚠️ Authenticated endpoint blocked (HTTP 451)")
                print("📱 Please check balance manually in Binance app")
                return self._get_balance_fallback()
            else:
                print(f"❌ Balance check failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Balance check error: {e}")
            return None
    
    def _get_balance_fallback(self):
        \"\"\"Fallback method when balance endpoint is blocked\"\"\"
        print("📋 Balance check fallback:")
        print("1. Check balance in Binance mobile app")
        print("2. Use /balance command in Telegram")
        print("3. Monitor positions manually")
        return {"fallback": True, "message": "Check balance manually"}
    
    def place_order(self, symbol, side, quantity, order_type="MARKET"):
        \"\"\"Place order with error handling\"\"\"
        try:
            url = f"{self.base_url}/fapi/v1/order"
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity
            }
            headers = {
                'X-MBX-APIKEY': self.api_key
            }
            
            response = self.session.post(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 451:
                print("⚠️ Order placement blocked (HTTP 451)")
                print("📱 Please place orders manually in Binance app")
                return {"error": "HTTP 451", "message": "Place order manually"}
            else:
                print(f"❌ Order failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Order error: {e}")
            return None

# Usage example:
# trader = WebHorizonTrader(api_key, api_secret)
# balance = trader.get_account_balance()
"""
    
    with open('web_horizon_trader.py', 'w') as f:
        f.write(trader_content)
    
    print("✅ Alternative trader created")

def create_telegram_monitor():
    """Create Telegram monitoring for manual trading"""
    print("\n📱 Creating Telegram monitoring...")
    
    monitor_content = """
# Telegram Monitor for Manual Trading
# When automated trading is blocked, use manual trading with monitoring

import requests
import time
from datetime import datetime

class ManualTradingMonitor:
    def __init__(self, telegram_token, chat_id):
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{telegram_token}"
        
    def send_signal(self, signal_data):
        \"\"\"Send trading signal for manual execution\"\"\"
        message = f"""
MANUAL TRADING SIGNAL

PAIR: {signal_data.get('symbol', 'N/A')}
Time: {datetime.now().strftime('%H:%M UTC')}
Signal: {signal_data.get('signal', 'N/A')}
Entry: {signal_data.get('entry', 'N/A')}
SL: {signal_data.get('sl', 'N/A')}
TP1: {signal_data.get('tp1', 'N/A')}
TP2: {signal_data.get('tp2', 'N/A')}

MANUAL ACTION REQUIRED
Execute this trade in Binance app
"""
        
        self.send_message(message)
    
    def send_message(self, text):
        \"\"\"Send message to Telegram\"\"\"
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data, timeout=10)
            return response.json()
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            return None
    
    def send_balance_request(self):
        \"\"\"Request balance check\"\"\"
        message = """
BALANCE CHECK REQUEST

Please check your Binance balance and reply with:
- USDT Balance: XXX
- Available Margin: XXX
- Open Positions: XXX

This helps monitor your account status.
"""
        self.send_message(message)

# Usage:
# monitor = ManualTradingMonitor(telegram_token, chat_id)
# monitor.send_signal(signal_data)
"""
    
    with open('manual_monitor.py', 'w') as f:
        f.write(monitor_content)
    
    print("✅ Manual trading monitor created")

def main():
    """Main function"""
    print("🚀 Web Horizon Fix for HTTP 451 Error")
    print("=" * 50)
    
    # Test current access
    working_public, working_auth = test_web_horizon_access()
    
    print(f"\n📊 Results:")
    print(f"✅ Working public endpoints: {len(working_public)}")
    print(f"❌ Working auth endpoints: {len(working_auth)}")
    
    if len(working_public) > 0 and len(working_auth) == 0:
        print("\n🔧 Creating Web Horizon solutions...")
        
        # Create solutions
        create_web_horizon_config()
        create_alternative_trader()
        create_telegram_monitor()
        
        print("\n📋 Solutions created:")
        print("1. web_horizon_config.py - Configuration handler")
        print("2. web_horizon_trader.py - Alternative trader")
        print("3. manual_monitor.py - Manual trading monitor")
        
        print("\n📱 Next steps:")
        print("1. Use manual_monitor.py for signal alerts")
        print("2. Execute trades manually in Binance app")
        print("3. Monitor via Telegram commands")
        print("4. Consider VPS deployment for full automation")
        
    else:
        print("\n❌ No solutions available for current setup")
        print("💡 Consider VPS deployment instead")

if __name__ == "__main__":
    main()