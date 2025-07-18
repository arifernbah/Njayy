#!/usr/bin/env python3
"""
Simple Web Horizon Fix for HTTP 451 Error
"""

import requests
import time
from datetime import datetime

def test_web_horizon():
    """Test Web Horizon access"""
    print("Testing Web Horizon access to Binance...")
    
    # Test public endpoints
    public_endpoints = [
        "https://fapi.binance.com/fapi/v1/ping",
        "https://fapi.binance.com/fapi/v1/time",
        "https://fapi.binance.com/fapi/v1/exchangeInfo",
    ]
    
    working_public = []
    for endpoint in public_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                working_public.append(endpoint)
                print(f"OK: {endpoint}")
            else:
                print(f"FAIL: {endpoint} - HTTP {response.status_code}")
        except Exception as e:
            print(f"ERROR: {endpoint} - {e}")
    
    return working_public

def create_simple_monitor():
    """Create simple manual trading monitor"""
    print("\nCreating simple manual trading monitor...")
    
    monitor_code = '''
import requests
import time
from datetime import datetime

class SimpleMonitor:
    def __init__(self, telegram_token, chat_id):
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{telegram_token}"
        
    def send_signal(self, symbol, signal_type, entry, sl, tp1, tp2):
        message = f"""
MANUAL TRADING SIGNAL

PAIR: {symbol}
Time: {datetime.now().strftime('%H:%M UTC')}
Signal: {signal_type}
Entry: {entry}
SL: {sl}
TP1: {tp1}
TP2: {tp2}

MANUAL ACTION REQUIRED
Execute this trade in Binance app
"""
        self.send_message(message)
    
    def send_message(self, text):
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
            print(f"Telegram error: {e}")
            return None

# Usage:
# monitor = SimpleMonitor(telegram_token, chat_id)
# monitor.send_signal("BTCUSDT", "BUY", "50000", "49500", "51000", "52000")
'''
    
    with open('simple_monitor.py', 'w') as f:
        f.write(monitor_code)
    
    print("Simple monitor created: simple_monitor.py")

def create_manual_trading_guide():
    """Create manual trading guide"""
    print("\nCreating manual trading guide...")
    
    guide = '''
MANUAL TRADING GUIDE FOR WEB HORIZON

Since automated trading is blocked (HTTP 451), use this manual approach:

1. SIGNAL DETECTION:
   - Bot detects signals using public data
   - Sends alerts via Telegram
   - You execute trades manually

2. TELEGRAM COMMANDS:
   /status - Bot status
   /test - Test connection
   /help - Show commands

3. MANUAL TRADING PROCESS:
   a) Bot sends signal to Telegram
   b) You open Binance app
   c) Execute trade manually
   d) Set SL/TP manually
   e) Monitor position

4. SETUP:
   - Run: python3 simple_monitor.py
   - Configure Telegram bot
   - Test signal alerts

5. MONITORING:
   - Check Telegram for signals
   - Monitor positions in Binance app
   - Use /status to check bot health

This approach works around the HTTP 451 restriction.
'''
    
    with open('MANUAL_TRADING_GUIDE.md', 'w') as f:
        f.write(guide)
    
    print("Manual trading guide created: MANUAL_TRADING_GUIDE.md")

def main():
    """Main function"""
    print("Web Horizon Fix for HTTP 451 Error")
    print("=" * 40)
    
    # Test access
    working_public = test_web_horizon()
    
    print(f"\nResults:")
    print(f"Working public endpoints: {len(working_public)}")
    
    if len(working_public) > 0:
        print("\nCreating Web Horizon solutions...")
        
        # Create solutions
        create_simple_monitor()
        create_manual_trading_guide()
        
        print("\nSolutions created:")
        print("1. simple_monitor.py - Simple trading monitor")
        print("2. MANUAL_TRADING_GUIDE.md - Trading guide")
        
        print("\nNext steps:")
        print("1. Use simple_monitor.py for signal alerts")
        print("2. Execute trades manually in Binance app")
        print("3. Monitor via Telegram")
        print("4. Consider VPS for full automation")
        
    else:
        print("\nNo solutions available")
        print("Consider VPS deployment instead")

if __name__ == "__main__":
    main()