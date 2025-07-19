import requests
import json
from datetime import datetime
from core.config import config
from utils.logger import logger

class TelegramBot:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
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
    
    def send_message(self, message, parse_mode="Markdown"):
        """Send message to Telegram"""
        try:
            if not config.ENABLE_TELEGRAM:
                logger.info(f"Telegram disabled. Message: {message}")
                return True
            
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                error_msg = response.json().get('description', 'Unknown error')
                logger.error(f"Telegram send failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
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

# Create global telegram instance
telegram = TelegramBot()