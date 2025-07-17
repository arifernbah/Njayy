import requests
import json
from datetime import datetime
from core.config import config
from utils.logger import logger
import time
import threading

class TelegramBot:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self._polling_active = False
        self._polling_thread = None
        self._last_update_id = None
        self.message_handler = None  # User can set this to a function
        
        # Test connection on init
        self.test_connection()
    
    def test_connection(self):
        """Test Telegram bot connection"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"Telegram bot connected: {bot_info['result']['username']}")
                return True
            else:
                logger.error(f"Telegram connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False
    
    def send_message(self, message, parse_mode=None):
        """Send message to Telegram with retry, no formatting (plain text)"""
        for attempt in range(3):
            try:
                if not config.ENABLE_TELEGRAM:
                    logger.info(f"Telegram disabled. Message: {message}")
                    return True
                url = f"{self.base_url}/sendMessage"
                payload = {
                    'chat_id': self.chat_id,
                    'text': message
                }
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    logger.info("Telegram message sent successfully")
                    return True
                else:
                    error_msg = response.json().get('description', 'Unknown error')
                    logger.error(f"Telegram send failed (attempt {attempt+1}): {error_msg}")
            except Exception as e:
                logger.error(f"Telegram send error (attempt {attempt+1}): {e}")
            time.sleep(2)
        logger.error(f"Telegram send failed after 3 attempts: {message}")
        return False
    
    def send_trade_alert(self, signal, bias, risk, position_size):
        """Send formatted trade alert"""
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        
        message = f"""
📢 *ENTRY SIGNAL DETECTED*

📌 *PAIR*: {signal.pair}
🕒 *Time*: {timestamp}
📊 *Bias*: {bias['direction']} ({bias['strength']})
🧠 *Signal Strength*: {signal.strength}
🧱 *OB + BOS Valid*: ✅
🕳 *FVG*: ✅
💧 *Liquidity Sweep*: ✅
🔥 *Displacement Candle*: ✅

🎯 *ENTRY*: {signal.entry}
🛡 *SL*: {signal.sl}
🎯 *TP1*: {signal.tp1}
🎯 *TP2*: {signal.tp2}
⚖️ *Risk %*: {risk * 100:.1f}%
💰 *Size*: {position_size}

📈 *Status*: Active
        """
        
        return self.send_message(message)
    
    def send_trade_update(self, trade_id, status, pnl=None):
        """Send trade update notification"""
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        
        status_emoji = {
            'closed_profit': '✅',
            'closed_loss': '❌',
            'partial_profit': '🔄',
            'modified': '⚙️'
        }
        
        message = f"""
{status_emoji.get(status, '📊')} *TRADE UPDATE*

🕒 *Time*: {timestamp}
🔢 *Trade ID*: {trade_id}
📊 *Status*: {status.replace('_', ' ').title()}
"""
        
        if pnl is not None:
            message += f"💰 *P&L*: {pnl:.2f}$\n"
        
        return self.send_message(message)
    
    def send_daily_summary(self, summary):
        """Send daily performance summary"""
        message = f"""
📊 *DAILY SUMMARY*

📅 *Date*: {datetime.utcnow().strftime("%Y-%m-%d")}
🎯 *Total Trades*: {summary.get('total_trades', 0)}
✅ *Winners*: {summary.get('winners', 0)}
❌ *Losers*: {summary.get('losers', 0)}
📈 *Win Rate*: {summary.get('win_rate', 0):.1f}%
💰 *Total P&L*: {summary.get('total_pnl', 0):.2f}$
📊 *Best Trade*: {summary.get('best_trade', 0):.2f}$
📉 *Worst Trade*: {summary.get('worst_trade', 0):.2f}$

🤖 *Bot Status*: Running
        """
        
        return self.send_message(message)
    
    def send_error_alert(self, error_msg, error_type="General"):
        """Send error alert"""
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        
        message = f"""
⚠️ *ERROR ALERT*

🕒 *Time*: {timestamp}
🔴 *Type*: {error_type}
📝 *Message*: {error_msg}

🤖 *Bot Status*: Checking...
        """
        
        return self.send_message(message)
    
    def send_startup_message(self, bot_version, author):
        """Send bot startup message"""
        message = f"""
🚀 *ICT Bot {bot_version} Started*

👨‍💻 *Author*: {author}
🕒 *Started*: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
📊 *Settings*:
- Max Daily Trades: {config.MAX_DAILY_TRADES}
- Default Risk: {config.DEFAULT_RISK}%
- Min Signal Strength: {config.MIN_SIGNAL_STRENGTH}
- Loop Interval: {config.LOOP_INTERVAL}s

🤖 *Status*: Bot is running...
        """
        
        return self.send_message(message)
    
    def send_session_info(self, session_name, active=True):
        """Send trading session info"""
        status = "🟢 ACTIVE" if active else "🔴 INACTIVE"
        
        message = f"""
⏰ *TRADING SESSION*

📍 *Session*: {session_name}
📊 *Status*: {status}
🕒 *Time*: {datetime.utcnow().strftime("%H:%M UTC")}

🤖 *Bot*: Monitoring...
        """
        
        return self.send_message(message)

    def poll_messages(self, timeout=30):
        """Poll for new messages using getUpdates"""
        url = f"{self.base_url}/getUpdates"
        params = {'timeout': timeout}
        if self._last_update_id:
            params['offset'] = self._last_update_id + 1
        try:
            response = requests.get(url, params=params, timeout=timeout+5)
            if response.status_code == 200:
                updates = response.json()['result']
                return updates
            else:
                logger.error(f"Polling failed: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Polling error: {e}")
            return []

    def start_polling(self, handler=None, interval=2):
        """Start background polling for incoming messages"""
        if self._polling_active:
            logger.info("Polling already active.")
            return
        self._polling_active = True
        if handler:
            self.message_handler = handler
        self._polling_thread = threading.Thread(target=self._polling_loop, args=(interval,), daemon=True)
        self._polling_thread.start()
        logger.info("Started Telegram polling thread.")

    def stop_polling(self):
        self._polling_active = False
        if self._polling_thread:
            self._polling_thread.join(timeout=2)
            logger.info("Stopped Telegram polling thread.")

    def _polling_loop(self, interval):
        while self._polling_active:
            updates = self.poll_messages()
            for update in updates:
                self._last_update_id = update['update_id']
                if 'message' in update:
                    msg = update['message']
                    if self.message_handler:
                        try:
                            self.message_handler(msg)
                        except Exception as e:
                            logger.error(f"Message handler error: {e}")
                    else:
                        logger.info(f"Received message: {msg}")
            time.sleep(interval)

    def set_message_handler(self, handler):
        """Set a custom handler for incoming messages"""
        self.message_handler = handler

# Create global telegram instance
telegram = TelegramBot()