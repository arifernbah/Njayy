#!/usr/bin/env python3
"""
Test Telegram Connection
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_telegram_connection():
    """Test Telegram bot connection and send test message"""
    try:
        # Import after loading env
        from core.config import config
        from integrations.telegram import telegram
        
        print("🔍 Testing Telegram Configuration...")
        print(f"ENABLE_TELEGRAM: {config.ENABLE_TELEGRAM}")
        print(f"TELEGRAM_TOKEN: {'SET' if config.TELEGRAM_TOKEN else 'NOT SET'}")
        print(f"TELEGRAM_CHAT_ID: {'SET' if config.TELEGRAM_CHAT_ID else 'NOT SET'}")
        
        if not config.ENABLE_TELEGRAM:
            print("❌ Telegram is disabled in config")
            return False
            
        if not config.TELEGRAM_TOKEN or config.TELEGRAM_TOKEN == 'your_telegram_bot_token_here':
            print("❌ Telegram token not set or still using placeholder")
            return False
            
        if not config.TELEGRAM_CHAT_ID or config.TELEGRAM_CHAT_ID == 'your_telegram_chat_id_here':
            print("❌ Telegram chat ID not set or still using placeholder")
            return False
        
        print("✅ Telegram credentials found")
        
        # Test connection
        print("🔗 Testing Telegram connection...")
        if telegram.test_connection():
            print("✅ Telegram connection successful")
            
            # Send test message
            print("📤 Sending test message...")
            test_msg = "🤖 Test message from Arif_Bot\n\nBot is working correctly! ✅"
            
            if telegram.send_message(test_msg):
                print("✅ Test message sent successfully!")
                return True
            else:
                print("❌ Failed to send test message")
                return False
        else:
            print("❌ Telegram connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Telegram: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Arif_Bot Telegram Test")
    print("=" * 40)
    
    success = test_telegram_connection()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Telegram test PASSED")
        print("Bot should be able to send notifications")
    else:
        print("❌ Telegram test FAILED")
        print("\n🔧 To fix:")
        print("1. Edit .env file")
        print("2. Set TELEGRAM_TOKEN=your_actual_bot_token")
        print("3. Set TELEGRAM_CHAT_ID=your_actual_chat_id")
        print("4. Make sure ENABLE_TELEGRAM=True")
        print("5. Restart bot")
    
    return success

if __name__ == "__main__":
    main()