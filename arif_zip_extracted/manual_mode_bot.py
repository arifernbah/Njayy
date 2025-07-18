#!/usr/bin/env python3
"""
Manual Trading Mode Bot for Web Horizon
This bot detects signals and sends alerts for manual execution
"""

import time
from datetime import datetime
from core.config import config
from utils.logger import logger
from integrations.telegram import telegram
from strategies.ict_core import ICTStrategy
from analysis.bias import BiasAnalyzer

class ManualTradingBot:
    def __init__(self):
        self.author = "arifernbah1"
        self.version = "8.1-MANUAL"
        self.last_update = "2025-07-18 08:00:00"
        
        # Components
        self.strategy = ICTStrategy()
        self.analyzer = BiasAnalyzer()
        
        # Manual trading mode
        self.manual_mode = True
        self.signal_count = 0
        
        # Get settings from config
        self.timeframes = config.get_timeframe_settings()
        self.filters = config.get_filter_settings()
        self.sessions = config.get_session_settings()
        self.trading_pairs = config.TRADING_PAIRS

    def start(self):
        """Initialize and start the manual trading bot"""
        try:
            logger.info("Starting Manual Trading Bot v8.1...")
            self.send_startup_message()
            
            while True:
                self.main_loop()
                time.sleep(config.LOOP_INTERVAL)
                
        except Exception as e:
            logger.error(f"Bot error: {e}")
            telegram.send_critical(f"Bot Error: {e}", msg_type='Bot Error')
            time.sleep(10)

    def main_loop(self):
        """Main bot loop for signal detection"""
        try:
            # Check session
            current_session = self.check_session()
            if not current_session:
                return
            
            # Process each trading pair
            for pair in self.trading_pairs:
                # Analyze bias
                bias = self.analyzer.analyze_bias(pair)
                if not bias['valid']:
                    continue
                
                # Find signals
                signals = self.strategy.find_signals(bias, pair)
                if signals:
                    logger.info(f"Found {len(signals)} signals for {pair}")
                    
                    for signal in signals:
                        if self.validate_signal(signal):
                            self.send_manual_signal(signal, bias)
                            self.signal_count += 1
            
            # Update status
            self.update_status()
            
        except Exception as e:
            logger.error(f"Main loop error: {e}")

    def check_session(self):
        """Check if current time is within trading session"""
        current_time = datetime.utcnow().strftime("%H:%M")
        
        for session, times in self.sessions.items():
            if times['start'] <= current_time <= times['end']:
                return session
        return None

    def validate_signal(self, signal):
        """Validate signal against filters"""
        try:
            # Signal freshness check
            if not signal.is_fresh(max_age_minutes=5):
                return False
                
            # Killzone check
            from datetime import datetime, timedelta
            utc_now = datetime.utcnow() + timedelta(hours=7)  # WIB
            hour = utc_now.hour
            in_killzone = (
                (8 <= hour < 18) or   # Asia+London
                (19 <= hour < 22)    # New York
            )
            if not in_killzone:
                return False
                
            # Cooldown check
            last_entry = getattr(self, 'last_entry_time', {})
            pair = getattr(signal, 'pair', None) or getattr(signal, 'symbol', None)
            if pair and pair in last_entry:
                if (utc_now - last_entry[pair]).total_seconds() < 20*60:
                    return False
                    
            # Filter check
            valid = (
                signal.strength >= 8 and
                signal.bias >= 7 and
                signal.regime >= 7 and
                self.filters['vol_range'][0] <= signal.volatility <= self.filters['vol_range'][1]
            )
            
            if valid and pair:
                if not hasattr(self, 'last_entry_time'):
                    self.last_entry_time = {}
                self.last_entry_time[pair] = utc_now
                
            return valid
            
        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            return False

    def send_manual_signal(self, signal, bias):
        """Send manual trading signal via Telegram"""
        try:
            timestamp = datetime.utcnow().strftime("%H:%M UTC")
            
            message = f"""
🚨 *MANUAL TRADING SIGNAL #{self.signal_count}*

📌 *PAIR*: {signal.pair}
🕒 *Time*: {timestamp}
📊 *Bias*: {bias['direction']} ({bias['strength']:.1f})
🧠 *Signal Strength*: {signal.strength}
⏰ *Killzone*: {'Active' if self.strategy.in_killzone() else 'Inactive'}

🎯 *ENTRY*: {signal.entry}
🛡 *SL*: {signal.sl}
🎯 *TP1*: {signal.tp1}
🎯 *TP2*: {signal.tp2}

⚠️ *MANUAL ACTION REQUIRED*
📱 Open Binance app and execute this trade manually

💡 *Instructions*:
1. Open Binance Futures
2. Select {signal.pair}
3. Set leverage to 5x
4. Place {signal.direction} order at {signal.entry}
5. Set SL at {signal.sl}
6. Set TP1 at {signal.tp1}
7. Set TP2 at {signal.tp2}

📈 *Risk Management*:
- Use 1-2% risk per trade
- Monitor position closely
- Adjust SL if needed
"""
            
            telegram.send_critical(message, msg_type='Manual Signal')
            logger.info(f"Manual signal sent for {signal.pair}")
            
        except Exception as e:
            logger.error(f"Manual signal error: {e}")

    def send_startup_message(self):
        """Send startup message"""
        if not config.ENABLE_TELEGRAM:
            return
            
        try:
            from datetime import timedelta
            utc_now = datetime.utcnow()
            wib_now = utc_now + timedelta(hours=7)
            
            pairs = self.trading_pairs
            if len(pairs) > 5:
                pairs_str = ', '.join(pairs[:5]) + '\n  ' + ', '.join(pairs[5:])
            else:
                pairs_str = ', '.join(pairs)
                
            msg = f"""
🤖 *Manual Trading Bot v8.1 Started*

Author: {self.author}
Start: {wib_now.strftime('%Y-%m-%d %H:%M:%S')} WIB

📊 *Configuration*:
- Pairs: {pairs_str}
- Mode: Manual Trading
- Signal Detection: Active
- Telegram Alerts: Active

⚠️ *IMPORTANT*:
- Bot will detect signals
- You execute trades manually
- Monitor positions in Binance app
- Use Telegram for alerts

Status: Bot aktif & siap detect signals!
"""
            telegram.send_message(msg)
            
        except Exception as e:
            logger.error(f"Startup message error: {e}")

    def update_status(self):
        """Update bot status"""
        try:
            status = {
                "running": True,
                "mode": "Manual Trading",
                "signals_detected": self.signal_count,
                "session": self.check_session()
            }
            
            # Log status every 10 minutes
            if hasattr(self, 'last_status_log'):
                if (datetime.utcnow() - self.last_status_log).total_seconds() > 600:
                    logger.info(f"Bot status: {status}")
                    self.last_status_log = datetime.utcnow()
            else:
                self.last_status_log = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Status update error: {e}")

    def handle_command(self, message):
        """Handle Telegram commands"""
        try:
            text = message.get('text', '').strip()
            if not text.startswith('/'):
                return
            
            command = text.split()[0].lower()
            
            if command == '/status':
                telegram.send_medium_priority(
                    f"✅ Bot status: Manual Trading Mode\n"
                    f"📊 Signals detected: {self.signal_count}\n"
                    f"⏰ Session: {self.check_session() or 'Outside trading hours'}",
                    msg_type='Status Check'
                )
                
            elif command == '/help':
                telegram.send_low_priority("""
🤖 *Manual Trading Bot Commands*

/status - Check bot status
/help - Show this help
/shutdown - Shutdown bot

📱 *Manual Trading Process*:
1. Bot detects ICT signals
2. Sends alerts via Telegram
3. You execute trades manually
4. Monitor positions in Binance app

⚠️ *Note*: Automated trading disabled due to regional restrictions
                """, msg_type='Help')
                
            elif command == '/shutdown':
                telegram.send_critical("🛑 Manual trading bot will be stopped...", msg_type='Shutdown Command')
                self.running = False
                
            else:
                telegram.send_low_priority(f"⚠️ Unknown command: {text}", msg_type='Unknown Command')
                
        except Exception as e:
            logger.error(f"Command handler error: {e}")
            telegram.send_critical(f"❌ Command error: {e}", msg_type='Command Error')

if __name__ == "__main__":
    def telegram_message_handler(msg):
        try:
            bot_instance.handle_command(msg)
        except Exception as e:
            logger.error(f"Message handler error: {e}")
    
    # Set up Telegram message handler
    telegram.set_message_handler(telegram_message_handler)
    telegram.start_polling()
    
    # Create and run manual trading bot
    bot = ManualTradingBot()
    bot.start()