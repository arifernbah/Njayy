import time
from datetime import datetime
from core.config import config
from utils.logger import logger
from integrations.telegram import telegram
from strategies.ict_core import ICTStrategy
from execution.trader import EnhancedICTTrader
from analysis.bias import BiasAnalyzer

class ICTBot:
    def __init__(self):
        self.author = "arifernbah1"
        self.version = "8.1"
        self.last_update = "2025-07-15 10:53:00"
        
        # Components
        self.strategy = ICTStrategy()
        self.trader = EnhancedICTTrader()
        self.analyzer = BiasAnalyzer()
        
        # Performance Parameters
        self.signal_target = f"{config.SIGNAL_TARGET_MIN}-{config.SIGNAL_TARGET_MAX} per day"
        self.expected_wr = f"{config.TARGET_WIN_RATE}%"
        self.max_drawdown = f"{config.MAX_DRAWDOWN}%"
        
        # Get settings from config
        self.timeframes = config.get_timeframe_settings()
        self.filters = config.get_filter_settings()
        self.risk_management = config.get_risk_settings()
        self.sessions = config.get_session_settings()
        self.trading_pairs = config.TRADING_PAIRS

    def start(self):
        """Initialize and start the bot"""
        try:
            logger.info("Starting ICT Bot v8.1...")
            self.send_startup_message()
            
            while True:
                self.main_loop()
                time.sleep(config.LOOP_INTERVAL)
                
        except Exception as e:
            logger.error(f"Bot error: {e}")
            if config.ENABLE_TELEGRAM:
                telegram.send_message(f"⚠️ Bot Error: {e}")

    def main_loop(self):
        """Main bot loop"""
        try:
            # Check session
            current_session = self.check_session()
            if not current_session:
                return
            
            # Process each trading pair
            for pair in self.trading_pairs:
                self.trader.symbol = pair  # Set symbol untuk multi-pair
                # ✅ FIXED: Pass symbol parameter to analyze_bias
                bias = self.analyzer.analyze_bias(pair)
                if not bias['valid']:
                    logger.warning(f"Invalid bias for {pair}")
                    continue
                
                # Find signals with symbol parameter
                signals = self.strategy.find_signals(bias, pair)
                if signals:
                    for signal in signals:
                        if self.validate_signal(signal):
                            self.execute_signal(signal, bias)
                
                # Manage positions
                self.trader.manage_positions_enhanced()
            
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
            return (
                signal.strength >= self.filters['signal_strength'] and
                signal.bias >= self.filters['bias_strength'] and
                signal.regime >= self.filters['regime_score'] and
                self.filters['vol_range'][0] <= signal.volatility <= self.filters['vol_range'][1]
            )
        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            return False

    def execute_signal(self, signal, bias):
        """Execute validated signal"""
        try:
            # Calculate position size
            risk = self.calculate_risk()
            position_size = self.trader.calculate_position_size(signal, risk)
            
            # Execute trade
            success = self.trader.execute_entry_enhanced(signal)
            
            if success and config.ENABLE_TELEGRAM:
                # Send signal notification
                timestamp = datetime.utcnow().strftime("%H:%M UTC")
                message = f"""
📢 *ENTRY SIGNAL DETECTED*

📌 *PAIR*: {signal.pair}
🕒 *Time*: {timestamp}
📊 *Bias*: {bias['direction']} ({bias['strength']:.1f})
🧠 *Signal Strength*: {signal.strength}
🧱 *OB + BOS Valid*: ✅
🕳 *FVG*: ✅
💧 *Liquidity Sweep*: ✅
🔥 *Displacement Candle*: ✅
⏰ *Killzone Active*: {'Ya' if self.strategy.in_killzone() else 'Tidak'}

🎯 *ENTRY*: {signal.entry}
🛡 *SL*: {signal.sl}
🎯 *TP1*: {signal.tp1}
🎯 *TP2*: {signal.tp2}
⚖️ *Risk %*: {risk * 100:.1f}%
💰 *Size*: {position_size}

📈 *Win Rate Saat Ini*: ~{self.trader.get_win_rate()}%
"""
                telegram.send_message(message)
                
        except Exception as e:
            logger.error(f"Signal execution error: {e}")

    def calculate_risk(self):
        """Calculate risk based on account conditions"""
        try:
            # Default risk
            risk = self.risk_management['default_risk']
            
            # Check drawdown
            if self.trader.get_drawdown() > 5:
                risk = self.risk_management['reduced_risk']
            
            # Check consecutive losses
            if self.trader.get_consecutive_losses() >= 2:
                risk = self.risk_management['minimum_risk']
                
            return risk
        except Exception as e:
            logger.error(f"Risk calculation error: {e}")
            return self.risk_management['minimum_risk']

    def send_startup_message(self):
        """Send startup message to Telegram"""
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
            msg = (
                f"🚀 ICT Bot v8.1 Siap Beraksi!\n\n"
                f"Author: {self.author}\n"
                f"Start: {wib_now.strftime('%Y-%m-%d %H:%M:%S')} WIB\n\n"
                f"Pengaturan Bot:\n"
                f"- Pairs: {pairs_str}\n"
                f"- Target Sinyal: {self.signal_target} per hari\n"
                f"- Min Score: {self.filters['signal_strength']}\n"
                f"- Risk per Trade: {self.risk_management['default_risk']*100}%\n\n"
                f"Status: Bot aktif & siap trading!"
            )
            telegram.send_message(msg)
        except Exception as e:
            logger.error(f"Startup message error: {e}")

    def update_status(self):
        """Update bot status"""
        try:
            status = {
                "running": True,
                "current_trades": self.trader.get_active_trades(),
                "daily_trades": self.trader.get_daily_trades(),
                "performance": self.trader.get_performance()
            }
            
            if status['daily_trades'] >= self.risk_management['max_trades']:
                logger.info("Daily trade limit reached")
        except Exception as e:
            logger.error(f"Status update error: {e}")

if __name__ == "__main__":
    def telegram_message_handler(msg):
        text = msg.get('text', '').strip().lower()
        chat_id = msg.get('chat', {}).get('id')
        # Only respond to the configured chat_id
        if str(chat_id) != str(config.TELEGRAM_CHAT_ID):
            telegram.send_message("⚠️ Unauthorized access.")
            return
        if text == "/status":
            telegram.send_message("✅ Bot status: Aktif dan berjalan")
        elif text == "/balance":
            trader = EnhancedICTTrader()
            balance = trader.get_account_balance()
            telegram.send_message(f"💰 Saldo USDT saat ini: {balance}")
        elif text == "/drawdown":
            trader = EnhancedICTTrader()
            drawdown = trader.get_drawdown()
            telegram.send_message(f"📉 Drawdown saat ini: {drawdown:.2f}%")
        elif text == "/help":
            telegram.send_message("""
📖 Daftar Perintah:
/status - Cek status bot
/balance - Cek saldo USDT
/drawdown - Cek drawdown saat ini
/help - Lihat daftar command

Perintah lanjutan dapat ditambahkan nanti seperti /summary, /pause, dll.
""")
        elif text == "/shutdown":
            telegram.send_message("🛑 Bot akan dimatikan...")
            exit(0)
        else:
            telegram.send_message(f"⚠️ Perintah tidak dikenali: {text}")

    telegram.start_polling(handler=telegram_message_handler)
    bot = ICTBot()
    bot.start()