from datetime import datetime, timedelta
from utils.logger import logger
from core.config import config
from binance.client import Client
import time
import threading
from collections import defaultdict
import statistics
from integrations.telegram import telegram
import decimal
import os
import json

def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d

class EnhancedICTTrader:
    def __init__(self):
        self.client = Client(api_key=config.BINANCE_API_KEY, api_secret=config.BINANCE_SECRET)
        self.symbol = "BTCUSDT"  # Default symbol, tetap bisa diubah untuk multi-pair
        self.active_positions = {}
        self.daily_trades = 0
        self.leverage = config.LEVERAGE  # Use leverage from config
        self.performance = {
            "wins": 0,
            "losses": 0,
            "consecutive_losses": 0,
            "daily_pnl": 0.0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "max_balance": 0.0,
            "min_balance": float('inf')
        }
        
        # Enhanced features
        self.max_daily_trades = config.MAX_DAILY_TRADES
        self.max_open_positions = config.MAX_OPEN_POSITIONS
        self.max_consecutive_losses = 5
        self.connection_retry_count = 0
        self.last_heartbeat = datetime.utcnow()
        self.market_volatility = 0.0
        self.order_cache = {}
        
        # Rate limiting
        self.api_call_times = defaultdict(list)
        self.max_calls_per_minute = 50
        
        # State management
        self.stuck_alert_sent = set()
        self.last_entry_time = {}
        self._last_balance_error_time = 0
        
        # Telegram spam prevention
        self._last_telegram_alerts = {
            'circuit_breaker_balance': 0,
            'circuit_breaker_drawdown': 0,
            'circuit_breaker_losses': 0,
            'circuit_breaker_api': 0,
            'circuit_breaker_positions': 0,
            'emergency_shutdown': 0,
            'balance_error': 0
        }
        self._telegram_cooldown = config.TELEGRAM_COOLDOWN  # Configurable cooldown
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        # Restore open positions from Binance Futures
        try:
            logger.info("[INIT] Restoring open positions...")
            try:
                open_positions = self.client.futures_position_information()
            except Exception as e:
                logger.error(f"[INIT] Error restoring open positions: {e}")
                open_positions = []
            for pos in open_positions:
                try:
                    if abs(float(safe_get(pos, 'positionAmt', default=0))) > 0:
                        symbol = safe_get(pos, 'symbol', default='')
                        entry = float(safe_get(pos, 'entryPrice', default=0))
                        size = abs(float(safe_get(pos, 'positionAmt', default=0)))
                        direction = 'BUY' if float(safe_get(pos, 'positionAmt', default=0)) > 0 else 'SELL'
                        # Fetch open orders for this symbol
                        try:
                            open_orders = self.client.futures_get_open_orders(symbol=symbol)
                        except Exception as e:
                            logger.error(f"[INIT] Error fetching open orders for {symbol}: {e}")
                            open_orders = []
                        sl_order = None
                        tp1_order = None
                        tp2_order = None
                        # Identify SL/TP orders
                        limit_orders = [o for o in open_orders if safe_get(o, 'type', default='') == 'LIMIT']
                        stop_orders = [o for o in open_orders if safe_get(o, 'type', default='') == 'STOP_MARKET']
                        for o in stop_orders:
                            if (direction == 'BUY' and float(safe_get(o, 'stopPrice', default=0)) < entry) or (direction == 'SELL' and float(safe_get(o, 'stopPrice', default=0)) > entry):
                                sl_order = o
                        tp_candidates = []
                        for o in limit_orders:
                            if (direction == 'BUY' and float(safe_get(o, 'price', default=0)) > entry) or (direction == 'SELL' and float(safe_get(o, 'price', default=0)) < entry):
                                tp_candidates.append(o)
                        tp_candidates.sort(key=lambda x: abs(float(safe_get(x, 'price', default=0)) - entry))
                        if len(tp_candidates) > 0:
                            tp1_order = tp_candidates[0]
                        if len(tp_candidates) > 1:
                            tp2_order = tp_candidates[1]
                        trailing_order = None
                        for o in open_orders:
                            if safe_get(o, 'type', default='') == 'TRAILING_STOP_MARKET':
                                trailing_order = o
                        sl_moved_to_be = False
                        if sl_order and abs(float(safe_get(sl_order, 'stopPrice', default=0)) - entry) < 1e-6:
                            sl_moved_to_be = True
                        trailing_active = trailing_order is not None
                        self.active_positions[symbol] = {
                            'symbol': symbol,
                            'entry': entry,
                            'sl': float(safe_get(sl_order, 'stopPrice', default=0)) if sl_order else None,
                            'tp1': float(safe_get(tp1_order, 'price', default=0)) if tp1_order else None,
                            'tp2': float(safe_get(tp2_order, 'price', default=0)) if tp2_order else None,
                            'size': size,
                            'direction': direction,
                            'opened_at': None,
                            'orders': {
                                'sl_order': sl_order,
                                'tp1_order': tp1_order,
                                'tp2_order': tp2_order,
                                'trailing_order': trailing_order
                            },
                            'sl_moved_to_be': sl_moved_to_be,
                            'tp1_hit': False,
                            'tp2_hit': False,
                            'trailing_active': trailing_active,
                            'market_volatility_at_entry': None,
                            'last_price_check': None,
                            'price_check_failures': 0,
                            'notifications': {
                                'tp1_notified': False,
                                'tp2_notified': False,
                                'sl_notified': False,
                                'trailing_notified': False,
                                'sl_be_notified': False
                            }
                        }
                except Exception as e:
                    logger.error(f"[INIT] Error processing open position: {e}")
            if self.active_positions:
                from integrations.telegram import telegram
                telegram.send_message(f"♻️ Bot restart: {len(self.active_positions)} open position(s) with SL/TP restored and will be monitored.")
        except Exception as e:
            logger.error(f"Failed to restore open positions/orders on startup: {e}")
        # === Log initial balance at startup ===
        try:
            # Ensure logs directory exists
            os.makedirs("logs", exist_ok=True)
            balance = self.get_account_balance()
            logger.info(f"[STARTUP] Initial balance: {balance:.2f} USDT")
            with open("logs/equity.log", "a") as f:
                f.write(f"[{datetime.utcnow()}] STARTUP BALANCE: {balance:.2f} USDT\n")
        except Exception as e:
            logger.error(f"[STARTUP] Failed to log initial balance: {e}")

    def save_state(self, filename="state.json"):
        try:
            state = {
                "stuck_alert_sent": list(self.stuck_alert_sent),
                "last_entry_time": {k: v.isoformat() for k, v in self.last_entry_time.items()},
                "daily_trades": self.daily_trades
            }
            with open(filename, "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def load_state(self, filename="state.json"):
        try:
            if not os.path.exists(filename):
                return
            with open(filename, "r") as f:
                state = json.load(f)
            self.stuck_alert_sent = set(state.get("stuck_alert_sent", []))
            from datetime import datetime
            self.last_entry_time = {}
            for k, v in state.get("last_entry_time", {}).items():
                if v is not None:
                    try:
                        self.last_entry_time[k] = datetime.fromisoformat(v)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid datetime format for {k}: {v}")
                        continue
            self.daily_trades = state.get("daily_trades", 0)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    def _monitoring_loop(self):
        """Background monitoring for health checks and maintenance"""
        last_log_hour = None
        last_cleanup_hour = None
        while self.monitoring_active:
            try:
                self._health_check()
                self._cleanup_old_api_calls()
                self._update_market_volatility()
                self._daily_summary_check()
                
                # Log equity every hour
                now = datetime.utcnow()
                if last_log_hour is None or now.hour != last_log_hour:
                    self.log_equity(event="PERIODIC")
                    last_log_hour = now.hour
                
                # ✅ Cleanup orphaned positions every 2 hours
                if last_cleanup_hour is None or (now - last_cleanup_hour).total_seconds() > 7200:  # 2 hours
                    self.cleanup_orphaned_positions()
                    last_cleanup_hour = now
                
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)

    def _health_check(self):
        """Perform health checks"""
        try:
            # Test connection
            self.client.futures_account_balance()
            self.last_heartbeat = datetime.utcnow()
            self.connection_retry_count = 0
            
            # Check for stuck positions
            self._check_stuck_positions()
            
        except Exception as e:
            self.connection_retry_count += 1
            logger.warning(f"Health check failed (retry {self.connection_retry_count}): {e}")
            
            if self.connection_retry_count >= 5:
                telegram.send_message(
                    f"🚨 *CONNECTION ISSUE*\n"
                    f"Bot connection unstable\n"
                    f"Retry count: {self.connection_retry_count}"
                )

    def _cleanup_old_api_calls(self):
        """Clean up old API call timestamps"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=1)
        for endpoint in self.api_call_times:
            self.api_call_times[endpoint] = [
                call_time for call_time in self.api_call_times[endpoint]
                if call_time > cutoff_time
            ]

    def _update_market_volatility(self):
        """Update market volatility measure"""
        try:
            # Get recent klines for volatility calculation
            klines = self.client.futures_klines(
                symbol=self.symbol,
                interval='1m',
                limit=100
            )
            
            closes = [float(k[4]) for k in klines]
            if len(closes) > 1:
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                self.market_volatility = statistics.stdev(returns) * 100
                
        except Exception as e:
            logger.error(f"Failed to update volatility: {e}")

    def _daily_summary_check(self):
        """Check if it's time to send daily summary and reset counters"""
        try:
            now = datetime.utcnow()
            current_date = now.strftime('%Y-%m-%d')
            
            # Check if we need to reset daily counters
            if not hasattr(self, '_last_reset_date') or self._last_reset_date != current_date:
                self._reset_daily_counters()
                self._last_reset_date = current_date
                
                # Send daily summary if we have trades
                if self.daily_trades > 0:
                    self._send_daily_summary()
                    
        except Exception as e:
            logger.error(f"Daily summary check error: {e}")

    def _reset_daily_counters(self):
        """Reset daily counters and performance metrics"""
        try:
            logger.info("[DAILY RESET] Resetting daily counters...")
            
            # Reset daily trade counter
            self.daily_trades = 0
            
            # Reset daily PnL
            self.performance['daily_pnl'] = 0.0
            
            # Reset daily returns
            if 'daily_returns' in self.performance:
                self.performance['daily_returns'] = []
            
            # Reset last entry times
            if hasattr(self, 'last_entry_time'):
                self.last_entry_time = {}
            
            # Reset stuck alert flags
            if hasattr(self, 'stuck_alert_sent'):
                self.stuck_alert_sent = set()
            
            # Save state after reset
            self.save_state()
            
            logger.info("[DAILY RESET] Daily counters reset completed")
            
            if config.ENABLE_TELEGRAM:
                telegram.send_message("🔄 Daily counters reset - ready for new trading day!")
                
        except Exception as e:
            logger.error(f"Error resetting daily counters: {e}")

    def _send_daily_summary(self):
        """Send comprehensive daily summary"""
        try:
            performance = self.get_enhanced_performance()
            
            # Calculate daily statistics
            daily_trades = self.daily_trades
            daily_pnl = performance.get('daily_pnl', 0)
            win_rate = performance.get('win_rate', 0)
            
            # Get current balance
            current_balance = self.get_account_balance()
            
            # Calculate daily return
            daily_return = 0
            if performance.get('max_balance', 0) > 0:
                daily_return = ((current_balance - performance['max_balance']) / performance['max_balance']) * 100
            
            message = f"""
📊 *DAILY SUMMARY*

📅 Date: {datetime.utcnow().strftime('%Y-%m-%d')}
🎯 Daily Trades: {daily_trades}
💰 Daily PnL: ${daily_pnl:.2f}
📈 Daily Return: {daily_return:.2f}%
🎯 Win Rate: {win_rate:.1f}%

📊 *PERFORMANCE METRICS*:
• Total Trades: {performance.get('total_trades', 0)}
• Profit Factor: {performance.get('profit_factor', 0):.2f}
• Sharpe Ratio: {performance.get('sharpe_ratio', 0):.2f}
• Current Drawdown: {performance.get('current_drawdown', 0):.2f}%

💼 *ACCOUNT STATUS*:
• Current Balance: ${current_balance:.2f}
• Max Balance: ${performance.get('max_balance', 0):.2f}
• Active Positions: {performance.get('active_positions', 0)}

{'🎉 Excellent day!' if daily_pnl > 0 else '📉 Tough day, but tomorrow is another opportunity!'}
            """
            
            if config.ENABLE_TELEGRAM:
                telegram.send_message(message)
                
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    def _rate_limit_check(self, endpoint):
        """Check API rate limits"""
        now = datetime.utcnow()
        self.api_call_times[endpoint].append(now)
        
        recent_calls = len(self.api_call_times[endpoint])
        if recent_calls >= self.max_calls_per_minute:
            logger.warning(f"Rate limit approaching for {endpoint}")
            return False
        return True

    def _execute_with_retry(self, func, *args, max_retries=None, delay=None, **kwargs):
        from core.config import config
        max_retries = max_retries or config.BINANCE_MAX_RETRIES
        delay = delay or config.BINANCE_RETRY_DELAY
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Cek jika error karena rate limit (HTTP 429)
                if hasattr(e, 'status_code') and getattr(e, 'status_code', None) == 429:
                    logger.warning(f"Rate limit hit (429) on {func.__name__}, attempt {attempt+1}")
                    time.sleep(delay * (2 ** attempt))
                else:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}")
                    time.sleep(delay * (2 ** attempt))
        logger.error(f"Function {func.__name__} failed after {max_retries} attempts.")
        # (Opsional) telegram.send_message(f"Binance API error berulang pada {func.__name__}")
        return None

    def get_account_balance(self, symbol=None):
        """Get USDT balance from futures account with retry"""
        symbol = symbol or self.symbol
        if not symbol:
            logger.error("Symbol belum di-set pada EnhancedICTTrader!")
            raise ValueError("Symbol belum di-set pada EnhancedICTTrader!")
        try:
            if not self._rate_limit_check('balance'):
                time.sleep(1)
                
            balances = self._execute_with_retry(self.client.futures_account_balance)
            for b in balances:
                if b['asset'] == 'USDT':
                    balance = float(b['balance'])
                    # Update max/min balance for drawdown tracking
                    if balance > self.performance['max_balance']:
                        self.performance['max_balance'] = balance
                    if balance < self.performance['min_balance']:
                        self.performance['min_balance'] = balance
                    return balance
            return 0.0
        except Exception as e:
            import time as _time
            now = _time.time()
            if now - self._last_balance_error_time > 300:  # 5 menit
                self._send_telegram_alert('balance_error', f"❌ Gagal cek saldo: {e}")
                self._last_balance_error_time = now
            logger.error(f"Failed to get balance: {e}")
            return 0.0

    def _send_telegram_alert(self, alert_type, message):
        """Send Telegram alert with cooldown to prevent spam"""
        try:
            import time
            current_time = time.time()
            last_alert_time = self._last_telegram_alerts.get(alert_type, 0)
            
            if current_time - last_alert_time > self._telegram_cooldown:
                if config.ENABLE_TELEGRAM:
                    telegram.send_message(message)
                self._last_telegram_alerts[alert_type] = current_time
                logger.info(f"[TELEGRAM] Alert sent: {alert_type}")
            else:
                logger.debug(f"[TELEGRAM] Alert suppressed (cooldown): {alert_type}")
                
        except Exception as e:
            logger.error(f"[TELEGRAM] Error sending alert: {e}")

    def check_circuit_breaker(self):
        """Enhanced circuit breaker with multiple safety checks"""
        try:
            # Check consecutive losses
            if self.performance['consecutive_losses'] >= 5:
                logger.warning("[CIRCUIT BREAKER] 5 consecutive losses - trading paused")
                self._send_telegram_alert('circuit_breaker_losses', 
                    "🚨 CIRCUIT BREAKER: 5 consecutive losses - trading paused for safety")
                return False
            
            # Check drawdown limit
            current_drawdown = self.get_drawdown()
            if current_drawdown > config.MAX_DRAWDOWN:
                logger.warning(f"[CIRCUIT BREAKER] Drawdown {current_drawdown:.2f}% exceeds limit {config.MAX_DRAWDOWN}%")
                self._send_telegram_alert('circuit_breaker_drawdown', 
                    f"🚨 CIRCUIT BREAKER: Drawdown {current_drawdown:.2f}% exceeds limit")
                return False
            
            # Check balance minimum
            balance = self.get_account_balance()
            if balance < config.MIN_BALANCE:
                logger.warning(f"[CIRCUIT BREAKER] Balance too low: ${balance:.2f} (min: ${config.MIN_BALANCE})")
                self._send_telegram_alert('circuit_breaker_balance', 
                    f"🚨 CIRCUIT BREAKER: Balance too low (${balance:.2f}) - minimum required: ${config.MIN_BALANCE}")
                return False
            
            # Check API connection health
            if self.connection_retry_count > 10:
                logger.warning("[CIRCUIT BREAKER] Too many API connection failures")
                self._send_telegram_alert('circuit_breaker_api', 
                    "🚨 CIRCUIT BREAKER: API connection issues")
                return False
            
            # Check for stuck positions
            stuck_positions = 0
            for pos_id, position in self.active_positions.items():
                if not self.verify_position_active(pos_id):
                    stuck_positions += 1
            
            if stuck_positions > 2:
                logger.warning(f"[CIRCUIT BREAKER] Too many stuck positions: {stuck_positions}")
                self._send_telegram_alert('circuit_breaker_positions', 
                    f"🚨 CIRCUIT BREAKER: {stuck_positions} stuck positions detected")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[CIRCUIT BREAKER] Error in circuit breaker check: {e}")
            return False  # Fail safe - don't trade if we can't check

    def emergency_shutdown(self, reason="Unknown"):
        """Emergency shutdown with cleanup"""
        try:
            logger.error(f"[EMERGENCY SHUTDOWN] Triggered: {reason}")
            
            self._send_telegram_alert('emergency_shutdown', f"🚨 EMERGENCY SHUTDOWN: {reason}")
            
            # Close all positions
            for pos_id, position in list(self.active_positions.items()):
                try:
                    self.cancel_all_orders(position)
                    logger.info(f"[EMERGENCY] Cancelled orders for position {pos_id}")
                except Exception as e:
                    logger.error(f"[EMERGENCY] Failed to cancel orders for {pos_id}: {e}")
            
            # Save state
            self.save_state()
            
            # Stop monitoring
            self.monitoring_active = False
            
            logger.info("[EMERGENCY] Shutdown completed")
            
        except Exception as e:
            logger.error(f"[EMERGENCY] Error during shutdown: {e}")

    def recover_from_error(self, error_type, error_msg):
        """Recover from different types of errors"""
        try:
            logger.warning(f"[RECOVERY] Attempting to recover from {error_type}: {error_msg}")
            
            if error_type == "API_ERROR":
                # Wait and retry
                time.sleep(30)
                self.connection_retry_count += 1
                
            elif error_type == "POSITION_ERROR":
                # Cleanup orphaned positions
                self.cleanup_orphaned_positions()
                
            elif error_type == "ORDER_ERROR":
                # Cancel all pending orders
                for pos_id, position in list(self.active_positions.items()):
                    self.cancel_all_orders(position)
                
            elif error_type == "BALANCE_ERROR":
                # Check balance and pause if needed
                balance = self.get_account_balance()
                if balance < 10:
                    logger.error("[RECOVERY] Balance too low, cannot recover")
                    return False
            
            # Reset error counters if recovery successful
            if self.connection_retry_count > 0:
                self.connection_retry_count = max(0, self.connection_retry_count - 1)
            
            logger.info(f"[RECOVERY] Recovery from {error_type} completed")
            return True
            
        except Exception as e:
            logger.error(f"[RECOVERY] Error during recovery: {e}")
            return False

    def calculate_adaptive_position_size(self, signal, base_risk_percent=2):
        """Calculate position size with volatility adjustment and small balance handling"""
        try:
            # Base calculation
            balance = self.get_account_balance()
            
            # For small balances, use more conservative approach
            if balance < config.SMALL_BALANCE_THRESHOLD:
                logger.info(f"Small balance detected: ${balance:.2f}, using conservative settings")
                base_risk_percent = min(base_risk_percent, config.SMALL_BALANCE_RISK)
                # Use smaller leverage for small balance
                effective_leverage = min(self.leverage, config.SMALL_BALANCE_LEVERAGE)
                logger.info(f"Using reduced leverage: {effective_leverage}x (original: {self.leverage}x)")
            else:
                effective_leverage = self.leverage
            
            # Adjust risk based on volatility
            volatility_factor = min(self.market_volatility / 100, 0.5)
            adjusted_risk = base_risk_percent * (1 - volatility_factor)
            
            # Adjust based on consecutive losses
            if self.performance['consecutive_losses'] > 0:
                loss_factor = 0.9 ** self.performance['consecutive_losses']
                adjusted_risk *= loss_factor
            
            risk_amount = balance * (adjusted_risk / 100)
            risk_per_unit = abs(signal.entry - signal.sl)
            
            if risk_per_unit <= 0:
                logger.error("Invalid risk calculation - SL too close to entry")
                return 0
                
            position_size = risk_amount / risk_per_unit
            
            # Get precision for this symbol
            precision = self.get_quantity_precision(self.symbol)
            
            # Round to proper precision
            position_size = round(position_size, precision)
            
            # Ensure minimum position size
            if position_size < config.MIN_POSITION_SIZE:
                logger.warning(f"Position size too small: {position_size}, using minimum: {config.MIN_POSITION_SIZE}")
                position_size = config.MIN_POSITION_SIZE
            
            logger.info(f"Calculated position size: {position_size} (precision: {precision}, balance: ${balance:.2f}, leverage: {effective_leverage}x)")
            return position_size
            
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return 0

    def verify_position_active(self, position_id):
        """Enhanced position verification with comprehensive checks"""
        try:
            # Get position from Binance
            positions = self._execute_with_retry(
                self.client.futures_position_information,
                symbol=position_id  # Use position_id as symbol
            )
            
            if not positions:
                logger.warning(f"[POSITION] No position data received for {position_id}")
                return False
            
            # Find our position
            for pos in positions:
                if abs(float(safe_get(pos, 'positionAmt', default=0))) > 0:
                    # Position exists on Binance
                    position_amt = float(safe_get(pos, 'positionAmt', default=0))
                    entry_price = float(safe_get(pos, 'entryPrice', default=0))
                    
                    # Validate against our tracking
                    tracked_position = self.active_positions.get(position_id)
                    if tracked_position:
                        tracked_size = safe_get(tracked_position, 'size', default=0)
                        tracked_entry = safe_get(tracked_position, 'entry', default=0)
                        
                        # Check if position matches our tracking
                        size_diff = abs(position_amt) - tracked_size
                        entry_diff = abs(entry_price - tracked_entry)
                        
                        if size_diff > 0.001 or entry_diff > 0.01:  # Allow small differences
                            logger.warning(f"[POSITION] Position mismatch for {position_id}: size_diff={size_diff}, entry_diff={entry_diff}")
                            # Update our tracking with real data
                            self.active_positions[position_id].update({
                                'size': abs(position_amt),
                                'entry': entry_price,
                                'last_validation': datetime.utcnow()
                            })
                    
                    return True
            
            # Position not found on Binance
            logger.warning(f"[POSITION] Position {position_id} not found on Binance")
            return False
            
        except Exception as e:
            logger.error(f"[POSITION] Error verifying position {position_id}: {e}")
            return False

    def cleanup_orphaned_positions(self):
        """Clean up positions that no longer exist on Binance"""
        try:
            orphaned_positions = []
            
            for pos_id, position in list(self.active_positions.items()):
                if not self.verify_position_active(pos_id):
                    orphaned_positions.append(pos_id)
                    logger.warning(f"[CLEANUP] Orphaned position detected: {pos_id}")
            
            # Remove orphaned positions
            for pos_id in orphaned_positions:
                del self.active_positions[pos_id]
                logger.info(f"[CLEANUP] Removed orphaned position: {pos_id}")
            
            if orphaned_positions and config.ENABLE_TELEGRAM:
                telegram.send_message(
                    f"🧹 *POSITION CLEANUP*\n"
                    f"Removed {len(orphaned_positions)} orphaned position(s)\n"
                    f"Active positions: {len(self.active_positions)}"
                )
                
        except Exception as e:
            logger.error(f"[CLEANUP] Error cleaning orphaned positions: {e}")

    def cancel_all_orders(self, position):
        """Cancel all pending orders for a position"""
        cancelled_orders = []
        for order_type, order in safe_get(position, 'orders', default={}).items():
            if order and 'orderId' in order:
                try:
                    self.client.futures_cancel_order(
                        symbol=self.symbol,
                        orderId=safe_get(order, 'orderId', default=0)
                    )
                    cancelled_orders.append(order_type)
                except Exception as e:
                    logger.warning(f"Failed to cancel {order_type} order: {e}")
        
        if cancelled_orders:
            logger.info(f"Cancelled orders: {cancelled_orders}")
        return cancelled_orders

    def get_quantity_precision(self, symbol):
        """Get quantity precision for symbol with enhanced error handling"""
        try:
            info = self.client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            step_size = float(f['stepSize'])
                            if step_size == 0:
                                logger.warning(f"Invalid step size for {symbol}: {step_size}")
                                return 3
                            
                            # Calculate precision from step size
                            precision = 0
                            while step_size < 1:
                                step_size *= 10
                                precision += 1
                            
                            logger.info(f"Precision for {symbol}: {precision} (step size: {f['stepSize']})")
                            return precision
            
            logger.warning(f"Symbol {symbol} not found in exchange info, using default precision 3")
            return 3
            
        except Exception as e:
            logger.error(f"Error getting precision for {symbol}: {e}")
            return 3  # Safe default

    def place_market_order_enhanced(self, side, quantity):
        """Enhanced market order with validation"""
        try:
            if not self._rate_limit_check('market_order'):
                time.sleep(1)
                
            # Validate quantity
            if quantity <= 0:
                logger.error("Invalid quantity for market order")
                return None
                
            precision = self.get_quantity_precision(self.symbol)
            quantity = round(quantity, precision)

            order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            # Cache order for tracking
            self.order_cache[safe_get(order, 'orderId', default=0)] = order
            logger.info(f"Market order placed: {order}")
            return order
            
        except Exception as e:
            logger.error(f"Market order error: {e}")
            return None

    def place_stop_market_order_enhanced(self, side, stop_price, quantity):
        """Enhanced stop market order with validation"""
        try:
            if not self._rate_limit_check('stop_order'):
                time.sleep(1)
                
            # Validate parameters
            if quantity <= 0 or stop_price <= 0:
                logger.error("Invalid parameters for stop order")
                return None
                
            precision = self.get_quantity_precision(self.symbol)
            quantity = round(quantity, precision)

            order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=side,
                type='STOP_MARKET',
                stopPrice=round(stop_price, 2),
                quantity=quantity,
                timeInForce='GTC'
            )
            
            self.order_cache[safe_get(order, 'orderId', default=0)] = order
            logger.info(f"Stop market order placed: {order}")
            return order
            
        except Exception as e:
            logger.error(f"Stop market order error: {e}")
            return None

    def place_market_tp_order_enhanced(self, side, quantity):
        """Enhanced market TP order with validation and error handling"""
        try:
            if not self._rate_limit_check('market_tp_order'):
                time.sleep(1)
            # Validate parameters
            if quantity <= 0:
                logger.error("Invalid quantity for market TP order")
                return None
            precision = self.get_quantity_precision(self.symbol)
            quantity = round(quantity, precision)
            # Place market order untuk TP dengan reduceOnly=True
            order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=side,
                type='MARKET',
                quantity=quantity,
                reduceOnly=True
            )
            if not order:
                logger.error("Market TP order gagal, tidak ada response dari Binance.")
                return None
            self.order_cache[safe_get(order, 'orderId', default=0)] = order
            logger.info(f"Market TP order placed (reduceOnly): {order}")
            return order
        except Exception as e:
            logger.error(f"Market TP order error: {e}")
            return None

    def place_limit_order_enhanced(self, side, price, quantity):
        """Enhanced limit order with validation and pro error handling"""
        try:
            if not self._rate_limit_check('limit_order'):
                time.sleep(1)
            # Validate parameters
            if quantity <= 0 or price <= 0:
                logger.error("Invalid parameters for limit order")
                return None
            precision = self.get_quantity_precision(self.symbol)
            quantity = round(quantity, precision)
            # Tick size validation
            info = self.client.futures_exchange_info()
            tick_size = 0.01
            for s in info['symbols']:
                if s['symbol'] == self.symbol:
                    for f in s['filters']:
                        if f['filterType'] == 'PRICE_FILTER':
                            tick_size = float(f['tickSize'])
            price = round(round(price / tick_size) * tick_size, 8)
            # Cek deviasi harga limit dari harga pasar
            current_price = self.get_current_price_enhanced(self.symbol)
            max_deviation = 0.01  # 1% dari harga pasar
            if abs(price - current_price) / current_price > max_deviation:
                logger.error(f"Limit price terlalu jauh dari harga pasar: {price} vs {current_price}")
                return None
            # Tambahkan reduceOnly agar TP benar-benar close posisi
            order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=side,
                type='LIMIT',
                price=price,
                quantity=quantity,
                timeInForce='GTC',
                reduceOnly=True
            )
            if not order:
                logger.error("Limit order gagal, tidak ada response dari Binance.")
                return None
            self.order_cache[safe_get(order, 'orderId', default=0)] = order
            logger.info(f"Limit order placed (reduceOnly): {order}")
            return order
        except Exception as e:
            logger.error(f"Limit order error: {e}")
            return None

    def set_leverage_api(self, symbol, leverage=None):
        """Set leverage for the symbol via Binance API"""
        try:
            leverage = leverage or self.leverage
            result = self.client.futures_change_leverage(symbol=symbol, leverage=int(leverage))
            logger.info(f"Leverage for {symbol} set to {leverage}x via API. Response: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to set leverage for {symbol} via API: {e}")
            return None

    def log_equity(self, event="PERIODIC"):
        try:
            # Ensure logs directory exists
            os.makedirs("logs", exist_ok=True)
            equity = self.get_account_balance()
            log_line = f"[{datetime.utcnow()}] Equity: {equity:.2f} USDT (after {event} {self.symbol})\n"
            with open("logs/equity.log", "a") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to log equity: {e}")

    def execute_entry_enhanced(self, signal):
        """Enhanced entry execution with comprehensive checks and auto leverage"""
        try:
            # Limitasi jumlah entry harian
            if self.daily_trades >= self.max_daily_trades:
                logger.warning(f"[ENTRY LIMIT] Entry harian sudah mencapai {self.max_daily_trades}, skip entry baru.")
                return False
            # Limitasi jumlah posisi aktif bersamaan
            if len(self.active_positions) >= self.max_open_positions:
                logger.warning(f"[POSITION LIMIT] Posisi aktif sudah {self.max_open_positions}, skip entry baru.")
                return False
            # Anti-double entry: cek apakah sudah ada posisi aktif untuk symbol ini
            for pos in self.active_positions.values():
                if pos.get('symbol') == self.symbol:
                    logger.warning(f"[ANTI-DOUBLE ENTRY] Sudah ada posisi aktif untuk {self.symbol}, skip entry baru.")
                    return False
            # Circuit breaker check
            if not self.check_circuit_breaker():
                return False
            # AUTO SET LEVERAGE VIA API
            self.set_leverage_api(self.symbol, self.leverage)
            # Calculate adaptive position size
            position_size = self.calculate_adaptive_position_size(signal)
            if position_size <= 0:
                logger.error("Invalid position size calculated")
                return False
            # Check margin
            if not self.check_margin_sufficient(position_size, signal.entry):
                return False
            side = 'BUY' if signal.direction == 'BUY' else 'SELL'
            opposite_side = 'SELL' if side == 'BUY' else 'BUY'
            # 1. Place MARKET entry order
            entry_order = self.place_market_order_enhanced(side, position_size)
            if not entry_order:
                logger.error("Failed to place entry order")
                telegram.send_message(f"❌ ENTRY FAILED! Order market tidak masuk ke Binance untuk {self.symbol}.")
                return False
            # Ambil harga entry/orderId real dari respons Binance
            entry_price_real = safe_get(entry_order, 'avgFillPrice', default=safe_get(entry_order, 'price', default=signal.entry))
            order_id = safe_get(entry_order, 'orderId', default='N/A')
            
            # ✅ DYNAMIC SL/TP CALCULATION berdasarkan entry real
            risk_amount = abs(entry_price_real - signal.sl)  # Risk dari sinyal original
            
            # Hitung SL/TP baru berdasarkan entry real untuk jaga RR konsisten
            if signal.direction == 'BUY':
                sl_real = entry_price_real - risk_amount
                tp1_real = entry_price_real + (risk_amount * 1.2)  # RR 1:1.2
                tp2_real = entry_price_real + (risk_amount * 2.0)  # RR 1:2
            else:  # SELL
                sl_real = entry_price_real + risk_amount
                tp1_real = entry_price_real - (risk_amount * 1.2)  # RR 1:1.2
                tp2_real = entry_price_real - (risk_amount * 2.0)  # RR 1:2
            
            # 2. Place STOP_MARKET for SL dengan harga real
            sl_order = None
            if 'orders' in entry_order and entry_order['orders'].get('sl_order'):
                # Cancel SL lama jika ada
                self.cancel_all_orders({'orders': {'sl_order': entry_order['orders']['sl_order']}})
            sl_order = self.place_stop_market_order_enhanced(opposite_side, sl_real, position_size)
            if not sl_order:
                logger.warning("Failed to place SL order - CRITICAL!")
                # Cancel entry if SL placement fails
                self.cancel_all_orders({'orders': {'entry': entry_order}})
                return False
            # 3. Place MARKET orders for TP1 (70%) and TP2 (30%) - lebih mudah kena
            tp1_size = round(position_size * 0.7, 4)
            tp2_size = round(position_size * 0.3, 4)
            tp1_order = self.place_market_tp_order_enhanced(opposite_side, tp1_size)
            tp2_order = self.place_market_tp_order_enhanced(opposite_side, tp2_size)
            # 4. Track the position dengan harga real
            self.track_position_enhanced(signal, entry_order, position_size, {
                'sl_order': sl_order,
                'tp1_order': tp1_order,
                'tp2_order': tp2_order,
                'entry_order': entry_order
            }, entry_price_real, sl_real, tp1_real, tp2_real)
            self.daily_trades += 1
            # Enhanced telegram notification
            wib_now = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
            telegram.send_message(
                f"🚀 *ENTRY EXECUTED*\n"
                f"Order ID: {order_id}\n"
                f"📌 PAIR: {self.symbol}\n"
                f"🎯 Direction: {signal.direction}\n"
                f"💰 Entry (real): ${entry_price_real:.2f}\n"
                f"🛑 SL (real): ${sl_real:.2f}\n"
                f"🎯 TP1: MARKET ORDER (70%) - RR 1:1.2\n"
                f"🎯 TP2: MARKET ORDER (30%) - RR 1:2\n"
                f"📊 Size: {position_size}\n"
                f"💹 Market Vol: {self.market_volatility:.2f}%\n"
                f"🔢 Daily Trades: {self.daily_trades}/{self.max_daily_trades}\n"
                f"🕒 Waktu: {wib_now} WIB"
            )
            # Log equity after entry
            self.log_equity(event="ENTRY")
            # Save state after successful entry
            self.save_state()
            return True
        except Exception as e:
            logger.error(f"Execute entry error: {e}")
            return False

    def track_position_enhanced(self, signal, entry_order, size, orders, entry_real=None, sl_real=None, tp1_real=None, tp2_real=None):
        """Enhanced position tracking with more metadata"""
        position_id = safe_get(entry_order, 'orderId', default=0)
        
        # ✅ Gunakan harga real jika tersedia, fallback ke harga sinyal
        entry_price = entry_real if entry_real is not None else signal.entry
        sl_price = sl_real if sl_real is not None else signal.sl
        tp1_price = tp1_real if tp1_real is not None else signal.tp1
        tp2_price = tp2_real if tp2_real is not None else signal.tp2
        
        self.active_positions[position_id] = {
            'symbol': self.symbol,
            'entry': entry_price,
            'sl': sl_price,
            'tp1': tp1_price,
            'tp2': tp2_price,
            'size': size,
            'direction': signal.direction,
            'opened_at': datetime.utcnow(),
            'orders': orders,
            'sl_moved_to_be': False,
            'tp1_hit': False,
            'tp2_hit': False,
            'trailing_active': False,
            'market_volatility_at_entry': self.market_volatility,
            'last_price_check': datetime.utcnow(),
            'price_check_failures': 0,
            'notifications': {
                'tp1_notified': False,
                'tp2_notified': False,
                'sl_notified': False,
                'trailing_notified': False,
                'sl_be_notified': False
            }
        }

    def should_move_sl_to_be_enhanced(self, position, current_price):
        """Enhanced SL+ logic with time and volatility considerations"""
        entry = safe_get(position, 'entry', default=0)
        tp1 = safe_get(position, 'tp1', default=0)
        direction = safe_get(position, 'direction', default='')
        
        # Time factor - more conservative early in trade
        time_factor = (datetime.utcnow() - safe_get(position, 'opened_at', default=datetime.utcnow())).seconds / 3600
        volatility_threshold = 0.8 if time_factor > 2 else 0.75
        
        # Volatility adjustment
        if self.market_volatility > safe_get(position, 'market_volatility_at_entry', default=0) * 1.5:
            volatility_threshold = 0.85  # More conservative in high volatility
        
        # Calculate profit target
        if direction == 'BUY':
            profit_target = entry + volatility_threshold * (tp1 - entry)
            return current_price >= profit_target
        else:  # SELL
            profit_target = entry - volatility_threshold * (entry - tp1)
            return current_price <= profit_target

    def _check_stuck_positions(self):
        """Check for positions that haven't been updated recently"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        for pos_id, position in self.active_positions.items():
            last_price_check = safe_get(position, 'last_price_check', default=None)
            if last_price_check is not None and last_price_check < cutoff_time:
                logger.warning(f"Position {pos_id} hasn't been updated recently")
                telegram.send_message(
                    f"⚠️ *POSITION ALERT*\n"
                    f"Position {pos_id} may be stuck\n"
                    f"Last update: {last_price_check}"
                )

    def get_current_price_enhanced(self, symbol):
        """Enhanced price fetching with fallback and caching"""
        try:
            # ✅ ENHANCED: Validate symbol parameter
            if not symbol or not isinstance(symbol, str):
                logger.error(f"Invalid symbol parameter: {symbol}")
                return 0
            
            if not self._rate_limit_check('price_check'):
                time.sleep(0.5)
                
            ticker = self._execute_with_retry(
                self.client.futures_symbol_ticker,
                symbol=symbol
            )
            
            # ✅ ENHANCED: Validate ticker response
            if not ticker or not isinstance(ticker, dict):
                logger.error(f"Invalid ticker response for {symbol}: {ticker}")
                return 0
            
            price_str = safe_get(ticker, 'price', default=None)
            if not price_str:
                logger.error(f"No price in ticker response for {symbol}: {ticker}")
                return 0
            
            # ✅ ENHANCED: Validate price is numeric
            try:
                price = float(price_str)
                if price <= 0:
                    logger.error(f"Non-positive price for {symbol}: {price}")
                    return 0
                return price
            except (ValueError, TypeError) as e:
                logger.error(f"Price is not numeric for {symbol}: {price_str}, error: {e}")
                return 0
            
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return 0

    def manage_positions_enhanced(self):
        """Enhanced position management with comprehensive monitoring"""
        try:
            for pos_id, position in list(self.active_positions.items()):
                try:
                    # Update last check time
                    self.active_positions[pos_id]['last_price_check'] = datetime.utcnow()
                    
                    # Verify position is still active
                    if not self.verify_position_active(pos_id):
                        logger.warning(f"Position {pos_id} no longer active on exchange")
                        continue
                    
                    current_price = self.get_current_price_enhanced(self.symbol)
                    if current_price <= 0:
                        self.active_positions[pos_id]['price_check_failures'] += 1
                        if self.active_positions[pos_id]['price_check_failures'] >= 3:
                            logger.error(f"Multiple price check failures for position {pos_id}")
                        continue
                    
                    # Reset failure count on successful price fetch
                    self.active_positions[pos_id]['price_check_failures'] = 0
                    
                    # Existing management logic with enhanced checks
                    self._manage_single_position(pos_id, position, current_price)
                    
                except Exception as e:
                    logger.error(f"Error managing position {pos_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Position management error: {e}")

    def _manage_single_position(self, pos_id, position, current_price):
        """Manage a single position with enhanced logic"""
        entry = safe_get(position, 'entry', default=0)
        tp1 = safe_get(position, 'tp1', default=0)
        tp2 = safe_get(position, 'tp2', default=0)
        sl = safe_get(position, 'sl', default=0)
        direction = safe_get(position, 'direction', default='')

        # Check order status for TP orders (MARKET orders)
        tp1_executed = False
        tp2_executed = False
        
        try:
            # Check TP1 order status
            if safe_get(position, 'orders', default={}).get('tp1_order'):
                tp1_order_id = safe_get(position['orders']['tp1_order'], 'orderId', default=0)
                if tp1_order_id:
                    tp1_order_status = self.client.futures_get_order(symbol=self.symbol, orderId=tp1_order_id)
                    tp1_executed = safe_get(tp1_order_status, 'status', default='') == 'FILLED'
            
            # Check TP2 order status
            if safe_get(position, 'orders', default={}).get('tp2_order'):
                tp2_order_id = safe_get(position['orders']['tp2_order'], 'orderId', default=0)
                if tp2_order_id:
                    tp2_order_status = self.client.futures_get_order(symbol=self.symbol, orderId=tp2_order_id)
                    tp2_executed = safe_get(tp2_order_status, 'status', default='') == 'FILLED'
        except Exception as e:
            logger.error(f"Error checking TP order status: {e}")

        # Calculate SL hit
        if direction == 'BUY':
            sl_hit = current_price <= sl
        else:  # SELL
            sl_hit = current_price >= sl

        # 1. Enhanced SL+ logic
        if not safe_get(position, 'sl_moved_to_be', default=False):
            if self.should_move_sl_to_be_enhanced(position, current_price):
                self.move_sl_to_breakeven_enhanced(pos_id, position)

        # 2. Handle TP1 executed (MARKET order)
        if not safe_get(position, 'tp1_hit', default=False) and tp1_executed:
            self._handle_tp1_hit(pos_id, position)
            self.activate_trailing_stop_enhanced(pos_id, position)

        # 3. Handle TP2 executed (MARKET order)
        if not safe_get(position, 'tp2_hit', default=False) and tp2_executed:
            self._handle_tp2_hit(pos_id, position)

        # 4. Handle SL hit
        if not safe_get(position, 'notifications', default={})['sl_notified']:
            if sl_hit:
                self._handle_sl_hit(pos_id, position)

    def move_sl_to_breakeven_enhanced(self, pos_id, position):
        """Enhanced SL+ movement with validation"""
        try:
            # Cancel existing SL order jika ada
            if safe_get(position, 'orders', default={}).get('sl_order'):
                self.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=safe_get(safe_get(position, 'orders', default={})['sl_order'], 'orderId', default=0)
                )
            # Place new SL at break-even (gunakan entry real)
            opposite_side = 'SELL' if safe_get(position, 'direction', default='') == 'BUY' else 'BUY'
            entry_price = safe_get(position, 'entry', default=0)
            new_sl_order = self.place_stop_market_order_enhanced(
                opposite_side, 
                entry_price,  # SL di entry price (breakeven)
                safe_get(position, 'size', default=0)
            )
            if new_sl_order:
                self.active_positions[pos_id]['orders']['sl_order'] = new_sl_order
                self.active_positions[pos_id]['sl_moved_to_be'] = True
                # Send notification
                if not safe_get(position, 'notifications', default={})['sl_be_notified']:
                    entry_price = safe_get(position, 'entry', default=0)
                    telegram.send_message(
                        f"📈 *SL MOVED TO BREAKEVEN*\n"
                        f"📌 PAIR: {self.symbol}\n"
                        f"🛡️ Risk eliminated - SL at entry: ${entry_price:.2f}\n"
                        f"💹 Current Price: ${self.get_current_price_enhanced(self.symbol):.2f}"
                    )
                    self.active_positions[pos_id]['notifications']['sl_be_notified'] = True
        except Exception as e:
            logger.error(f"Failed to move SL to breakeven: {e}")

    def _handle_tp1_hit(self, pos_id, position):
        """Handle TP1 hit event - MARKET order executed"""
        self.active_positions[pos_id]['tp1_hit'] = True
        
        if not safe_get(position, 'notifications', default={})['tp1_notified']:
            current_price = self.get_current_price_enhanced(self.symbol)
            wib_now = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
            telegram.send_message(
                f"🎯 *TP1 EXECUTED!*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"💰 70% position closed via MARKET order\n"
                f"📊 Execution Price: ${current_price:.2f}\n"
                f"🔄 Trailing stop activated for remaining 30%\n"
                f"🕒 Waktu: {wib_now} WIB"
            )
            self.active_positions[pos_id]['notifications']['tp1_notified'] = True
        # Log equity after TP1
        self.log_equity(event="TP1")

    def _handle_tp2_hit(self, pos_id, position):
        """Handle TP2 hit event - MARKET order executed"""
        self.active_positions[pos_id]['tp2_hit'] = True
        
        if not safe_get(position, 'notifications', default={})['tp2_notified']:
            current_price = self.get_current_price_enhanced(self.symbol)
            pnl = self._calculate_position_pnl(position)
            wib_now = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
            telegram.send_message(
                f"🎯 *TP2 EXECUTED!*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"💰 Full position closed via MARKET order\n"
                f"📊 Execution Price: ${current_price:.2f}\n"
                f"🏆 Maximum profit achieved!\n"
                f"📈 Estimated PnL: ${pnl:.2f}\n"
                f"🕒 Waktu: {wib_now} WIB"
            )
            self.active_positions[pos_id]['notifications']['tp2_notified'] = True
            
        # Update performance
        self.performance['wins'] += 1
        self.performance['consecutive_losses'] = 0
        self.performance['total_pnl'] += pnl
        
        # Remove position dari active_positions
        del self.active_positions[pos_id]

    def _handle_sl_hit(self, pos_id, position):
        """Handle SL hit event"""
        pnl = self._calculate_position_pnl(position)
        
        wib_now = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        telegram.send_message(
            f"🛑 *STOP LOSS HIT!*\n"
            f"📌 PAIR: {self.symbol}\n"
            f"⚠️ Position closed at ${safe_get(position, 'sl', default=0):.2f}\n"
            f"🛡️ Capital protected\n"
            f"📉 Estimated PnL: ${pnl:.2f}\n"
            f"🕒 Waktu: {wib_now} WIB"
        )
        self.active_positions[pos_id]['notifications']['sl_notified'] = True
        # Log equity after SL
        self.log_equity(event="SL")
        
        # Update performance
        self.performance['losses'] += 1
        self.performance['consecutive_losses'] += 1
        self.performance['total_pnl'] += pnl
        
        # Remove position dari active_positions
        del self.active_positions[pos_id]

    def _calculate_position_pnl(self, position):
        """Calculate estimated PnL for a position"""
        try:
            current_price = self.get_current_price_enhanced(self.symbol)
            entry_price = safe_get(position, 'entry', default=0)
            size = safe_get(position, 'size', default=0)
            
            if safe_get(position, 'direction', default='') == 'BUY':
                pnl = (current_price - entry_price) * size
            else:
                pnl = (entry_price - current_price) * size
                
            return pnl
        except Exception as e:
            logger.error(f"Failed to calculate PnL: {e}")
            return 0.0

    def activate_trailing_stop_enhanced(self, pos_id, position):
        """Enhanced trailing stop activation"""
        try:
            # Cancel existing SL order
            if safe_get(position, 'orders', default={}).get('sl_order'):
                self.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=safe_get(safe_get(position, 'orders', default={})['sl_order'], 'orderId', default=0)
                )

            # Calculate remaining quantity (30% after TP1)
            remaining_size = round(safe_get(position, 'size', default=0) * 0.3, 4)
            
            # Adjust callback rate based on volatility
            base_callback = 1.5
            if self.market_volatility > 5.0:
                callback_rate = base_callback * 1.2  # More aggressive in high volatility
            else:
                callback_rate = base_callback
            
            # Place trailing stop market order
            opposite_side = 'SELL' if safe_get(position, 'direction', default='') == 'BUY' else 'BUY'
            trailing_order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=opposite_side,
                type='TRAILING_STOP_MARKET',
                quantity=remaining_size,
                callbackRate=callback_rate,
                timeInForce='GTC'
            )
            
            if trailing_order:
                self.active_positions[pos_id]['orders']['trailing_order'] = trailing_order
                self.active_positions[pos_id]['trailing_active'] = True
                
                # Send notification
                if not safe_get(position, 'notifications', default={})['trailing_notified']:
                    wib_now = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
                    telegram.send_message(
                        f"🔄 *TRAILING STOP ACTIVATED*\n"
                        f"📌 PAIR: {self.symbol}\n"
                        f"📊 Remaining size: {remaining_size}\n"
                        f"🎯 Callback rate: {callback_rate:.1f}%\n"
                        f"💹 Market volatility: {self.market_volatility:.2f}%\n"
                        f"🕒 Waktu: {wib_now} WIB"
                    )
                    self.active_positions[pos_id]['notifications']['trailing_notified'] = True
                    
        except Exception as e:
            logger.error(f"Failed to activate trailing stop: {e}")

    def get_enhanced_performance(self):
        """Enhanced performance metrics with detailed analysis"""
        try:
            total_trades = self.performance['wins'] + self.performance['losses']
            win_rate = (self.performance['wins'] / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate additional metrics
            avg_win = self.performance.get('total_wins', 0) / self.performance['wins'] if self.performance['wins'] > 0 else 0
            avg_loss = self.performance.get('total_losses', 0) / self.performance['losses'] if self.performance['losses'] > 0 else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # Calculate drawdown
            current_drawdown = self.get_drawdown()
            max_drawdown = self.get_max_drawdown()
            
            # Calculate Sharpe ratio (simplified)
            daily_returns = self.performance.get('daily_returns', [])
            sharpe_ratio = 0
            if len(daily_returns) > 1:
                avg_return = sum(daily_returns) / len(daily_returns)
                std_return = (sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
                sharpe_ratio = avg_return / std_return if std_return != 0 else 0
            
            return {
                'total_trades': total_trades,
                'wins': self.performance['wins'],
                'losses': self.performance['losses'],
                'win_rate': win_rate,
                'total_pnl': self.performance['total_pnl'],
                'daily_pnl': self.performance['daily_pnl'],
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'consecutive_losses': self.performance['consecutive_losses'],
                'max_balance': self.performance['max_balance'],
                'min_balance': self.performance['min_balance'],
                'active_positions': len(self.active_positions),
                'daily_trades': self.daily_trades,
                'max_daily_trades': self.max_daily_trades
            }
        except Exception as e:
            logger.error(f"Error calculating enhanced performance: {e}")
            return {}

    def update_performance_metrics(self, trade_result):
        """Update performance metrics after trade completion"""
        try:
            pnl = trade_result.get('pnl', 0)
            is_win = pnl > 0
            
            if is_win:
                self.performance['wins'] += 1
                self.performance['consecutive_losses'] = 0
                self.performance['total_wins'] = self.performance.get('total_wins', 0) + pnl
            else:
                self.performance['losses'] += 1
                self.performance['consecutive_losses'] += 1
                self.performance['total_losses'] = self.performance.get('total_losses', 0) + abs(pnl)
            
            # Update balance tracking
            current_balance = self.get_account_balance()
            self.performance['max_balance'] = max(self.performance['max_balance'], current_balance)
            self.performance['min_balance'] = min(self.performance['min_balance'], current_balance)
            
            # Update daily returns
            if 'daily_returns' not in self.performance:
                self.performance['daily_returns'] = []
            
            # Calculate daily return
            if len(self.performance['daily_returns']) > 0:
                daily_return = (current_balance - self.performance['max_balance']) / self.performance['max_balance']
                self.performance['daily_returns'].append(daily_return)
            
            # Keep only last 30 days
            if len(self.performance['daily_returns']) > 30:
                self.performance['daily_returns'] = self.performance['daily_returns'][-30:]
            
            logger.info(f"[PERFORMANCE] Trade completed: {'WIN' if is_win else 'LOSS'} (PnL: ${pnl:.2f})")
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")

    def get_active_trades(self):
        # Mengembalikan jumlah posisi aktif yang sedang dimonitor bot
        return len(self.active_positions)

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Enhanced ICT Trader...")
        self.monitoring_active = False
        
        # Cancel all active orders
        for pos_id, position in self.active_positions.items():
            self.cancel_all_orders(position)
            
        # Send final summary
        wib_now = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        telegram.send_message(
            f"🔄 *BOT SHUTDOWN*\n"
            f"Final Statistics:\n"
            f"📊 Performance: {self.get_enhanced_performance()}\n"
            f"⏰ Waktu: {wib_now} WIB"
        )
        
        # Save state saat shutdown
        self.save_state()
        logger.info("Enhanced ICT Trader shutdown complete")

    def check_margin_sufficient(self, position_size, entry_price):
        """Check if margin is sufficient for position with enhanced small balance handling"""
        try:
            balance = self.get_account_balance()
            
            # Use appropriate leverage based on balance
            if balance < config.SMALL_BALANCE_THRESHOLD:
                effective_leverage = min(self.leverage, config.SMALL_BALANCE_LEVERAGE)
            else:
                effective_leverage = self.leverage
            
            required_margin = (position_size * entry_price) / effective_leverage
            
            # For small balances, add safety buffer
            safety_buffer = 1.1 if balance < config.SMALL_BALANCE_THRESHOLD else 1.05
            required_margin_with_buffer = required_margin * safety_buffer
            
            if required_margin_with_buffer > balance:
                logger.warning(f"❌ Margin tidak cukup. Dibutuhkan: {required_margin_with_buffer:.2f}, tersedia: {balance:.2f}")
                
                # Suggest alternatives for small balance
                if balance < config.SMALL_BALANCE_THRESHOLD:
                    logger.info(f"💡 Saran untuk balance kecil (${balance:.2f}):")
                    logger.info(f"   - Kurangi leverage dari {self.leverage}x ke {config.SMALL_BALANCE_LEVERAGE}x")
                    logger.info(f"   - Kurangi risk dari {config.DEFAULT_RISK}% ke {config.SMALL_BALANCE_RISK}%")
                    logger.info(f"   - Top up balance minimal ${config.SMALL_BALANCE_THRESHOLD*2} untuk trading yang lebih aman")
                
                return False
            
            logger.info(f"✅ Margin cukup. Dibutuhkan: {required_margin_with_buffer:.2f}, tersedia: {balance:.2f} (leverage: {effective_leverage}x)")
            return True
            
        except Exception as e:
            logger.error(f"Error checking margin: {e}")
            return False

    def get_drawdown(self):
        """Calculate current drawdown percentage"""
        try:
            if self.performance['max_balance'] <= 0:
                return 0.0
            current_balance = self.get_account_balance()
            if current_balance <= 0:
                return 0.0
            drawdown = ((self.performance['max_balance'] - current_balance) / self.performance['max_balance']) * 100
            return max(0.0, drawdown)  # Ensure non-negative
        except Exception as e:
            logger.error(f"Failed to calculate drawdown: {e}")
            return 0.0

    def get_max_drawdown(self):
        """Calculate maximum drawdown experienced"""
        try:
            if self.performance['max_balance'] <= 0:
                return 0.0
            max_drawdown = ((self.performance['max_balance'] - self.performance['min_balance']) / self.performance['max_balance']) * 100
            return max(0.0, max_drawdown)
        except Exception as e:
            logger.error(f"Failed to calculate max drawdown: {e}")
            return 0.0
    
    def calculate_position_size(self, signal, base_risk_percent=2):
        """Calculate position size (alias for adaptive method)"""
        return self.calculate_adaptive_position_size(signal, base_risk_percent)

    def get_daily_trades(self):
        """Get current daily trades count"""
        return self.daily_trades

    def get_consecutive_losses(self):
        """Get current consecutive losses count"""
        return self.performance.get('consecutive_losses', 0)

    def get_performance(self):
        """Return current performance dictionary"""
        return self.performance
    