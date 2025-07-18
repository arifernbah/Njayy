#!/usr/bin/env python3
"""
Binance ICT Trading Bot - No WebSocket Version
Fixed version without WebSocket to avoid HTTP 451 errors
"""

import time
import requests
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import threading
from typing import Dict, List, Optional

# Configuration
class Config:
    # Binance API
    API_KEY = "your_api_key_here"
    SECRET_KEY = "your_secret_key_here"
    BASE_URL = "https://fapi.binance.com"
    
    # Trading settings
    TRADING_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    POSITION_SIZE_PERCENT = 1.0  # 1% of balance per trade
    MAX_POSITIONS = 3
    
    # ICT Settings
    KILLZONE_ASIA = (8, 18)  # 08:00-18:00 WIB
    KILLZONE_NY = (19, 22)   # 19:00-22:00 WIB
    MIN_SIGNAL_STRENGTH = 8
    MIN_BIAS_STRENGTH = 7
    
    # Risk Management
    STOP_LOSS_PERCENT = 2.0
    TAKE_PROFIT_1_PERCENT = 4.0
    TAKE_PROFIT_2_PERCENT = 8.0
    
    # Telegram (optional)
    TELEGRAM_BOT_TOKEN = "your_telegram_token_here"
    TELEGRAM_CHAT_ID = "your_chat_id_here"
    
    # Loop settings
    LOOP_INTERVAL = 30  # seconds
    PRICE_CHECK_INTERVAL = 5  # seconds

class Logger:
    @staticmethod
    def info(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[INFO] {timestamp} - {message}")
    
    @staticmethod
    def error(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[ERROR] {timestamp} - {message}")
    
    @staticmethod
    def warning(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[WARNING] {timestamp} - {message}")

class BinanceAPI:
    def __init__(self):
        self.api_key = Config.API_KEY
        self.secret_key = Config.SECRET_KEY
        self.base_url = Config.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })
    
    def _generate_signature(self, params):
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, method, endpoint, params=None, signed=False):
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, params=params)
            elif method == 'DELETE':
                response = self.session.delete(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                Logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            Logger.error(f"Request error: {e}")
            return None
    
    def get_account_info(self):
        """Get account information"""
        return self._make_request('GET', '/fapi/v2/account', signed=True)
    
    def get_balance(self):
        """Get USDT balance"""
        account = self.get_account_info()
        if account and 'assets' in account:
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    return float(asset['walletBalance'])
        return 0.0
    
    def get_positions(self):
        """Get open positions"""
        account = self.get_account_info()
        if account and 'positions' in account:
            return [pos for pos in account['positions'] if float(pos['positionAmt']) != 0]
        return []
    
    def get_price(self, symbol):
        """Get current price using REST API"""
        endpoint = f"/fapi/v1/ticker/price"
        params = {'symbol': symbol}
        result = self._make_request('GET', endpoint, params)
        if result:
            return float(result['price'])
        return None
    
    def get_klines(self, symbol, interval='1m', limit=100):
        """Get candlestick data"""
        endpoint = "/fapi/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        return self._make_request('GET', endpoint, params)
    
    def place_order(self, symbol, side, quantity, price=None, order_type='MARKET'):
        """Place order"""
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity
        }
        
        if price and order_type == 'LIMIT':
            params['price'] = price
            params['timeInForce'] = 'GTC'
        
        return self._make_request('POST', '/fapi/v1/order', params, signed=True)
    
    def cancel_order(self, symbol, order_id):
        """Cancel order"""
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_request('DELETE', '/fapi/v1/order', params, signed=True)

class ICTAnalyzer:
    def __init__(self):
        self.last_analysis = {}
    
    def analyze_bias(self, symbol, klines_data):
        """Analyze market bias using ICT concepts"""
        if not klines_data or len(klines_data) < 50:
            return {'valid': False, 'direction': 'neutral', 'strength': 0}
        
        try:
            # Convert klines to OHLCV
            closes = [float(k[4]) for k in klines_data]
            highs = [float(k[2]) for k in klines_data]
            lows = [float(k[3]) for k in klines_data]
            volumes = [float(k[5]) for k in klines_data]
            
            # ICT Bias Analysis
            current_price = closes[-1]
            sma_20 = sum(closes[-20:]) / 20
            sma_50 = sum(closes[-50:]) / 50
            
            # Volume analysis
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Price momentum
            price_change = (current_price - closes[-5]) / closes[-5] * 100
            
            # ICT Bias calculation
            bias_score = 0
            
            # Trend bias
            if current_price > sma_20 > sma_50:
                bias_score += 3  # Strong bullish
            elif current_price > sma_20:
                bias_score += 2  # Moderate bullish
            elif current_price < sma_20 < sma_50:
                bias_score -= 3  # Strong bearish
            elif current_price < sma_20:
                bias_score -= 2  # Moderate bearish
            
            # Volume confirmation
            if volume_ratio > 1.5:
                bias_score += 1
            elif volume_ratio < 0.5:
                bias_score -= 1
            
            # Momentum
            if price_change > 1:
                bias_score += 1
            elif price_change < -1:
                bias_score -= 1
            
            # Determine direction and strength
            if bias_score >= 3:
                direction = 'bullish'
                strength = min(10, 5 + bias_score)
            elif bias_score <= -3:
                direction = 'bearish'
                strength = min(10, 5 + abs(bias_score))
            else:
                direction = 'neutral'
                strength = 5
            
            return {
                'valid': True,
                'direction': direction,
                'strength': strength,
                'price': current_price,
                'volume_ratio': volume_ratio,
                'momentum': price_change
            }
            
        except Exception as e:
            Logger.error(f"Bias analysis error for {symbol}: {e}")
            return {'valid': False, 'direction': 'neutral', 'strength': 0}

class ICTSignalFinder:
    def __init__(self):
        self.last_signals = {}
    
    def find_signals(self, symbol, bias, klines_data):
        """Find ICT trading signals"""
        if not bias['valid'] or bias['strength'] < Config.MIN_BIAS_STRENGTH:
            return []
        
        try:
            # Convert klines to OHLCV
            opens = [float(k[1]) for k in klines_data]
            highs = [float(k[2]) for k in klines_data]
            lows = [float(k[3]) for k in klines_data]
            closes = [float(k[4]) for k in klines_data]
            
            signals = []
            current_price = closes[-1]
            
            # ICT Signal Detection
            if bias['direction'] == 'bullish':
                # Bullish signals
                if self._check_bullish_setup(klines_data):
                    signal = {
                        'symbol': symbol,
                        'side': 'BUY',
                        'entry': current_price,
                        'sl': current_price * (1 - Config.STOP_LOSS_PERCENT / 100),
                        'tp1': current_price * (1 + Config.TAKE_PROFIT_1_PERCENT / 100),
                        'tp2': current_price * (1 + Config.TAKE_PROFIT_2_PERCENT / 100),
                        'strength': bias['strength'],
                        'bias': bias['strength'],
                        'regime': 8,
                        'volatility': 5,
                        'timestamp': datetime.now()
                    }
                    signals.append(signal)
            
            elif bias['direction'] == 'bearish':
                # Bearish signals
                if self._check_bearish_setup(klines_data):
                    signal = {
                        'symbol': symbol,
                        'side': 'SELL',
                        'entry': current_price,
                        'sl': current_price * (1 + Config.STOP_LOSS_PERCENT / 100),
                        'tp1': current_price * (1 - Config.TAKE_PROFIT_1_PERCENT / 100),
                        'tp2': current_price * (1 - Config.TAKE_PROFIT_2_PERCENT / 100),
                        'strength': bias['strength'],
                        'bias': bias['strength'],
                        'regime': 8,
                        'volatility': 5,
                        'timestamp': datetime.now()
                    }
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            Logger.error(f"Signal finding error for {symbol}: {e}")
            return []
    
    def _check_bullish_setup(self, klines_data):
        """Check for bullish ICT setup"""
        if len(klines_data) < 10:
            return False
        
        # Simple bullish setup check
        closes = [float(k[4]) for k in klines_data]
        current = closes[-1]
        prev = closes[-2]
        
        # Price is moving up
        return current > prev
    
    def _check_bearish_setup(self, klines_data):
        """Check for bearish ICT setup"""
        if len(klines_data) < 10:
            return False
        
        # Simple bearish setup check
        closes = [float(k[4]) for k in klines_data]
        current = closes[-1]
        prev = closes[-2]
        
        # Price is moving down
        return current < prev

class ICTTrader:
    def __init__(self):
        self.api = BinanceAPI()
        self.analyzer = ICTAnalyzer()
        self.signal_finder = ICTSignalFinder()
        self.last_trade_time = {}
        self.positions = {}
    
    def is_killzone_active(self):
        """Check if current time is in ICT killzone"""
        now = datetime.now()
        hour = now.hour
        
        # Asia + London killzone (08:00-18:00 WIB)
        if Config.KILLZONE_ASIA[0] <= hour <= Config.KILLZONE_ASIA[1]:
            return True
        
        # New York killzone (19:00-22:00 WIB)
        if Config.KILLZONE_NY[0] <= hour <= Config.KILLZONE_NY[1]:
            return True
        
        return False
    
    def calculate_position_size(self, balance, price):
        """Calculate position size based on risk"""
        risk_amount = balance * (Config.POSITION_SIZE_PERCENT / 100)
        return risk_amount / price
    
    def execute_trade(self, signal):
        """Execute trading signal"""
        try:
            symbol = signal['symbol']
            side = signal['side']
            entry_price = signal['entry']
            
            # Check cooldown
            if symbol in self.last_trade_time:
                time_diff = (datetime.now() - self.last_trade_time[symbol]).total_seconds()
                if time_diff < 300:  # 5 minutes cooldown
                    Logger.warning(f"Cooldown active for {symbol}")
                    return False
            
            # Get current balance
            balance = self.api.get_balance()
            if balance < 10:  # Minimum $10
                Logger.warning(f"Insufficient balance: ${balance}")
                return False
            
            # Calculate position size
            quantity = self.calculate_position_size(balance, entry_price)
            
            # Round quantity to appropriate decimal places
            if symbol == "BTCUSDT":
                quantity = round(quantity, 3)
            elif symbol == "ETHUSDT":
                quantity = round(quantity, 4)
            else:
                quantity = round(quantity, 2)
            
            if quantity <= 0:
                Logger.warning(f"Invalid quantity: {quantity}")
                return False
            
            # Place order
            Logger.info(f"Placing {side} order for {quantity} {symbol} at {entry_price}")
            result = self.api.place_order(symbol, side, quantity)
            
            if result and result.get('orderId'):
                self.last_trade_time[symbol] = datetime.now()
                Logger.info(f"✅ Order placed successfully: {result['orderId']}")
                
                # Send Telegram notification
                self.send_telegram_notification(signal, result['orderId'])
                return True
            else:
                Logger.error(f"❌ Order failed for {symbol}")
                return False
                
        except Exception as e:
            Logger.error(f"Trade execution error: {e}")
            return False
    
    def send_telegram_notification(self, signal, order_id):
        """Send Telegram notification"""
        if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
            return
        
        try:
            message = f"""
🚀 *ICT TRADING SIGNAL EXECUTED*

📊 *Symbol*: {signal['symbol']}
📈 *Side*: {signal['side']}
💰 *Entry*: ${signal['entry']:.4f}
🛡️ *Stop Loss*: ${signal['sl']:.4f}
🎯 *TP1*: ${signal['tp1']:.4f}
🎯 *TP2*: ${signal['tp2']:.4f}
💪 *Signal Strength*: {signal['strength']}/10
🧠 *Bias Strength*: {signal['bias']}/10
⏰ *Time*: {datetime.now().strftime('%H:%M:%S')}
🆔 *Order ID*: {order_id}

🎯 *Good Luck Trading!*
"""
            
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': Config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data)
            if response.status_code == 200:
                Logger.info("Telegram notification sent")
            else:
                Logger.error(f"Telegram error: {response.text}")
                
        except Exception as e:
            Logger.error(f"Telegram notification error: {e}")
    
    def manage_positions(self):
        """Manage open positions"""
        try:
            positions = self.api.get_positions()
            for position in positions:
                symbol = position['symbol']
                side = position['side']
                quantity = float(position['positionAmt'])
                entry_price = float(position['entryPrice'])
                unrealized_pnl = float(position['unRealizedProfit'])
                
                if quantity != 0:
                    Logger.info(f"Position: {symbol} {side} {quantity} @ {entry_price} PnL: {unrealized_pnl}")
                    
        except Exception as e:
            Logger.error(f"Position management error: {e}")
    
    def get_account_status(self):
        """Get account status"""
        try:
            balance = self.api.get_balance()
            positions = self.api.get_positions()
            
            return {
                'balance': balance,
                'positions_count': len(positions),
                'killzone_active': self.is_killzone_active()
            }
            
        except Exception as e:
            Logger.error(f"Status check error: {e}")
            return None

class ICTBot:
    def __init__(self):
        self.trader = ICTTrader()
        self.running = False
    
    def start(self):
        """Start the bot"""
        Logger.info("🚀 Starting ICT Trading Bot (No WebSocket Version)")
        Logger.info("✅ Fixed: No WebSocket to avoid HTTP 451 errors")
        
        # Test connection
        status = self.trader.get_account_status()
        if not status:
            Logger.error("❌ Failed to connect to Binance API")
            return
        
        Logger.info(f"✅ Connected to Binance API")
        Logger.info(f"💰 Balance: ${status['balance']:.2f}")
        Logger.info(f"📊 Open Positions: {status['positions_count']}")
        
        self.running = True
        
        while self.running:
            try:
                self.main_loop()
                time.sleep(Config.LOOP_INTERVAL)
                
            except KeyboardInterrupt:
                Logger.info("🛑 Bot stopped by user")
                self.running = False
                break
            except Exception as e:
                Logger.error(f"Main loop error: {e}")
                time.sleep(10)
    
    def main_loop(self):
        """Main trading loop"""
        try:
            # Check killzone
            if not self.trader.is_killzone_active():
                Logger.info("⏰ Outside killzone, waiting...")
                return
            
            # Process each trading pair
            for symbol in Config.TRADING_PAIRS:
                # Get market data
                klines = self.trader.api.get_klines(symbol, '1m', 100)
                if not klines:
                    continue
                
                # Analyze bias
                bias = self.trader.analyzer.analyze_bias(symbol, klines)
                if not bias['valid']:
                    continue
                
                # Find signals
                signals = self.trader.signal_finder.find_signals(symbol, bias, klines)
                
                # Execute signals
                for signal in signals:
                    if signal['strength'] >= Config.MIN_SIGNAL_STRENGTH:
                        Logger.info(f"🎯 Signal found for {symbol}: {signal['side']} @ {signal['entry']}")
                        self.trader.execute_trade(signal)
            
            # Manage positions
            self.trader.manage_positions()
            
        except Exception as e:
            Logger.error(f"Main loop error: {e}")

def main():
    """Main function"""
    print("=" * 60)
    print("🚀 BINANCE ICT TRADING BOT - NO WEBSOCKET VERSION")
    print("✅ Fixed: No WebSocket to avoid HTTP 451 errors")
    print("=" * 60)
    
    # Check configuration
    if Config.API_KEY == "your_api_key_here":
        print("❌ Please set your Binance API key in Config.API_KEY")
        return
    
    if Config.SECRET_KEY == "your_secret_key_here":
        print("❌ Please set your Binance secret key in Config.SECRET_KEY")
        return
    
    # Start bot
    bot = ICTBot()
    bot.start()

if __name__ == "__main__":
    main()