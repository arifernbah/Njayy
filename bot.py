import time
from datetime import datetime
from core.config import config
from utils.logger import logger
from integrations.telegram import telegram
from strategies.ict_core import ICTStrategy
from execution.trader import EnhancedICTTrader
from analysis.bias import BiasAnalyzer
import os
from binance import AsyncClient, BinanceSocketManager
import asyncio

def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d

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

    async def websocket_candle_handler(self):
        """Websocket handler untuk menerima candle close dari Binance dan trigger strategi secara real-time."""
        max_reconnect_attempts = 5
        reconnect_delay = 5  # seconds
        
        for attempt in range(max_reconnect_attempts):
            try:
                client = await AsyncClient.create(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
                bm = BinanceSocketManager(client)
                interval = self.default_interval.lower()
                streams = [f"{pair.lower()}@kline_{interval}" for pair in self.trading_pairs]
                multi_stream = bm.multiplex_socket(streams)
                
                logger.info(f"[WEBSOCKET] Connected to {len(streams)} streams (attempt {attempt + 1})")
                
                async with multi_stream as stream:
                    while True:
                        try:
                            res = await stream.recv()
                            if res and 'data' in res and 'k' in res['data']:
                                kline = res['data']['k']
                                if safe_get(kline, 'x', default=False):  # Hanya proses saat candle close
                                    symbol = safe_get(res, 'data', 's', default='')
                                    candle = {
                                        'timestamp': safe_get(kline, 't', default=0),
                                        'open': float(safe_get(kline, 'o', default=0)),
                                        'high': float(safe_get(kline, 'h', default=0)),
                                        'low': float(safe_get(kline, 'l', default=0)),
                                        'close': float(safe_get(kline, 'c', default=0)),
                                        'volume': float(safe_get(kline, 'v', default=0)),
                                        'close_time': safe_get(kline, 'T', default=0)
                                    }
                                    from datetime import datetime
                                    candle_close_time = datetime.utcnow()
                                    logger.info(f"[ENTRY TIMING] Candle close received at {candle_close_time.isoformat()} for {symbol}")
                                    # Trigger entry (pastikan proses ini secepat mungkin)
                                    self.strategy.on_new_candle(symbol, candle, self.analyzer, candle_close_time)
                        except Exception as e:
                            logger.error(f"[WEBSOCKET] Error processing message: {e}")
                            continue  # Continue processing other messages
                            
            except Exception as e:
                logger.error(f"[WEBSOCKET] Connection error (attempt {attempt + 1}): {e}")
                if attempt < max_reconnect_attempts - 1:
                    logger.info(f"[WEBSOCKET] Reconnecting in {reconnect_delay} seconds...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay *= 2  # Exponential backoff
                else:
                    logger.error("[WEBSOCKET] Max reconnection attempts reached. Stopping bot.")
                    if config.ENABLE_TELEGRAM:
                        telegram.send_message("🚨 WEBSOCKET ERROR: Bot stopped due to connection issues")
                    break
            finally:
                try:
                    await client.aclose()
                except:
                    pass

    def start(self):
        """Initialize and start the bot (websocket version)"""
        try:
            logger.info("Starting ICT Bot v8.1 (websocket real-time)...")
            self.send_startup_message()
            asyncio.run(self.websocket_candle_handler())
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
                if not safe_get(bias, 'valid', default=False):
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
            # Ensure logs directory exists
            os.makedirs("logs", exist_ok=True)
            log_line = (
                f"[{datetime.utcnow()}] VALID SIGNAL: {signal.pair} {signal.direction} "
                f"entry={signal.entry} sl={signal.sl} tp1={signal.tp1} tp2={signal.tp2} "
                f"score={getattr(signal, 'quality_score', 'N/A')} zone={getattr(signal, 'zone_position', 'N/A')}\n"
            )
            with open("logs/valid_signals.log", "a") as f:
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
                if pair in last_entry and last_entry[pair] is not None:
                    if (utc_now - last_entry[pair]).total_seconds() < 20*60:
                        return False
            # ✅ ENHANCED: ICT Quality-based filtering
            valid = (
                signal.strength >= 8 and
                signal.bias >= 7 and
                signal.regime >= 7 and
                safe_get(self.filters, 'vol_range', default=[0,0])[0] <= signal.volatility <= safe_get(self.filters, 'vol_range', default=[0,0])[1] and
                # ✅ NEW: ICT Quality checks
                signal.quality_score >= safe_get(self.filters, 'min_quality_score', default=0) and  # Minimum quality score from .env
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
            risk = safe_get(self.risk_management, 'default_risk', default=0)
            
            # Check drawdown
            if self.trader.get_drawdown() > 5:
                risk = safe_get(self.risk_management, 'reduced_risk', default=0)
            
            # Check consecutive losses
            if self.trader.get_consecutive_losses() >= 2:
                risk = safe_get(self.risk_management, 'minimum_risk', default=0)
                
            return risk
        except Exception as e:
            logger.error(f"Risk calculation error: {e}")
            return safe_get(self.risk_management, 'minimum_risk', default=0)

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
                f"Risk: {safe_get(self.risk_management, 'default_risk', default=0)*100:.0f}% per trade\n"
                f"Quality minimal: {safe_get(self.filters, 'min_quality_score', default=0)}\n\n"
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
            
            if safe_get(self.risk_management, 'max_trades', default=0) <= status['daily_trades']:
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
            f"Risk: {safe_get(s.risk_management, 'default_risk', default=0)*100:.2f}%\n"
            f"Leverage: {s.trader.leverage}x\n"
            f"Max Daily Trades: {safe_get(s.risk_management, 'max_trades', default=0)}\n"
            f"Max Concurrent Trades: {safe_get(s.risk_management, 'max_concurrent', default=0)}\n"
            f"Drawdown Limit: {config.MAX_DRAWDOWN}%\n"
            f"Min Quality Score: {safe_get(s.filters, 'min_quality_score', default=0)}\n"
            f"Min Signal Strength: {safe_get(s.filters, 'signal_strength', default=0)}\n"
            f"Min Bias Strength: {safe_get(s.filters, 'bias_strength', default=0)}\n"
            f"Min Regime Score: {safe_get(s.filters, 'regime_score', default=0)}\n"
            f"Volatility Range: {safe_get(s.filters, 'vol_range', default=[0,0])[0]} - {safe_get(s.filters, 'vol_range', default=[0,0])[1]}\n"
            f"Timeframe aktif: {config.DEFAULT_INTERVAL}\n"
            f"Session: London {config.LONDON_START}-{config.LONDON_END}, NY {config.NY_START}-{config.NY_END}, Asia {config.ASIAN_START}-{config.ASIAN_END}\n"
            f"Pairs: {', '.join(self.trading_pairs)}\n"
            f"Loop Interval: {config.LOOP_INTERVAL}s\n"
            f"Telegram: {config.ENABLE_TELEGRAM}"
        )
        return settings

    # TODO: Implementasi websocket event handler jika ingin fitur tambahan (saat ini tidak digunakan)
    # (Kosong, tidak ada pass)

if __name__ == "__main__":
    def telegram_message_handler(msg):
        text = msg.get('text', '').strip().lower()
        chat_id = msg.get('chat', {}).get('id')
        # Only respond to the configured chat_id
        if str(chat_id) != str(config.TELEGRAM_CHAT_ID):
            telegram.send_message("⚠️ Unauthorized access.")
            return
        
        if text == "/start":
            telegram.send_message("👋 Hai! Aku Arif_Bot, siap membantu trading kamu. Ketik /help untuk daftar perintah.")
            telegram.send_main_menu()
            return
        
        if text == "/status":
            # ✅ ENHANCED: Use new enhanced status
            telegram.send_enhanced_status(ICTBot.instance)
        elif text == "/balance":
            trader = EnhancedICTTrader()
            balance = trader.get_account_balance()
            telegram.send_message(f"💰 Saldo USDT saat ini: {balance:.2f}")
        elif text == "/drawdown":
            trader = EnhancedICTTrader()
            drawdown = trader.get_drawdown()
            max_drawdown = trader.get_max_drawdown()
            telegram.send_message(f"📉 Drawdown saat ini: {drawdown:.2f}%\n📊 Max Drawdown: {max_drawdown:.2f}%")
        elif text == "/performance":
            # ✅ NEW: Detailed performance report
            telegram.send_performance_report(ICTBot.instance)
        elif text == "/cleanup":
            # ✅ NEW: Cleanup orphaned positions
            telegram.send_cleanup_command(ICTBot.instance)
        elif text == "/positions":
            # ✅ NEW: Show active positions
            active_positions = ICTBot.instance.trader.active_positions
            if not active_positions:
                telegram.send_message("📊 Tidak ada posisi aktif saat ini.")
            else:
                msg = "📊 *AKTIF POSITIONS:*\n\n"
                for pos_id, pos in active_positions.items():
                    pnl = ICTBot.instance.trader._calculate_position_pnl(pos)
                    msg += f"🎯 {pos['symbol']} {pos['direction']}\n"
                    msg += f"💰 Entry: ${pos['entry']:.2f}\n"
                    msg += f"🛑 SL: ${pos['sl']:.2f}\n"
                    msg += f"📊 Size: {pos['size']}\n"
                    msg += f"📈 PnL: ${pnl:.2f}\n"
                    msg += f"⏰ Opened: {pos['opened_at'].strftime('%H:%M')}\n\n"
                telegram.send_message(msg)
        elif text == "/help":
            telegram.send_message("""
📖 *Daftar Perintah Lengkap:*

🔍 *STATUS & MONITORING:*
/status - Status bot dengan metrics lengkap
/performance - Laporan performa detail
/balance - Cek saldo USDT
/drawdown - Cek drawdown saat ini
/positions - Lihat posisi aktif
/uptime - Lama bot berjalan

⚙️ *MANAGEMENT:*
/settings - Lihat setting utama bot
/cleanup - Bersihkan orphaned positions
/pause - Pause trading
/resume - Lanjutkan trading
/shutdown - Matikan bot

📊 *REPORTS:*
/summary - Ringkasan performa harian
/help - Lihat daftar command

💡 *Tips:* Gunakan /status untuk monitoring real-time!
            """)
            telegram.send_main_menu()
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
            # ✅ ENHANCED: Proper shutdown
            ICTBot.instance.trader.shutdown()
            exit(0)
        else:
            telegram.send_message(f"⚠️ Perintah tidak dikenali: {text}\nKetik /help untuk daftar perintah yang tersedia.")

    ICTBot.instance = None
    bot = ICTBot()
    telegram.start_polling(handler=telegram_message_handler)
    ICTBot.instance = bot
    bot.start()