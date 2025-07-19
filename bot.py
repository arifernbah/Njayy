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

    def log_rejected_signal(self, signal, reason, details=None):
        """Log rejected signals with detailed information"""
        try:
            # ✅ ENHANCED: Validate parameters
            if not signal:
                logger.error("Cannot log rejected signal: signal is None")
                return
            
            if not reason:
                reason = "UNKNOWN"
            
            if details is None:
                details = "No details provided"
            
            # ✅ ENHANCED: Safe attribute access
            try:
                pair = getattr(signal, 'pair', None) or getattr(signal, 'symbol', None) or "UNKNOWN"
                direction = getattr(signal, 'direction', "UNKNOWN")
                entry = getattr(signal, 'entry', "N/A")
                sl = getattr(signal, 'sl', "N/A")
                tp1 = getattr(signal, 'tp1', "N/A")
                tp2 = getattr(signal, 'tp2', "N/A")
            except Exception as e:
                logger.error(f"Error accessing signal attributes: {e}")
                pair = "UNKNOWN"
                direction = "UNKNOWN"
                entry = sl = tp1 = tp2 = "N/A"
            
            # Ensure logs directory exists
            os.makedirs("logs", exist_ok=True)
            
            # ✅ ENHANCED: Safe string formatting
            try:
                log_line = (
                    f"[{datetime.utcnow()}] REJECTED SIGNAL: {pair} {direction} "
                    f"entry={entry} sl={sl} tp1={tp1} tp2={tp2} "
                    f"reason={reason} details={details}\n"
                )
            except Exception as e:
                logger.error(f"Error formatting log line: {e}")
                log_line = f"[{datetime.utcnow()}] REJECTED SIGNAL: {pair} reason={reason} details={details}\n"
            
            # ✅ ENHANCED: Safe file writing
            try:
                with open("logs/rejected_signals.log", "a", encoding='utf-8') as f:
                    f.write(log_line)
            except (IOError, OSError) as e:
                logger.error(f"Failed to write to rejected_signals.log: {e}")
                # Fallback: try to write to console
                print(f"REJECTED SIGNAL LOG: {log_line.strip()}")
                
        except Exception as e:
            logger.error(f"Failed to log rejected signal: {e}")
            # Last resort: print to console
            print(f"CRITICAL: Failed to log rejected signal - {e}")

    def validate_signal(self, signal):
        """Enhanced signal validation with ICT quality checks and price deviation validation"""
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
            
            # ✅ NEW: Price Deviation Validation
            try:
                current_price = self.trader.get_current_price_enhanced(pair)
                if current_price and current_price > 0:
                    # ✅ ENHANCED: Validate signal attributes exist
                    if not hasattr(signal, 'entry') or not hasattr(signal, 'sl') or not hasattr(signal, 'tp1') or not hasattr(signal, 'tp2'):
                        logger.error(f"Signal missing required attributes: entry={hasattr(signal, 'entry')}, sl={hasattr(signal, 'sl')}, tp1={hasattr(signal, 'tp1')}, tp2={hasattr(signal, 'tp2')}")
                        self.log_rejected_signal(signal, "MISSING_ATTRIBUTES", "Signal missing entry/sl/tp1/tp2 attributes")
                        return False
                    
                    # ✅ ENHANCED: Validate signal prices are numeric
                    try:
                        entry_price = float(signal.entry)
                        sl_price = float(signal.sl)
                        tp1_price = float(signal.tp1)
                        tp2_price = float(signal.tp2)
                    except (ValueError, TypeError) as e:
                        logger.error(f"Signal prices are not numeric: {e}")
                        self.log_rejected_signal(signal, "INVALID_PRICES", f"Prices not numeric: entry={signal.entry}, sl={signal.sl}, tp1={signal.tp1}, tp2={signal.tp2}")
                        return False
                    
                    # ✅ ENHANCED: Validate prices are positive
                    if entry_price <= 0 or sl_price <= 0 or tp1_price <= 0 or tp2_price <= 0:
                        logger.error(f"Signal contains non-positive prices: entry={entry_price}, sl={sl_price}, tp1={tp1_price}, tp2={tp2_price}")
                        self.log_rejected_signal(signal, "NON_POSITIVE_PRICES", f"Non-positive prices detected")
                        return False
                    
                    # Check entry price deviation
                    entry_deviation = abs(entry_price - current_price) / current_price
                    if entry_deviation > config.SIGNAL_MAX_ENTRY_DEVIATION:
                        logger.warning(f"Signal entry terlalu jauh dari market: {entry_deviation:.2%} > {config.SIGNAL_MAX_ENTRY_DEVIATION:.2%}")
                        self.log_rejected_signal(signal, "ENTRY_DEVIATION", f"Entry dev: {entry_deviation:.2%}, Max: {config.SIGNAL_MAX_ENTRY_DEVIATION:.2%}")
                        return False
                    
                    # Check SL price deviation
                    sl_deviation = abs(sl_price - current_price) / current_price
                    if sl_deviation > config.SIGNAL_MAX_SL_DEVIATION:
                        logger.warning(f"Signal SL terlalu jauh dari market: {sl_deviation:.2%} > {config.SIGNAL_MAX_SL_DEVIATION:.2%}")
                        self.log_rejected_signal(signal, "SL_DEVIATION", f"SL dev: {sl_deviation:.2%}, Max: {config.SIGNAL_MAX_SL_DEVIATION:.2%}")
                        return False
                    
                    # Check TP1 price deviation
                    tp1_deviation = abs(tp1_price - current_price) / current_price
                    if tp1_deviation > config.SIGNAL_MAX_TP_DEVIATION:
                        logger.warning(f"Signal TP1 terlalu jauh dari market: {tp1_deviation:.2%} > {config.SIGNAL_MAX_TP_DEVIATION:.2%}")
                        self.log_rejected_signal(signal, "TP1_DEVIATION", f"TP1 dev: {tp1_deviation:.2%}, Max: {config.SIGNAL_MAX_TP_DEVIATION:.2%}")
                        return False
                    
                    # Check TP2 price deviation
                    tp2_deviation = abs(tp2_price - current_price) / current_price
                    if tp2_deviation > config.SIGNAL_MAX_TP_DEVIATION:
                        logger.warning(f"Signal TP2 terlalu jauh dari market: {tp2_deviation:.2%} > {config.SIGNAL_MAX_TP_DEVIATION:.2%}")
                        self.log_rejected_signal(signal, "TP2_DEVIATION", f"TP2 dev: {tp2_deviation:.2%}, Max: {config.SIGNAL_MAX_TP_DEVIATION:.2%}")
                        return False
                    
                    logger.info(f"✅ Price validation passed: Entry={entry_deviation:.2%}, SL={sl_deviation:.2%}, TP1={tp1_deviation:.2%}, TP2={tp2_deviation:.2%}")
                else:
                    logger.warning(f"Tidak bisa dapat current price untuk {pair}, skip price validation")
            except Exception as e:
                logger.warning(f"Price validation error: {e}, skip price validation")
                # ✅ ENHANCED: Log the specific error for debugging
                self.log_rejected_signal(signal, "PRICE_VALIDATION_ERROR", f"Error: {str(e)}")
            
            # ✅ ENHANCED: ICT Quality-based filtering
            valid = (
                signal.strength >= 8 and
                signal.bias >= 7 and
                signal.regime >= 7 and
                # ✅ FIXED: Use proper volatility range default from config
                safe_get(self.filters, 'vol_range', default=[config.VOL_RANGE_MIN, config.VOL_RANGE_MAX])[0] <= signal.volatility <= safe_get(self.filters, 'vol_range', default=[config.VOL_RANGE_MIN, config.VOL_RANGE_MAX])[1] and
                # ✅ FIXED: Use proper quality score default from config
                signal.quality_score >= safe_get(self.filters, 'min_quality_score', default=config.MIN_QUALITY_SCORE) and  # Use config default instead of 0
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
        """Execute validated signal with ICT quality enhancements and price validation"""
        try:
            # ✅ NEW: Final Price Validation before execution
            pair = getattr(signal, 'pair', None) or getattr(signal, 'symbol', None)
            if pair:
                try:
                    current_price = self.trader.get_current_price_enhanced(pair)
                    if current_price and current_price > 0:
                        # ✅ ENHANCED: Validate signal entry price
                        if not hasattr(signal, 'entry'):
                            logger.error(f"Signal missing entry price for execution")
                            self.log_rejected_signal(signal, "EXECUTION_MISSING_ENTRY", "Signal missing entry price")
                            return False
                        
                        try:
                            entry_price = float(signal.entry)
                            if entry_price <= 0:
                                logger.error(f"Signal entry price is not positive: {entry_price}")
                                self.log_rejected_signal(signal, "EXECUTION_INVALID_ENTRY", f"Entry price not positive: {entry_price}")
                                return False
                        except (ValueError, TypeError) as e:
                            logger.error(f"Signal entry price is not numeric: {e}")
                            self.log_rejected_signal(signal, "EXECUTION_INVALID_ENTRY_TYPE", f"Entry price not numeric: {signal.entry}")
                            return False
                        
                        entry_deviation = abs(entry_price - current_price) / current_price
                        if entry_deviation > config.SIGNAL_EXECUTION_DEVIATION:
                            logger.warning(f"❌ Signal ditolak: Market price terlalu jauh untuk execution ({entry_deviation:.2%} > {config.SIGNAL_EXECUTION_DEVIATION:.2%})")
                            self.log_rejected_signal(signal, "EXECUTION_DEVIATION", f"Execution dev: {entry_deviation:.2%}, Max: {config.SIGNAL_EXECUTION_DEVIATION:.2%}")
                            if config.ENABLE_TELEGRAM:
                                try:
                                    telegram.send_message(
                                        f"⚠️ *SIGNAL DITOLAK*\n"
                                        f"📌 Pair: {pair}\n"
                                        f"🎯 Direction: {signal.direction}\n"
                                        f"💰 Signal Entry: ${entry_price:.2f}\n"
                                        f"💹 Market Price: ${current_price:.2f}\n"
                                        f"📊 Deviation: {entry_deviation:.2%}\n"
                                        f"🚫 Max Allowed: {config.SIGNAL_EXECUTION_DEVIATION:.2%}\n\n"
                                        f"*Alasan:* Market price terlalu jauh dari signal entry"
                                    )
                                except Exception as telegram_error:
                                    logger.error(f"Failed to send Telegram rejection alert: {telegram_error}")
                            return False
                        logger.info(f"✅ Final price validation passed: {entry_deviation:.2%} deviation")
                    else:
                        logger.warning(f"Tidak bisa dapat current price untuk {pair} saat execution, skip final validation")
                except Exception as e:
                    logger.warning(f"Final price validation error: {e}, continue with execution")
                    self.log_rejected_signal(signal, "EXECUTION_PRICE_ERROR", f"Final validation error: {str(e)}")
            
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
            # ✅ FIXED: Use proper risk defaults from config (values are in percentage)
            risk = safe_get(self.risk_management, 'default_risk', default=config.DEFAULT_RISK/100)
            
            # Check drawdown
            if self.trader.get_drawdown() > 5:
                risk = safe_get(self.risk_management, 'reduced_risk', default=config.REDUCED_RISK/100)
            
            # Check consecutive losses
            if self.trader.get_consecutive_losses() >= 2:
                risk = safe_get(self.risk_management, 'minimum_risk', default=config.MINIMUM_RISK/100)
                
            return risk
        except Exception as e:
            logger.error(f"Risk calculation error: {e}")
            return safe_get(self.risk_management, 'minimum_risk', default=config.MINIMUM_RISK/100)

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
                f"Risk: {safe_get(self.risk_management, 'default_risk', default=config.DEFAULT_RISK/100)*100:.0f}% per trade\n"
                f"Quality minimal: {safe_get(self.filters, 'min_quality_score', default=config.MIN_QUALITY_SCORE)}\n\n"
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
            
            if safe_get(self.risk_management, 'max_trades', default=config.MAX_DAILY_TRADES) <= status['daily_trades']:
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
            f"Risk: {safe_get(s.risk_management, 'default_risk', default=config.DEFAULT_RISK/100)*100:.2f}%\n"
            f"Leverage: {s.trader.leverage}x\n"
            f"Max Daily Trades: {safe_get(s.risk_management, 'max_trades', default=config.MAX_DAILY_TRADES)}\n"
            f"Max Concurrent Trades: {safe_get(s.risk_management, 'max_concurrent', default=config.MAX_CONCURRENT_TRADES)}\n"
            f"Drawdown Limit: {config.MAX_DRAWDOWN}%\n"
            f"Min Quality Score: {safe_get(s.filters, 'min_quality_score', default=config.MIN_QUALITY_SCORE)}\n"
            f"Min Signal Strength: {safe_get(s.filters, 'signal_strength', default=config.MIN_SIGNAL_STRENGTH)}\n"
            f"Min Bias Strength: {safe_get(s.filters, 'bias_strength', default=config.MIN_BIAS_STRENGTH)}\n"
            f"Min Regime Score: {safe_get(s.filters, 'regime_score', default=config.MIN_REGIME_SCORE)}\n"
            f"Volatility Range: {safe_get(s.filters, 'vol_range', default=[config.VOL_RANGE_MIN, config.VOL_RANGE_MAX])[0]} - {safe_get(s.filters, 'vol_range', default=[config.VOL_RANGE_MIN, config.VOL_RANGE_MAX])[1]}\n"
            f"Timeframe aktif: {config.DEFAULT_INTERVAL}\n"
            f"Session: London {config.LONDON_START}-{config.LONDON_END}, NY {config.NY_START}-{config.NY_END}, Asia {config.ASIAN_START}-{config.ASIAN_END}\n"
            f"Pairs: {', '.join(self.trading_pairs)}\n"
            f"Loop Interval: {config.LOOP_INTERVAL}s\n"
            f"Telegram: {config.ENABLE_TELEGRAM}\n\n"
            f"🔒 *PRICE VALIDATION*\n"
            f"Max Entry Deviation: {config.SIGNAL_MAX_ENTRY_DEVIATION:.1%}\n"
            f"Max SL Deviation: {config.SIGNAL_MAX_SL_DEVIATION:.1%}\n"
            f"Max TP Deviation: {config.SIGNAL_MAX_TP_DEVIATION:.1%}\n"
            f"Execution Deviation: {config.SIGNAL_EXECUTION_DEVIATION:.1%}"
        )
        return settings

    # TODO: Implementasi websocket event handler jika ingin fitur tambahan (saat ini tidak digunakan)
    # (Kosong, tidak ada pass)

if __name__ == "__main__":
    ICTBot.instance = None
    bot = ICTBot()
    
    # Set bot instance reference for Telegram
    telegram.set_bot_instance(bot)
    
    # Start Telegram polling (no need for separate handler)
    telegram.start_polling()
    
    ICTBot.instance = bot
    bot.start()