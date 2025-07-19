#!/usr/bin/env python3
"""
Test Bot Notifications
"""

import os
import sys

def test_notifications():
    """Test different types of bot notifications"""
    try:
        # Import after loading env
        from core.config import config
        from integrations.telegram import telegram
        
        print("🔍 Testing Bot Notifications...")
        
        if not config.ENABLE_TELEGRAM:
            print("❌ Telegram is disabled")
            return False
        
        # Test 1: Simple message
        print("📤 Test 1: Simple message...")
        if telegram.send_message("🤖 Test notification from Arif_Bot"):
            print("✅ Simple message sent")
        else:
            print("❌ Simple message failed")
            return False
        
        # Test 2: Margin insufficient notification
        print("📤 Test 2: Margin insufficient notification...")
        margin_msg = (
            f"⚠️ *MARGIN INSUFFICIENT*\n"
            f"📌 Pair: BTCUSDT\n"
            f"💰 Required: $15.50\n"
            f"💳 Available: $9.19\n"
            f"📊 Leverage: 3x\n"
            f"📈 Position Size: 0.001\n"
            f"🎯 Entry Price: $45,000.00\n\n"
            f"*Suggestion:* Top up balance or reduce position size"
        )
        if telegram.send_message(margin_msg):
            print("✅ Margin insufficient notification sent")
        else:
            print("❌ Margin insufficient notification failed")
        
        # Test 3: Entry failed notification
        print("📤 Test 3: Entry failed notification...")
        entry_failed_msg = f"❌ ENTRY FAILED! Order market tidak masuk ke Binance untuk BTCUSDT."
        if telegram.send_message(entry_failed_msg):
            print("✅ Entry failed notification sent")
        else:
            print("❌ Entry failed notification failed")
        
        # Test 4: Entry executed notification
        print("📤 Test 4: Entry executed notification...")
        entry_success_msg = (
            f"🚀 *ENTRY EXECUTED*\n"
            f"Order ID: 123456789\n"
            f"📌 PAIR: BTCUSDT\n"
            f"🎯 Direction: BUY\n"
            f"💰 Entry (real): $45,000.00\n"
            f"🛑 SL (real): $44,500.00\n"
            f"🎯 TP1: MARKET ORDER (70%) - RR 1:1.2\n"
            f"🎯 TP2: MARKET ORDER (30%) - RR 1:2\n"
            f"📊 Size: 0.001\n"
            f"💹 Market Vol: 2.5%\n"
            f"🔢 Daily Trades: 1/6\n"
            f"🕒 Waktu: 14:30:00 WIB"
        )
        if telegram.send_message(entry_success_msg):
            print("✅ Entry executed notification sent")
        else:
            print("❌ Entry executed notification failed")
        
        print("\n✅ All notification tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing notifications: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Arif_Bot Notification Test")
    print("=" * 50)
    
    success = test_notifications()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Notification test PASSED")
        print("Bot can send all types of notifications")
    else:
        print("❌ Notification test FAILED")
        print("Check Telegram credentials and connection")
    
    return success

if __name__ == "__main__":
    main()