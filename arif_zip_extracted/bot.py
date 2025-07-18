import time
from datetime import datetime
from core.config import config
from utils.logger import logger
from integrations.telegram import telegram
from strategies.ict_core import ICTStrategy
from execution.trader import EnhancedICTTrader
from analysis.bias import BiasAnalyzer
import os

class ICTBot:
    def __init__(self):
        self.author = "arifernbah1"
        self.version = "8.1"
        self.last_update = "2025-07-15 10:53:00"
        self.start_time = datetime.utcnow()  # Track bot start time
        self.paused = False  # Track pause state
        
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
        self.default_interval = config.DEFAULT_INTERVAL  # Tambah baris ini

    def start(self):
        """Initialize and start the bot"""
        try:
            logger.info("Starting ICT Bot v8.1...")
            self.send_startup_message()
            
            while True:
                if not self.paused:
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

    def log_valid_signal(self, signal):
        try:
            log_line = (
                f"[{datetime.utcnow()}] VALID SIGNAL: {signal.pair} {signal.direction} "
                f"entry={signal.entry} sl={signal.sl} tp1={signal.tp1} tp2={signal.tp2} "
                f"score={getattr(signal, 'quality_score', 'N/A')} zone={getattr(signal, 'zone_position', 'N/A')}\n"
            )
            with open("valid_signals.log", "a") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to log valid signal: {e}")

    def validate_signal(self, signal):
        """Enhanced signal validation with ICT quality checks"""
        try:
            # Killzone WIB diperpanjang: 08:00-18:00 (Asia+London panjang), NY tetap 19:00-22:00
            from datetime import datetime, timedelta
            utc_now = datetime.utcnow() + timedelta(hours=7)  # WIB
            hour = utc_now.hour
            in_killzone = (
                (8 <= hour < 18) or   # Asia+London panjang
                (19 <= hour < 22)    # New York
            )
            if not in_killzone:
                return False
            # Cooldown antar OP per pair
            last_entry = getattr(self, 'last_entry_time', {})
            pair = getattr(signal, 'pair', None) or getattr(signal, 'symbol', None)
            if pair:
                if pair in last_entry:
                    if (utc_now - last_entry[pair]).total_seconds() < 20*60:
                        return False
            # ✅ ENHANCED: ICT Quality-based filtering
            valid = (
                signal.strength >= 8 and
                signal.bias >= 7 and
                signal.regime >= 7 and
                self.filters['vol_range'][0] <= signal.volatility <= self.filters['vol_range'][1] and
                # ✅ NEW: ICT Quality checks
                signal.quality_score >= self.filters['min_quality_score'] and  # Minimum quality score from .env
                signal.validate_levels()  # Enhanced validation
            )
            if valid and pair:
                if not hasattr(self, 'last_entry_time'):
                    self.last_entry_time = {}
                self.last_entry_time[pair] = utc_now
                # Log valid signal
                self.log_valid_signal(signal)
            return valid
        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            return False

    def execute_signal(self, signal, bias):
        """Execute validated signal with ICT quality enhancements"""
        try:
            # Calculate position size
            risk = self.calculate_risk()
            position_size = self.trader.calculate_position_size(signal, risk)
            
            # Execute trade
            success = self.trader.execute_entry_enhanced(signal)
            
            if success and config.ENABLE_TELEGRAM:
                # ✅ ENHANCED: Send quality-based alerts
                if signal.quality_class == 'PREMIUM':
                    telegram.send_premium_signal_alert(signal, bias)
                else:
                    telegram.send_trade_alert(signal, bias, risk, position_size)
                
                # ✅ ADDITIONAL: Send ICT quality analysis
                if signal.quality_score >= 80:
                    telegram.send_ict_quality_alert(signal, bias)
                
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
            pairs = ', '.join(self.trading_pairs)
            msg = (
                f"👋 Hai, aku Arif_Bot!  \n"
                f"Mulai tugas: {wib_now.strftime('%Y-%m-%d %H:%M:%S')} WIB\n"
                f"Hari ini siap trading, jangan galak-galak ya~\n\n"
                f"Pairs: {pairs}\n"
                f"Target sinyal: {config.SIGNAL_TARGET_MIN}-{config.SIGNAL_TARGET_MAX}/hari\n"
                f"Risk: {self.risk_management['default_risk']*100:.0f}% per trade\n"
                f"Quality minimal: {self.filters['min_quality_score']}\n\n"
                f"Status: Lagi mantau market, siap cari cuan! 🚦\n\n"
                f"(Psst... Kalau aku error, jangan salahin aku, salahin market aja 😆)"
            )
            telegram.send_message(msg)
            telegram.send_main_menu()  # Show main menu keyboard after startup
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

    def get_uptime(self):
        delta = datetime.utcnow() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

    def get_summary(self):
        perf = self.trader.get_enhanced_performance()
        summary = (
            f"📊 *SUMMARY*\n"
            f"Total Trades: {perf.get('total_trades', 0)}\n"
            f"✅ Wins: {perf.get('wins', 0)}\n"
            f"❌ Losses: {perf.get('losses', 0)}\n"
            f"🎯 Win Rate: {perf.get('win_rate', 0):.1f}%\n"
            f"💰 Daily PnL: ${perf.get('daily_pnl', 0):.2f}\n"
            f"📉 Drawdown: {self.trader.get_drawdown():.2f}%\n"
            f"📈 Max Drawdown: {self.trader.get_max_drawdown():.2f}%\n"
            f"💹 Market Volatility: {perf.get('market_volatility', 0):.2f}%\n"
            f"🔄 Active Positions: {perf.get('active_positions', 0)}\n"
            f"⏱ Uptime: {self.get_uptime()}"
        )
        return summary

    def get_settings(self):
        s = self
        settings = (
            f"⚙️ *BOT SETTINGS*\n"
            f"Risk: {s.risk_management['default_risk']*100:.2f}%\n"
            f"Leverage: {s.trader.leverage}x\n"
            f"Max Daily Trades: {s.risk_management['max_trades']}\n"
            f"Max Concurrent Trades: {s.risk_management['max_concurrent']}\n"
            f"Drawdown Limit: {config.MAX_DRAWDOWN}%\n"
            f"Min Quality Score: {s.filters['min_quality_score']}\n"
            f"Min Signal Strength: {s.filters['signal_strength']}\n"
            f"Min Bias Strength: {s.filters['bias_strength']}\n"
            f"Min Regime Score: {s.filters['regime_score']}\n"
            f"Volatility Range: {s.filters['vol_range'][0]} - {s.filters['vol_range'][1]}\n"
            f"Session: London {config.LONDON_START}-{config.LONDON_END}, NY {config.NY_START}-{config.NY_END}, Asia {config.ASIAN_START}-{config.ASIAN_END}\n"
            f"Pairs: {', '.join(self.trading_pairs)}\n"
            f"Loop Interval: {config.LOOP_INTERVAL}s\n"
            f"Telegram: {config.ENABLE_TELEGRAM}"
        )
        return settings

    def start_websocket(self):
        """Inisialisasi dan jalankan websocket Binance untuk menerima candle baru sesuai interval di config."""
        # TODO: Implementasi websocket event handler
        pass

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
/summary - Ringkasan performa harian
/settings - Lihat setting utama bot
/uptime - Lama bot berjalan
/pause - Pause trading
/resume - Lanjutkan trading
/help - Lihat daftar command
/shutdown - Matikan bot
""")
            telegram.send_main_menu()  # Show main menu keyboard on /help
        elif text == "/summary":
            telegram.send_message(ICTBot.instance.get_summary())
        elif text == "/settings":
            telegram.send_message(ICTBot.instance.get_settings())
        elif text == "/uptime":
            telegram.send_message(f"⏱ Uptime: {ICTBot.instance.get_uptime()}")
        elif text == "/pause":
            ICTBot.instance.paused = True
            telegram.send_message("⏸️ Trading paused. Bot tidak akan entry baru sampai /resume.")
        elif text == "/resume":
            ICTBot.instance.paused = False
            telegram.send_message("▶️ Trading resumed. Bot akan entry seperti biasa.")
        elif text == "/shutdown":
            telegram.send_message("🛑 Bot akan dimatikan...")
            exit(0)
        else:
            telegram.send_message(f"⚠️ Perintah tidak dikenali: {text}")

    ICTBot.instance = None
    bot = ICTBot()
    telegram.start_polling(handler=telegram_message_handler)
    ICTBot.instance = bot
    bot.start()