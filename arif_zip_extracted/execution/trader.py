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
import websocket
import json
import time

class EnhancedICTTrader:
    def __init__(self):
        # Initialize client with configurable endpoint
        self.client = Client(api_key=config.BINANCE_API_KEY, api_secret=config.BINANCE_SECRET)
        
        # Set the base URL for the client
        if hasattr(config, 'BINANCE_BASE_URL') and config.BINANCE_BASE_URL:
            # Override the default URLs for the client
            if 'testnet' in config.BINANCE_BASE_URL:
                self.client.API_URL = config.BINANCE_BASE_URL + '/fapi'
                self.client.FUTURES_URL = config.BINANCE_BASE_URL + '/fapi'
                print(f"🔧 Using testnet endpoint: {config.BINANCE_BASE_URL}")
            else:
                self.client.API_URL = config.BINANCE_BASE_URL + '/fapi'
                self.client.FUTURES_URL = config.BINANCE_BASE_URL + '/fapi'
                print(f"🔧 Using endpoint: {config.BINANCE_BASE_URL}")
        
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
        
        # WebSocket real-time price data
        self.ws_prices = {}  # Store real-time prices
        self.ws_connected = False
        self.ws_thread = None
        # Use configurable WebSocket URL
        if hasattr(config, 'BINANCE_BASE_URL') and 'testnet' in config.BINANCE_BASE_URL:
            self.ws_url = "wss://stream.binancefuture.com/ws/"  # Testnet WebSocket
        else:
            self.ws_url = "wss://fstream.binance.com/ws/"  # Main WebSocket
        
        # Start WebSocket connection
        self.start_websocket()
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        # Restore open positions from Binance Futures
        try:
            open_positions = self.client.futures_position_information()
            for pos in open_positions:
                if abs(float(pos['positionAmt'])) > 0:
                    symbol = pos['symbol']
                    entry = float(pos['entryPrice'])
                    size = abs(float(pos['positionAmt']))
                    direction = 'BUY' if float(pos['positionAmt']) > 0 else 'SELL'
                    # Fetch open orders for this symbol
                    open_orders = self.client.futures_get_open_orders(symbol=symbol)
                    sl_order = None
                    tp1_order = None
                    tp2_order = None
                    # Identify SL/TP orders
                    limit_orders = [o for o in open_orders if o['type'] == 'LIMIT']
                    stop_orders = [o for o in open_orders if o['type'] == 'STOP_MARKET']
                    # SL: STOP_MARKET, side opposite, stopPrice < entry (BUY) or > entry (SELL)
                    for o in stop_orders:
                        if (direction == 'BUY' and float(o['stopPrice']) < entry) or (direction == 'SELL' and float(o['stopPrice']) > entry):
                            sl_order = o
                    # TP: LIMIT, side opposite, price > entry (BUY) or < entry (SELL)
                    tp_candidates = []
                    for o in limit_orders:
                        if (direction == 'BUY' and float(o['price']) > entry) or (direction == 'SELL' and float(o['price']) < entry):
                            tp_candidates.append(o)
                    # Ambil dua TP terdekat dari entry
                    tp_candidates.sort(key=lambda x: abs(float(x['price']) - entry))
                    if len(tp_candidates) > 0:
                        tp1_order = tp_candidates[0]
                    if len(tp_candidates) > 1:
                        tp2_order = tp_candidates[1]
                    # Trailing stop
                    trailing_order = None
                    for o in open_orders:
                        if o['type'] == 'TRAILING_STOP_MARKET':
                            trailing_order = o
                    # SL+ (breakeven): SL order di harga entry
                    sl_moved_to_be = False
                    if sl_order and abs(float(sl_order['stopPrice']) - entry) < 1e-6:
                        sl_moved_to_be = True
                    trailing_active = trailing_order is not None
                    self.active_positions[symbol] = {
                        'symbol': symbol,
                        'entry': entry,
                        'sl': float(sl_order['stopPrice']) if sl_order else None,
                        'tp1': float(tp1_order['price']) if tp1_order else None,
                        'tp2': float(tp2_order['price']) if tp2_order else None,
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
            if self.active_positions:
                from integrations.telegram import telegram
                telegram.send_medium_priority(f"♻️ Bot restart: {len(self.active_positions)} open position(s) with SL/TP restored and will be monitored.", msg_type='Bot Restart')
        except Exception as e:
            from utils.logger import logger
            logger.error(f"Failed to restore open positions/orders on startup: {e}")

    def start_websocket(self):
        """Start WebSocket connection for real-time price data"""
        try:
            # Subscribe to all trading pairs
            streams = [f"{pair.lower()}@ticker" for pair in config.TRADING_PAIRS]
            ws_url = self.ws_url + "/".join(streams)
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if 's' in data and 'c' in data:  # Symbol and close price
                        symbol = data['s']
                        price = float(data['c'])
                        self.ws_prices[symbol] = {
                            'price': price,
                            'timestamp': datetime.utcnow()
                        }
                except Exception as e:
                    logger.error(f"WebSocket message error: {e}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
                self.ws_connected = False
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning("WebSocket connection closed")
                self.ws_connected = False
                # Reconnect after 5 seconds
                time.sleep(5)
                self.start_websocket()
            
            def on_open(ws):
                logger.info("WebSocket connection established")
                self.ws_connected = True
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket: {e}")
            self.ws_connected = False

    def get_realtime_price(self, symbol):
        """Get real-time price from WebSocket, fallback to REST API"""
        try:
            # Try WebSocket first
            if self.ws_connected and symbol in self.ws_prices:
                price_data = self.ws_prices[symbol]
                # Check if price is fresh (less than 5 seconds old)
                if (datetime.utcnow() - price_data['timestamp']).total_seconds() < 5:
                    return price_data['price']
            
            # Fallback to REST API
            return self.get_current_price_enhanced(symbol)
            
        except Exception as e:
            logger.error(f"Failed to get real-time price: {e}")
            return self.get_current_price_enhanced(symbol)

    def _monitoring_loop(self):
        """Background monitoring for health checks and maintenance"""
        while self.monitoring_active:
            try:
                self._health_check()
                self._cleanup_old_api_calls()
                self._update_market_volatility()
                self._daily_summary_check()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)

    def _health_check(self):
        """Perform health checks with enhanced error handling"""
        try:
            # Test connection with better error handling
            try:
                # Use a simpler endpoint first to test connectivity
                server_time = self.client.get_server_time()
                if not server_time or 'serverTime' not in server_time:
                    raise Exception("Invalid server time response")
                
                # Now test futures account balance
                balance_response = self.client.futures_account_balance()
                
                # Validate response is not HTML
                if isinstance(balance_response, str) and '<html>' in balance_response.lower():
                    raise Exception("Received HTML response instead of JSON")
                
                if not isinstance(balance_response, list):
                    raise Exception("Invalid balance response format")
                
                self.last_heartbeat = datetime.utcnow()
                self.connection_retry_count = 0
                
                # Check for stuck positions
                self._check_stuck_positions()
                
            except Exception as api_error:
                # Check if it's an HTML error response
                error_str = str(api_error)
                if '<html>' in error_str.lower() or 'doctype' in error_str.lower():
                    logger.warning(f"Binance returned HTML error page (retry {self.connection_retry_count + 1})")
                    self.connection_retry_count += 1
                    
                    if self.connection_retry_count >= 3:
                        telegram.send_critical(
                            f"🚨 *BINANCE API ERROR*\n"
                            f"❌ HTML error response received\n"
                            f"🔄 Retry count: {self.connection_retry_count}\n"
                            f"⏰ Time: {datetime.utcnow().strftime('%H:%M UTC')}\n"
                            f"⚠️ Possible causes:\n"
                            f"• Rate limiting\n"
                            f"• Network issues\n"
                            f"• Binance server problems\n"
                            f"• API endpoint issues",
                            msg_type='API Error'
                        )
                    return
                else:
                    # Regular API error
                    raise api_error
                    
        except Exception as e:
            self.connection_retry_count += 1
            logger.warning(f"Health check failed (retry {self.connection_retry_count}): {e}")
            
            if self.connection_retry_count >= 5:
                telegram.send_critical(
                    f"🚨 *CONNECTION ISSUE*\n"
                    f"Bot connection unstable\n"
                    f"Retry count: {self.connection_retry_count}\n"
                    f"Error: {str(e)[:100]}..."
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
        try:
            performance = self.get_enhanced_performance()
            
            summary = {
                'total_trades': performance.get('total_trades', 0),
                'winners': performance.get('wins', 0),
                'losers': performance.get('losses', 0),
                'win_rate': performance.get('win_rate', 0),
                'total_pnl': performance.get('total_pnl', 0),
                'best_trade': max(performance.get('total_pnl', 0), 0),
                'worst_trade': min(performance.get('total_pnl', 0), 0)
            }
            
            telegram.send_daily_summary(summary)
            
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")

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
                result = func(*args, **kwargs)
                
                # Check if result is HTML error response
                if isinstance(result, str) and ('<html>' in result.lower() or 'doctype' in result.lower()):
                    raise Exception(f"HTML error response received: {result[:200]}...")
                
                return result
                
            except Exception as e:
                error_str = str(e)
                
                # Check for HTML error responses
                if '<html>' in error_str.lower() or 'doctype' in error_str.lower():
                    logger.warning(f"HTML error response on {func.__name__}, attempt {attempt+1}/{max_retries}")
                    if attempt == max_retries - 1:  # Last attempt
                        telegram.send_critical(
                            f"🚨 *BINANCE HTML ERROR*\n"
                            f"❌ Function: {func.__name__}\n"
                            f"🔄 Attempts: {max_retries}\n"
                            f"⏰ Time: {datetime.utcnow().strftime('%H:%M UTC')}",
                            msg_type='API Error'
                        )
                    time.sleep(delay * (2 ** attempt) + 5)  # Extra delay for HTML errors
                    continue
                
                # Check for rate limiting (HTTP 429)
                if hasattr(e, 'status_code') and getattr(e, 'status_code', None) == 429:
                    logger.warning(f"Rate limit hit (429) on {func.__name__}, attempt {attempt+1}")
                    time.sleep(delay * (2 ** attempt) + 10)  # Longer delay for rate limits
                else:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}")
                    time.sleep(delay * (2 ** attempt))
        
        logger.error(f"Function {func.__name__} failed after {max_retries} attempts.")
        return None

    def get_account_balance(self, symbol=None):
        """Get account balance with enhanced error handling"""
        try:
            if not self._rate_limit_check('balance'):
                time.sleep(1)
                
            balance_info = self._execute_with_retry(
                self.client.futures_account_balance,
                max_retries=3,
                delay=2
            )
            
            if symbol:
                # Get specific symbol balance
                for balance in balance_info:
                    if balance["asset"] == symbol:
                        return float(balance["balance"])
                return 0.0
            else:
                # Get USDT balance
                for balance in balance_info:
                    if balance["asset"] == "USDT":
                        return float(balance["balance"])
                return 0.0
                
        except Exception as e:
            telegram.send_critical(f"❌ Gagal cek saldo: {e}", msg_type='Balance Error')
            logger.error(f"Failed to get balance: {e}")
            return 0.0

    def check_circuit_breaker(self):
        """Check circuit breaker conditions"""
        try:
            # Check consecutive losses
            if self.performance['consecutive_losses'] >= self.max_consecutive_losses:
                telegram.send_critical(
                    f"🛑 *CIRCUIT BREAKER ACTIVATED*\n"
                    f"❌ Consecutive losses: {self.performance['consecutive_losses']}\n"
                    f"🛡️ Max allowed: {self.max_consecutive_losses}\n"
                    f"⏰ Bot paused for safety",
                    msg_type='Circuit Breaker'
                )
                return False
            
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                telegram.send_medium_priority(
                    f"📊 *DAILY TRADE LIMIT REACHED*\n"
                    f"🎯 Daily trades: {self.daily_trades}\n"
                    f"📈 Max allowed: {self.max_daily_trades}\n"
                    f"⏰ Waiting for reset",
                    msg_type='Daily Limit'
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Circuit breaker check error: {e}")
            return False

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
            return any(float(pos['positionAmt']) != 0 for pos in positions 
                      if pos['symbol'] == self.symbol)
        except Exception as e:
            logger.error(f"Failed to verify position: {e}")
            return False

    def cancel_all_orders(self, position):
        """Cancel all pending orders for a position"""
        cancelled_orders = []
        for order_type, order in position.get('orders', {}).items():
            if order and 'orderId' in order:
                try:
                    self.client.futures_cancel_order(
                        symbol=self.symbol,
                        orderId=order['orderId']
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
        """Enhanced market order with validation and priority execution"""
        try:
            if not self._rate_limit_check('market_order'):
                time.sleep(1)
                
            # Validate quantity
            if quantity <= 0:
                logger.error("Invalid quantity for market order")
                return None
                
            precision = self.get_quantity_precision(self.symbol)
            quantity = round(quantity, precision)
            
            # Get current market price for slippage calculation
            current_price = self.get_current_price_enhanced(self.symbol)
            if current_price <= 0:
                logger.error("Failed to get current price for market order")
                return None

            # Place market order with priority execution
            order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=side,
                type='MARKET',
                quantity=quantity,
                newOrderRespType='FULL'  # Get full response for execution details
            )
            
            if not order:
                logger.error("Market order failed, no response from Binance")
                return None
                
            # Calculate actual execution price and slippage
            if 'fills' in order and order['fills']:
                total_qty = sum(float(fill['qty']) for fill in order['fills'])
                weighted_price = sum(float(fill['qty']) * float(fill['price']) for fill in order['fills']) / total_qty
                slippage = abs(weighted_price - current_price) / current_price * 100
                
                logger.info(f"Market order executed: {order['orderId']}, Avg Price: {weighted_price:.4f}, Slippage: {slippage:.2f}%")
                
                # Warn if slippage is too high
                if slippage > 1.0:
                    logger.warning(f"High slippage detected: {slippage:.2f}% for {self.symbol}")
                    telegram.send_message(f"⚠️ High slippage: {slippage:.2f}% on {self.symbol} market order")
            else:
                logger.info(f"Market order placed: {order['orderId']}")
            
            # Cache order for tracking
            self.order_cache[order['orderId']] = order
            return order
            
        except Exception as e:
            logger.error(f"Market order error: {e}")
            return None

    def place_stop_market_order_enhanced(self, side, stop_price, quantity):
        """Enhanced stop market order with validation and precision"""
        try:
            if not self._rate_limit_check('stop_order'):
                time.sleep(1)
                
            # Validate parameters
            if quantity <= 0 or stop_price <= 0:
                logger.error("Invalid parameters for stop order")
                return None
                
            precision = self.get_quantity_precision(self.symbol)
            quantity = round(quantity, precision)

            # Get tick size for price precision
            info = self.client.futures_exchange_info()
            tick_size = 0.01
            for s in info['symbols']:
                if s['symbol'] == self.symbol:
                    for f in s['filters']:
                        if f['filterType'] == 'PRICE_FILTER':
                            tick_size = float(f['tickSize'])
                            break
                    break
            
            # Round stop price to tick size
            stop_price = round(round(stop_price / tick_size) * tick_size, 8)
            
            # Add small buffer to prevent premature triggering
            current_price = self.get_current_price_enhanced(self.symbol)
            if current_price > 0:
                buffer_percent = 0.05  # 0.05% buffer
                if side == 'SELL' and stop_price > current_price:  # SL for BUY position
                    buffer = current_price * buffer_percent
                    stop_price = stop_price + buffer
                elif side == 'BUY' and stop_price < current_price:  # SL for SELL position
                    buffer = current_price * buffer_percent
                    stop_price = stop_price - buffer
                
                # Re-round after buffer adjustment
                stop_price = round(round(stop_price / tick_size) * tick_size, 8)

            order = self._execute_with_retry(
                self.client.futures_create_order,
                symbol=self.symbol,
                side=side,
                type='STOP_MARKET',
                stopPrice=stop_price,
                quantity=quantity,
                timeInForce='GTC'
            )
            
            if order:
                self.order_cache[order['orderId']] = order
                logger.info(f"Stop market order placed: {order}")
                return order
            else:
                logger.error("Stop market order failed - no response from Binance")
                return None
            
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
            self.order_cache[order['orderId']] = order
            logger.info(f"Limit order placed: {order}")
            return order
        except Exception as e:
            logger.error(f"Limit order error: {e}")
            return None

    def execute_entry_enhanced(self, signal):
        """Enhanced entry execution with comprehensive checks"""
        try:
            # Circuit breaker check
            if not self.check_circuit_breaker():
                return False
                
            # REAL-TIME PRICE VALIDATION (WebSocket priority)
            current_market_price = self.get_realtime_price(self.symbol)
            if current_market_price <= 0:
                logger.error("Failed to get current market price")
                return False
                
            # Check if signal price is too old (more than 2% difference)
            price_diff_percent = abs(current_market_price - signal.entry) / current_market_price * 100
            if price_diff_percent > 2.0:
                logger.warning(f"Signal price too old: Signal={signal.entry}, Market={current_market_price}, Diff={price_diff_percent:.2f}%")
                return False
                
            # Recalculate levels based on current market price if needed
            if price_diff_percent > 0.5:
                logger.info(f"Adjusting signal levels: Old={signal.entry}, New={current_market_price}")
                # Update signal levels to current market price
                signal.entry = current_market_price
                # Recalculate SL and TP based on new entry
                risk = abs(signal.entry - signal.sl)
                if signal.direction == 'BUY':
                    signal.sl = signal.entry - risk
                    signal.tp1 = signal.entry + (risk * 1.2)
                    signal.tp2 = signal.entry + (risk * 2.0)
                else:
                    signal.sl = signal.entry + risk
                    signal.tp1 = signal.entry - (risk * 1.2)
                    signal.tp2 = signal.entry - (risk * 2.0)
                
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

            # Check for high slippage
            if entry_order and 'fills' in entry_order:
                total_filled = sum(float(fill['qty']) for fill in entry_order['fills'])
                if total_filled > 0:
                    avg_price = sum(float(fill['qty']) * float(fill['price']) for fill in entry_order['fills']) / total_filled
                    slippage = abs(avg_price - signal.entry) / signal.entry * 100
                    if slippage > 0.5:  # 0.5% slippage threshold
                        telegram.send_medium_priority(f"⚠️ High slippage: {slippage:.2f}% on {self.symbol} market order", msg_type='Slippage Warning')

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
            
            # Enhanced telegram notification with real-time price and WebSocket status
            ws_status = "✅ WebSocket" if self.ws_connected else "⚠️ REST API"
            telegram.send_high_priority(
                f"🚀 *ENTRY EXECUTED*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"🎯 Direction: {signal.direction}\n"
                f"💰 Entry: ${signal.entry:.2f}\n"
                f"📊 Market Price: ${current_market_price:.2f}\n"
                f"🔗 Data Source: {ws_status}\n"
                f"🛑 SL: ${signal.sl:.2f}\n"
                f"🎯 TP1: ${signal.tp1:.2f}\n"
                f"🎯 TP2: ${signal.tp2:.2f}\n"
                f"📊 Size: {position_size}\n"
                f"💹 Market Vol: {self.market_volatility:.2f}%\n"
                f"🔢 Daily Trades: {self.daily_trades}/{self.max_daily_trades}",
                msg_type='Entry Executed'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Execute entry error: {e}")
            return False

    def track_position_enhanced(self, signal, entry_order, size, orders):
        """Enhanced position tracking with more metadata"""
        position_id = entry_order['orderId']
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
        """Enhanced SL+ logic with improved accuracy and market conditions"""
        entry = position['entry']
        tp1 = position['tp1']
        direction = position['direction']
        
        # Calculate risk distance
        risk_distance = abs(tp1 - entry)
        
        # Enhanced time factor - more conservative early in trade
        time_since_entry = (datetime.utcnow() - position['opened_at']).total_seconds() / 3600
        
        # Dynamic profit target based on time and volatility
        if time_since_entry < 1:  # First hour - very conservative
            profit_threshold = 0.6  # 60% of risk distance
        elif time_since_entry < 4:  # 1-4 hours - moderate
            profit_threshold = 0.75  # 75% of risk distance
        else:  # After 4 hours - more aggressive
            profit_threshold = 0.8  # 80% of risk distance
        
        # Volatility adjustment
        current_volatility = self.market_volatility
        entry_volatility = position.get('market_volatility_at_entry', current_volatility)
        
        if current_volatility > entry_volatility * 1.3:  # High volatility
            profit_threshold *= 0.9  # More conservative
        elif current_volatility < entry_volatility * 0.7:  # Low volatility
            profit_threshold *= 1.1  # More aggressive
        
        # Calculate profit target
        if direction == 'BUY':
            profit_target = entry + (profit_threshold * risk_distance)
            # Add small buffer to prevent premature SL+ activation
            buffer = current_price * 0.001  # 0.1% buffer
            return current_price >= (profit_target + buffer)
        else:  # SELL
            profit_target = entry - (profit_threshold * risk_distance)
            # Add small buffer to prevent premature SL+ activation
            buffer = current_price * 0.001  # 0.1% buffer
            return current_price <= (profit_target - buffer)

    def _check_stuck_positions(self):
        """Check for positions that haven't been updated recently"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        for pos_id, position in self.active_positions.items():
            if position['last_price_check'] < cutoff_time:
                logger.warning(f"Position {pos_id} hasn't been updated recently")
                telegram.send_medium_priority(
                    f"⚠️ *POSITION ALERT*\n"
                    f"Position {pos_id} may be stuck\n"
                    f"Last update: {position['last_price_check']}",
                    msg_type='Stuck Position'
                )

    def get_current_price_enhanced(self, symbol):
        """Enhanced price fetching with WebSocket priority and fallback"""
        try:
            # Try WebSocket first (real-time)
            realtime_price = self.get_realtime_price(symbol)
            if realtime_price > 0:
                return realtime_price
            
            # Fallback to REST API
            if not self._rate_limit_check('price_check'):
                time.sleep(0.5)
                
            ticker = self._execute_with_retry(
                self.client.futures_symbol_ticker,
                symbol=symbol
            )
            return float(ticker['price'])
            
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            return 0

    def manage_positions_enhanced(self):
        """Enhanced position management with comprehensive monitoring"""
        try:
            for pos_id, position in list(self.active_positions.items()):
                try:
                    # Update last check time
                    position['last_price_check'] = datetime.utcnow()
                    
                    # Verify position is still active
                    if not self.verify_position_active(pos_id):
                        logger.warning(f"Position {pos_id} no longer active on exchange")
                        continue
                    
                    current_price = self.get_current_price_enhanced(self.symbol)
                    if current_price <= 0:
                        position['price_check_failures'] += 1
                        if position['price_check_failures'] >= 3:
                            logger.error(f"Multiple price check failures for position {pos_id}")
                        continue
                    
                    # Reset failure count on successful price fetch
                    position['price_check_failures'] = 0
                    
                    # Existing management logic with enhanced checks
                    self._manage_single_position(pos_id, position, current_price)
                    
                except Exception as e:
                    logger.error(f"Error managing position {pos_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Position management error: {e}")

    def _manage_single_position(self, pos_id, position, current_price):
        """Manage a single position with enhanced logic and better SL detection"""
        entry = position['entry']
        tp1 = position['tp1']
        tp2 = position['tp2']
        sl = position['sl']
        direction = position['direction']

        # Enhanced price validation
        if current_price <= 0:
            logger.warning(f"Invalid current price for position {pos_id}: {current_price}")
            return

        # Calculate targets with small tolerance for price fluctuations
        tolerance = current_price * 0.0005  # 0.05% tolerance
        
        if direction == 'BUY':
            tp1_hit = current_price >= (tp1 - tolerance)
            tp2_hit = current_price >= (tp2 - tolerance)
            sl_hit = current_price <= (sl + tolerance)
        else:  # SELL
            tp1_hit = current_price <= (tp1 + tolerance)
            tp2_hit = current_price <= (tp2 + tolerance)
            sl_hit = current_price >= (sl - tolerance)

        # 1. Enhanced SL+ logic with confirmation
        if not position['sl_moved_to_be']:
            if self.should_move_sl_to_be_enhanced(position, current_price):
                # Add confirmation check - ensure we're still in profit
                if direction == 'BUY' and current_price > entry:
                    self.move_sl_to_breakeven_enhanced(position)
                elif direction == 'SELL' and current_price < entry:
                    self.move_sl_to_breakeven_enhanced(position)

        # 2. Handle TP1 hit with confirmation
        if not position['tp1_hit'] and tp1_hit:
            # Confirm TP1 hit by checking if price stays above/below for a moment
            time.sleep(0.5)  # Brief pause
            confirm_price = self.get_current_price_enhanced(self.symbol)
            if confirm_price > 0:
                if direction == 'BUY' and confirm_price >= (tp1 - tolerance):
                    self._handle_tp1_hit(pos_id, position)
                elif direction == 'SELL' and confirm_price <= (tp1 + tolerance):
                    self._handle_tp1_hit(pos_id, position)

        # 3. Handle TP2 hit with confirmation
        if not position['tp2_hit'] and tp2_hit:
            # Confirm TP2 hit
            time.sleep(0.5)  # Brief pause
            confirm_price = self.get_current_price_enhanced(self.symbol)
            if confirm_price > 0:
                if direction == 'BUY' and confirm_price >= (tp2 - tolerance):
                    self._handle_tp2_hit(pos_id, position)
                elif direction == 'SELL' and confirm_price <= (tp2 + tolerance):
                    self._handle_tp2_hit(pos_id, position)

        # 4. Handle SL hit with confirmation
        if not position['notifications']['sl_notified'] and sl_hit:
            # Confirm SL hit
            time.sleep(0.5)  # Brief pause
            confirm_price = self.get_current_price_enhanced(self.symbol)
            if confirm_price > 0:
                if direction == 'BUY' and confirm_price <= (sl + tolerance):
                    self._handle_sl_hit(pos_id, position)
                elif direction == 'SELL' and confirm_price >= (sl - tolerance):
                    self._handle_sl_hit(pos_id, position)

    def move_sl_to_breakeven_enhanced(self, position):
        """Enhanced SL+ movement with improved accuracy and validation"""
        try:
            # Validate current position status
            if position['sl_moved_to_be']:
                logger.warning("SL already moved to breakeven")
                return False
                
            # Get current market price for validation
            current_price = self.get_current_price_enhanced(self.symbol)
            if current_price <= 0:
                logger.error("Cannot get current price for SL+ validation")
                return False
            
            # Validate that we're actually in profit before moving SL
            entry = position['entry']
            direction = position['direction']
            
            if direction == 'BUY' and current_price <= entry:
                logger.warning(f"BUY position not in profit: Entry={entry}, Current={current_price}")
                return False
            elif direction == 'SELL' and current_price >= entry:
                logger.warning(f"SELL position not in profit: Entry={entry}, Current={current_price}")
                return False
            
            # Cancel existing SL order with retry
            if position['orders'].get('sl_order'):
                try:
                    cancel_result = self._execute_with_retry(
                        self.client.futures_cancel_order,
                        symbol=self.symbol,
                        orderId=position['orders']['sl_order']['orderId'],
                        max_retries=3,
                        delay=1
                    )
                    if not cancel_result:
                        logger.error("Failed to cancel existing SL order")
                        return False
                except Exception as e:
                    logger.error(f"Error canceling SL order: {e}")
                    return False

            # Calculate new SL price with small buffer for safety
            buffer_percent = 0.02  # 0.02% buffer from entry
            if direction == 'BUY':
                new_sl_price = entry * (1 - buffer_percent)
            else:  # SELL
                new_sl_price = entry * (1 + buffer_percent)
            
            # Get tick size for price precision
            info = self.client.futures_exchange_info()
            tick_size = 0.01
            for s in info['symbols']:
                if s['symbol'] == self.symbol:
                    for f in s['filters']:
                        if f['filterType'] == 'PRICE_FILTER':
                            tick_size = float(f['tickSize'])
                            break
                    break
            
            # Round to tick size
            new_sl_price = round(round(new_sl_price / tick_size) * tick_size, 8)

            # Place new SL at breakeven with buffer
            opposite_side = 'SELL' if direction == 'BUY' else 'BUY'
            new_sl_order = self.place_stop_market_order_enhanced(
                opposite_side, 
                new_sl_price,
                position['size']
            )
            
            if new_sl_order:
                position['orders']['sl_order'] = new_sl_order
                position['sl'] = new_sl_price
                position['sl_moved_to_be'] = True
                
                # Send enhanced notification
                if not position['notifications']['sl_be_notified']:
                    profit_pnl = self._calculate_position_pnl(position)
                    telegram.send_high_priority(
                        f"📈 *SL MOVED TO BREAKEVEN*\n"
                        f"📌 PAIR: {self.symbol}\n"
                        f"🛡️ Risk eliminated - SL at: ${new_sl_price:.4f}\n"
                        f"💰 Current PnL: ${profit_pnl:.2f}\n"
                        f"💹 Market Price: ${current_price:.4f}\n"
                        f"⏰ Time in trade: {((datetime.utcnow() - position['opened_at']).total_seconds() / 3600):.1f}h",
                        msg_type='SL Breakeven'
                    )
                    position['notifications']['sl_be_notified'] = True
                
                logger.info(f"SL successfully moved to breakeven: {new_sl_price}")
                return True
            else:
                logger.error("Failed to place new SL order at breakeven")
                return False
                    
        except Exception as e:
            logger.error(f"Failed to move SL to breakeven: {e}")
            return False

    def _handle_tp1_hit(self, pos_id, position):
        """Handle TP1 hit event"""
        position['tp1_hit'] = True
        self.activate_trailing_stop_enhanced(position)
        
        if not position['notifications']['tp1_notified']:
            telegram.send_high_priority(
                f"🎯 *TP1 HIT!*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"💰 70% position closed at ${position['tp1']:.2f}\n"
                f"🔄 Trailing stop activated for remaining 30%\n"
                f"📊 Current Price: ${self.get_current_price_enhanced(self.symbol):.2f}",
                msg_type='TP1 Hit'
            )
            position['notifications']['tp1_notified'] = True

    def _handle_tp2_hit(self, pos_id, position):
        """Handle TP2 hit event"""
        position['tp2_hit'] = True
        
        if not position['notifications']['tp2_notified']:
            pnl = self._calculate_position_pnl(position)
            telegram.send_high_priority(
                f"🎯 *TP2 HIT!*\n"
                f"📌 PAIR: {self.symbol}\n"
                f"💰 Full position closed at ${position['tp2']:.2f}\n"
                f"🏆 Maximum profit achieved!\n"
                f"📈 Estimated PnL: ${pnl:.2f}",
                msg_type='TP2 Hit'
            )
            position['notifications']['tp2_notified'] = True
            
        # Update performance
        self.performance['wins'] += 1
        self.performance['consecutive_losses'] = 0
        self.performance['total_pnl'] += pnl
        
        # Remove position
        del self.active_positions[pos_id]

    def _handle_sl_hit(self, pos_id, position):
        """Handle SL hit event"""
        pnl = self._calculate_position_pnl(position)
        
        telegram.send_critical(
            f"🛑 *STOP LOSS HIT!*\n"
            f"📌 PAIR: {self.symbol}\n"
            f"⚠️ Position closed at ${position['sl']:.2f}\n"
            f"🛡️ Capital protected\n"
            f"📉 Estimated PnL: ${pnl:.2f}",
            msg_type='SL Hit'
        )
        position['notifications']['sl_notified'] = True
        
        # Update performance
        self.performance['losses'] += 1
        self.performance['consecutive_losses'] += 1
        self.performance['total_pnl'] += pnl
        
        # Remove position
        del self.active_positions[pos_id]

    def _calculate_position_pnl(self, position):
        """Calculate estimated PnL for a position"""
        try:
            current_price = self.get_current_price_enhanced(self.symbol)
            entry_price = position['entry']
            size = position['size']
            
            if position['direction'] == 'BUY':
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
            if position['orders'].get('sl_order'):
                self.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=position['orders']['sl_order']['orderId']
                )

            # Calculate remaining quantity (30% after TP1)
            remaining_size = round(position['size'] * 0.3, 4)
            
            # Adjust callback rate based on volatility
            base_callback = 1.5
            if self.market_volatility > 5.0:
                callback_rate = base_callback * 1.2  # More aggressive in high volatility
            else:
                callback_rate = base_callback
            
            # Place trailing stop market order
            opposite_side = 'SELL' if position['direction'] == 'BUY' else 'BUY'
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
                position['orders']['trailing_order'] = trailing_order
                position['trailing_active'] = True
                
                # Send notification
                if not position['notifications']['trailing_notified']:
                    telegram.send_medium_priority(
                        f"🔄 *TRAILING STOP ACTIVATED*\n"
                        f"📌 PAIR: {self.symbol}\n"
                        f"📊 Remaining size: {remaining_size}\n"
                        f"🎯 Callback rate: {callback_rate:.1f}%\n"
                        f"💹 Market volatility: {self.market_volatility:.2f}%",
                        msg_type='Trailing Stop'
                    )
                    position['notifications']['trailing_notified'] = True
                    
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
        telegram.send_medium_priority(
            f"🔄 *BOT SHUTDOWN*\n"
            f"Final Statistics:\n"
            f"📊 Performance: {self.get_enhanced_performance()}\n"
            f"⏰ Shutdown time: {datetime.utcnow()}",
            msg_type='Bot Shutdown'
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
    
    def test_binance_connection(self):
        """Test Binance API connection and provide diagnostics"""
        try:
            logger.info("Testing Binance API connection...")
            
            # Test 1: Server time (no auth required)
            try:
                server_time = self.client.get_server_time()
                logger.info(f"✅ Server time test passed: {server_time}")
            except Exception as e:
                logger.error(f"❌ Server time test failed: {e}")
                return False
            
            # Test 2: Exchange info (no auth required)
            try:
                exchange_info = self.client.futures_exchange_info()
                if isinstance(exchange_info, dict) and 'symbols' in exchange_info:
                    logger.info(f"✅ Exchange info test passed: {len(exchange_info['symbols'])} symbols")
                else:
                    logger.error("❌ Exchange info test failed: Invalid response format")
                    return False
            except Exception as e:
                logger.error(f"❌ Exchange info test failed: {e}")
                return False
            
            # Test 3: Account balance (requires auth)
            try:
                balance = self.client.futures_account_balance()
                if isinstance(balance, list):
                    usdt_balance = next((b for b in balance if b['asset'] == 'USDT'), None)
                    if usdt_balance:
                        logger.info(f"✅ Account balance test passed: {usdt_balance['balance']} USDT")
                    else:
                        logger.warning("⚠️ Account balance test passed but no USDT balance found")
                else:
                    logger.error("❌ Account balance test failed: Invalid response format")
                    return False
            except Exception as e:
                logger.error(f"❌ Account balance test failed: {e}")
                return False
            
            # Test 4: Position info (requires auth)
            try:
                positions = self.client.futures_position_information()
                if isinstance(positions, list):
                    active_positions = [p for p in positions if abs(float(p['positionAmt'])) > 0]
                    logger.info(f"✅ Position info test passed: {len(active_positions)} active positions")
                else:
                    logger.error("❌ Position info test failed: Invalid response format")
                    return False
            except Exception as e:
                logger.error(f"❌ Position info test failed: {e}")
                return False
            
            logger.info("🎉 All Binance API tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False

    def get_connection_diagnostics(self):
        """Get detailed connection diagnostics"""
        diagnostics = {
            'timestamp': datetime.utcnow().isoformat(),
            'api_key_configured': bool(config.BINANCE_API_KEY),
            'api_secret_configured': bool(config.BINANCE_SECRET),
            'connection_retry_count': self.connection_retry_count,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'websocket_connected': self.ws_connected,
            'rate_limit_status': {}
        }
        
        # Check rate limits
        for endpoint, calls in self.api_call_times.items():
            recent_calls = len([c for c in calls if (datetime.utcnow() - c).total_seconds() < 60])
            diagnostics['rate_limit_status'][endpoint] = {
                'recent_calls': recent_calls,
                'max_allowed': self.max_calls_per_minute,
                'limit_reached': recent_calls >= self.max_calls_per_minute
            }
        
        return diagnostics
    