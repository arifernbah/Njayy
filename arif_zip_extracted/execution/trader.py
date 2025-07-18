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
        self.leverage = 5
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
        self.max_daily_trades = 50
        self.max_consecutive_losses = 5
        self.connection_retry_count = 0
        self.last_heartbeat = datetime.utcnow()
        self.market_volatility = 0.0
        self.order_cache = {}
        
        # Rate limiting
        self.api_call_times = defaultdict(list)
        self.max_calls_per_minute = 50
        
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
            balance = self.get_account_balance()
            logger.info(f"[STARTUP] Initial balance: {balance:.2f} USDT")
            with open("equity.log", "a") as f:
                f.write(f"[{datetime.utcnow()}] STARTUP BALANCE: {balance:.2f} USDT\n")
        except Exception as e:
            logger.error(f"[STARTUP] Failed to log initial balance: {e}")

    def _monitoring_loop(self):
        """Background monitoring for health checks and maintenance"""
        last_log_hour = None
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
        """Send daily summary at midnight"""
        now = datetime.utcnow()
        if now.hour == 0 and now.minute == 0:
            self._send_daily_summary()

    def _send_daily_summary(self):
        """Send daily performance summary"""
        total_trades = self.performance['wins'] + self.performance['losses']
        win_rate = (self.performance['wins'] / total_trades * 100) if total_trades > 0 else 0
        
        telegram.send_message(
            f"📊 *DAILY SUMMARY*\n"
            f"📈 Total Trades: {total_trades}\n"
            f"✅ Wins: {self.performance['wins']}\n"
            f"❌ Losses: {self.performance['losses']}\n"
            f"🎯 Win Rate: {win_rate:.1f}%\n"
            f"💰 Daily PnL: ${self.performance['daily_pnl']:.2f}\n"
            f"📊 Market Volatility: {self.market_volatility:.2f}%\n"
            f"🔄 Active Positions: {len(self.active_positions)}"
        )

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
                telegram.send_message(f"❌ Gagal cek saldo: {e}")
                self._last_balance_error_time = now
            logger.error(f"Failed to get balance: {e}")
            return 0.0

    def check_circuit_breaker(self):
        """Check if trading should be stopped due to risk limits"""
        if self.daily_trades >= self.max_daily_trades:
            logger.warning("Daily trade limit reached")
            return False
            
        if self.performance['consecutive_losses'] >= self.max_consecutive_losses:
            logger.warning("Consecutive loss limit reached")
            telegram.send_message(
                f"🛑 *CIRCUIT BREAKER ACTIVATED*\n"
                f"Consecutive losses: {self.performance['consecutive_losses']}\n"
                f"Trading suspended for safety"
            )
            return False
            
        return True

    def calculate_adaptive_position_size(self, signal, base_risk_percent=2):
        """Calculate position size with volatility adjustment"""
        try:
            # Base calculation
            balance = self.get_account_balance()
            
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
            return round(position_size, 4)
            
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return 0

    def verify_position_active(self, position_id):
        """Verify if position is still active on exchange"""
        try:
            positions = self._execute_with_retry(self.client.futures_position_information)
            return any(float(safe_get(pos, 'positionAmt', default=0)) != 0 for pos in positions 
                      if safe_get(pos, 'symbol', default='') == self.symbol)
        except Exception as e:
            logger.error(f"Failed to verify position: {e}")
            return False

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
        info = self.client.futures_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                        precision = abs(decimal.Decimal(str(step_size)).as_tuple().exponent)
                        return precision
        return 3  # default jika tidak ketemu

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
            order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=side,
                type='LIMIT',
                price=price,
                quantity=quantity,
                timeInForce='GTC'
            )
            if not order:
                logger.error("Limit order gagal, tidak ada response dari Binance.")
                return None
            self.order_cache[safe_get(order, 'orderId', default=0)] = order
            logger.info(f"Limit order placed: {order}")
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
            equity = self.get_account_balance()
            log_line = f"[{datetime.utcnow()}] Equity: {equity:.2f} USDT (after {event} {self.symbol})\n"
            with open("equity.log", "a") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to log equity: {e}")

    def execute_entry_enhanced(self, signal):
        """Enhanced entry execution with comprehensive checks and auto leverage"""
        try:
            # Circuit breaker check
            if not self.check_circuit_breaker():
                return False

            # ✅ AUTO SET LEVERAGE VIA API
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
                return False

            # 2. Place STOP_MARKET for SL
            sl_order = self.place_stop_market_order_enhanced(opposite_side, signal.sl, position_size)
            if not sl_order:
                logger.warning("Failed to place SL order - CRITICAL!")
                # Cancel entry if SL placement fails
                self.cancel_all_orders({'orders': {'entry': entry_order}})
                return False

            # 3. Place LIMIT orders for TP1 (70%) and TP2 (30%)
            tp1_size = round(position_size * 0.7, 4)
            tp2_size = round(position_size * 0.3, 4)

            tp1_order = self.place_limit_order_enhanced(opposite_side, signal.tp1, tp1_size)
            tp2_order = self.place_limit_order_enhanced(opposite_side, signal.tp2, tp2_size)

            # 4. Track the position
            self.track_position_enhanced(signal, entry_order, position_size, {
                'sl_order': sl_order,
                'tp1_order': tp1_order,
                'tp2_order': tp2_order,
                'entry_order': entry_order
            })

            self.daily_trades += 1
            
            # Enhanced telegram notification
            telegram.send_message(
                f"🚀 *ENTRY EXECUTED*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"🎯 Direction: {signal.direction}\n"
                f"💰 Entry: ${signal.entry:.2f}\n"
                f"🛑 SL: ${signal.sl:.2f}\n"
                f"🎯 TP1: ${signal.tp1:.2f}\n"
                f"🎯 TP2: ${signal.tp2:.2f}\n"
                f"📊 Size: {position_size}\n"
                f"💹 Market Vol: {self.market_volatility:.2f}%\n"
                f"🔢 Daily Trades: {self.daily_trades}/{self.max_daily_trades}"
            )
            # Log equity after entry
            self.log_equity(event="ENTRY")
            
            return True
            
        except Exception as e:
            logger.error(f"Execute entry error: {e}")
            return False

    def track_position_enhanced(self, signal, entry_order, size, orders):
        """Enhanced position tracking with more metadata"""
        position_id = safe_get(entry_order, 'orderId', default=0)
        self.active_positions[position_id] = {
            'symbol': self.symbol,
            'entry': signal.entry,
            'sl': signal.sl,
            'tp1': signal.tp1,
            'tp2': signal.tp2,
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
            if safe_get(position, 'last_price_check', default=None) < cutoff_time:
                logger.warning(f"Position {pos_id} hasn't been updated recently")
                telegram.send_message(
                    f"⚠️ *POSITION ALERT*\n"
                    f"Position {pos_id} may be stuck\n"
                    f"Last update: {safe_get(position, 'last_price_check', default='N/A')}"
                )

    def get_current_price_enhanced(self, symbol):
        """Enhanced price fetching with fallback and caching"""
        try:
            if not self._rate_limit_check('price_check'):
                time.sleep(0.5)
                
            ticker = self._execute_with_retry(
                self.client.futures_symbol_ticker,
                symbol=symbol
            )
            return float(safe_get(ticker, 'price', default=0))
            
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
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

        # Calculate targets
        if direction == 'BUY':
            tp1_hit = current_price >= tp1
            tp2_hit = current_price >= tp2
            sl_hit = current_price <= sl
        else:  # SELL
            tp1_hit = current_price <= tp1
            tp2_hit = current_price <= tp2
            sl_hit = current_price >= sl

        # 1. Enhanced SL+ logic
        if not safe_get(position, 'sl_moved_to_be', default=False):
            if self.should_move_sl_to_be_enhanced(position, current_price):
                self.move_sl_to_breakeven_enhanced(position)

        # 2. Handle TP1 hit
        if not safe_get(position, 'tp1_hit', default=False) and tp1_hit:
            self._handle_tp1_hit(pos_id, position)

        # 3. Handle TP2 hit
        if not safe_get(position, 'tp2_hit', default=False) and tp2_hit:
            self._handle_tp2_hit(pos_id, position)

        # 4. Handle SL hit
        if not safe_get(position, 'notifications', default={})['sl_notified']:
            if sl_hit:
                self._handle_sl_hit(pos_id, position)

    def move_sl_to_breakeven_enhanced(self, position):
        """Enhanced SL+ movement with validation"""
        try:
            # Cancel existing SL order
            if safe_get(position, 'orders', default={}).get('sl_order'):
                self.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=safe_get(safe_get(position, 'orders', default={})['sl_order'], 'orderId', default=0)
                )

            # Place new SL at break-even
            opposite_side = 'SELL' if safe_get(position, 'direction', default='') == 'BUY' else 'BUY'
            new_sl_order = self.place_stop_market_order_enhanced(
                opposite_side, 
                safe_get(position, 'entry', default=0),
                safe_get(position, 'size', default=0)
            )
            
            if new_sl_order:
                self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['orders']['sl_order'] = new_sl_order
                self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['sl_moved_to_be'] = True
                
                # Send notification
                if not safe_get(position, 'notifications', default={})['sl_be_notified']:
                    telegram.send_message(
                        f"📈 *SL MOVED TO BREAKEVEN*\n"
                        f"📌 PAIR: {self.symbol}\n"
                        f"🛡️ Risk eliminated - SL at entry: ${safe_get(position, 'entry', default=0):.2f}\n"
                        f"💹 Current Price: ${self.get_current_price_enhanced(self.symbol):.2f}"
                    )
                    self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['notifications']['sl_be_notified'] = True
                    
        except Exception as e:
            logger.error(f"Failed to move SL to breakeven: {e}")

    def _handle_tp1_hit(self, pos_id, position):
        """Handle TP1 hit event"""
        self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['tp1_hit'] = True
        self.activate_trailing_stop_enhanced(position)
        
        if not safe_get(position, 'notifications', default={})['tp1_notified']:
            telegram.send_message(
                f"🎯 *TP1 HIT!*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"💰 70% position closed at ${safe_get(position, 'tp1', default=0):.2f}\n"
                f"🔄 Trailing stop activated for remaining 30%\n"
                f"📊 Current Price: ${self.get_current_price_enhanced(self.symbol):.2f}"
            )
            self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['notifications']['tp1_notified'] = True
        # Log equity after TP1
        self.log_equity(event="TP1")

    def _handle_tp2_hit(self, pos_id, position):
        """Handle TP2 hit event"""
        self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['tp2_hit'] = True
        
        if not safe_get(position, 'notifications', default={})['tp2_notified']:
            pnl = self._calculate_position_pnl(position)
            telegram.send_message(
                f"🎯 *TP2 HIT!*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"💰 Full position closed at ${safe_get(position, 'tp2', default=0):.2f}\n"
                f"🏆 Maximum profit achieved!\n"
                f"📈 Estimated PnL: ${pnl:.2f}"
            )
            self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['notifications']['tp2_notified'] = True
            
        # Update performance
        self.performance['wins'] += 1
        self.performance['consecutive_losses'] = 0
        self.performance['total_pnl'] += pnl
        
        # Remove position
        del self.active_positions[safe_get(position, 'symbol', default='')][pos_id]

    def _handle_sl_hit(self, pos_id, position):
        """Handle SL hit event"""
        pnl = self._calculate_position_pnl(position)
        
        telegram.send_message(
            f"🛑 *STOP LOSS HIT!*\n"
            f"📌 PAIR: {self.symbol}\n"
            f"⚠️ Position closed at ${safe_get(position, 'sl', default=0):.2f}\n"
            f"🛡️ Capital protected\n"
            f"📉 Estimated PnL: ${pnl:.2f}"
        )
        self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['notifications']['sl_notified'] = True
        # Log equity after SL
        self.log_equity(event="SL")
        
        # Update performance
        self.performance['losses'] += 1
        self.performance['consecutive_losses'] += 1
        self.performance['total_pnl'] += pnl
        
        # Remove position
        del self.active_positions[safe_get(position, 'symbol', default='')][pos_id]

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
        except:
            return 0.0

    def activate_trailing_stop_enhanced(self, position):
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
                self.active_positions[safe_get(position, 'symbol', default='')][safe_get(position, 'symbol', default='')][pos_id]['orders']['trailing_order'] = trailing_order
                self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['trailing_active'] = True
                
                # Send notification
                if not safe_get(position, 'notifications', default={})['trailing_notified']:
                    telegram.send_message(
                        f"🔄 *TRAILING STOP ACTIVATED*\n"
                        f"📌 PAIR: {self.symbol}\n"
                        f"📊 Remaining size: {remaining_size}\n"
                        f"🎯 Callback rate: {callback_rate:.1f}%\n"
                        f"💹 Market volatility: {self.market_volatility:.2f}%"
                    )
                    self.active_positions[safe_get(position, 'symbol', default='')][pos_id]['notifications']['trailing_notified'] = True
                    
        except Exception as e:
            logger.error(f"Failed to activate trailing stop: {e}")

    def get_enhanced_performance(self):
        """Get comprehensive performance statistics"""
        total_trades = self.performance['wins'] + self.performance['losses']
        win_rate = (self.performance['wins'] / total_trades * 100) if total_trades > 0 else 0
        
        return {
            **self.performance,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'active_positions': len(self.active_positions),
            'daily_trades': self.daily_trades,
            'market_volatility': self.market_volatility,
            'connection_health': self.connection_retry_count < 3
        }

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
        telegram.send_message(
            f"🔄 *BOT SHUTDOWN*\n"
            f"Final Statistics:\n"
            f"📊 Performance: {self.get_enhanced_performance()}\n"
            f"⏰ Shutdown time: {datetime.utcnow()}"
        )
        
        logger.info("Enhanced ICT Trader shutdown complete")

    def check_margin_sufficient(self, position_size, entry_price):
        """Check if margin is sufficient for the trade"""
        try:
            balance_info = self.client.futures_account_balance()
            usdt_balance = float(next(x for x in balance_info if x["asset"] == "USDT")["balance"])
            
            # Calculate required margin
            required_margin = (abs(position_size) * entry_price) / self.leverage
            
            if required_margin > usdt_balance:
                logger.warning(f"❌ Margin tidak cukup. Dibutuhkan: {required_margin:.2f}, tersedia: {usdt_balance:.2f}")
                return False
            return True
        except Exception as e:
            logger.error(f"Gagal cek margin: {e}")
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
    