#!/usr/bin/env python3
"""
Simple Telegram Test
"""

import os
import sys

def test_telegram_config():
    """Test Telegram configuration from .env file"""
    print("🔍 Testing Telegram Configuration...")
    
    # Read .env file manually
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print("❌ .env file not found")
        return False
    
    # Check Telegram settings
    enable_telegram = env_vars.get('ENABLE_TELEGRAM', 'False').lower() == 'true'
    telegram_token = env_vars.get('TELEGRAM_TOKEN', '')
    telegram_chat_id = env_vars.get('TELEGRAM_CHAT_ID', '')
    
    print(f"ENABLE_TELEGRAM: {enable_telegram}")
    print(f"TELEGRAM_TOKEN: {'SET' if telegram_token and telegram_token != 'your_telegram_bot_token_here' else 'NOT SET'}")
    print(f"TELEGRAM_CHAT_ID: {'SET' if telegram_chat_id and telegram_chat_id != 'your_telegram_chat_id_here' else 'NOT SET'}")
    
    if not enable_telegram:
        print("❌ Telegram is disabled in .env")
        return False
        
    if not telegram_token or telegram_token == 'your_telegram_bot_token_here':
        print("❌ Telegram token not set or still using placeholder")
        return False
        
    if not telegram_chat_id or telegram_chat_id == 'your_telegram_chat_id_here':
        print("❌ Telegram chat ID not set or still using placeholder")
        return False
    
    print("✅ Telegram credentials found in .env")
    return True

def main():
    """Main test function"""
    print("🚀 Arif_Bot Telegram Configuration Test")
    print("=" * 50)
    
    success = test_telegram_config()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Configuration test PASSED")
        print("Telegram credentials are properly set")
        print("\n🔧 Next steps:")
        print("1. Make sure your bot token is valid")
        print("2. Make sure your chat ID is correct")
        print("3. Make sure bot is added to your chat")
        print("4. Restart bot to test connection")
    else:
        print("❌ Configuration test FAILED")
        print("\n🔧 To fix:")
        print("1. Edit .env file")
        print("2. Set TELEGRAM_TOKEN=your_actual_bot_token")
        print("3. Set TELEGRAM_CHAT_ID=your_actual_chat_id")
        print("4. Make sure ENABLE_TELEGRAM=True")
        print("5. Save .env file")
        print("6. Restart bot")
    
    return success

if __name__ == "__main__":
    main()