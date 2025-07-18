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
                logger.info(f"Telegram bot connected: {safe_get(bot_info, 'result', 'username', default='N/A')}")
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
                    error_msg = safe_get(response.json(), 'description', 'Unknown error')
                    logger.error(f"Telegram send failed (attempt {attempt+1}): {error_msg}")
            except Exception as e:
                logger.error(f"Telegram send error (attempt {attempt+1}): {e}")
            time.sleep(2)
        logger.error(f"Telegram send failed after 3 attempts: {message}")
        return False
    
    def send_trade_alert(self, signal, bias, risk, position_size):
        """Send enhanced trade alert with ICT quality information"""
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        
        # ✅ ENHANCED: ICT Quality Information
        quality_emoji = {
            'PREMIUM': '💎',
            'STANDARD': '⭐',
            'BASIC': '📊',
            'LOW_QUALITY': '⚠️'
        }
        
        zone_emoji = {
            'PREMIUM': '🟢',
            'DISCOUNT': '🔴',
            'NEUTRAL': '🟡'
        }
        
        quality_icon = quality_emoji.get(signal.quality_class, '📊')
        zone_icon = zone_emoji.get(signal.zone_position, '🟡')
        
        # ✅ ENHANCED: ICT Metrics
        ict_summary = signal.get_ict_summary() if hasattr(signal, 'get_ict_summary') else {}
        
        message = f"""
📢 *ENTRY SIGNAL DETECTED*

{quality_icon} *QUALITY*: {signal.quality_class} ({signal.quality_score}/100)
{zone_icon} *ZONE*: {signal.zone_position}
📌 *PAIR*: {signal.pair}
🕒 *Time*: {timestamp}
📊 *Bias*: {safe_get(bias, 'direction', default='N/A')} ({safe_get(bias, 'strength', default=0):.1f})
🧠 *Signal Strength*: {signal.strength}
🧱 *OB + BOS Valid*: ✅
🕳 *FVG*: ✅
💧 *Liquidity Sweep*: {'✅' if signal.has_sweep else '❌'}
🔥 *Displacement Candle*: ✅

🎯 *ENTRY*: {signal.entry}
🛡 *SL*: {signal.sl}
🎯 *TP1*: {signal.tp1}
🎯 *TP2*: {signal.tp2}
⚖️ *Risk %*: {risk * 100:.1f}%
💰 *Size*: {position_size}

📈 *ICT ANALYSIS*:
• VWAP Distance: {ict_summary.get('vwap_distance', 'N/A')}
• Institutional Volume: {ict_summary.get('institutional_volume', 'N/A')}
• BOS Strength: {getattr(signal, 'bos_strength', 'N/A')}
• Mitigation Depth: {getattr(signal, 'mitigation_depth', 'N/A')}

📊 *Status*: Active
        """
        
        return self.send_message(message)

    def send_ict_quality_alert(self, signal, bias):
        """Send ICT quality analysis alert"""
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        
        quality_emoji = {
            'PREMIUM': '💎',
            'STANDARD': '⭐',
            'BASIC': '📊',
            'LOW_QUALITY': '⚠️'
        }
        
        quality_icon = quality_emoji.get(signal.quality_class, '📊')
        
        message = f"""
{quality_icon} *ICT QUALITY ANALYSIS*

📌 *PAIR*: {signal.pair}
🕒 *Time*: {timestamp}
📊 *Quality Score*: {signal.quality_score}/100
🏷️ *Quality Class*: {signal.quality_class}
🎯 *Priority*: {signal.priority}

📈 *ICT METRICS*:
• Zone Quality: {signal.ict_metrics.get('zone_quality', 0)}/25
• Volume Quality: {signal.ict_metrics.get('volume_quality', 0)}/25
• Signal Quality: {signal.ict_metrics.get('signal_quality', 0)}/25
• Structure Quality: {signal.ict_metrics.get('structure_quality', 0)}/25

📍 *ZONE ANALYSIS*:
• Position: {signal.zone_position}
• VWAP Distance: {signal.vwap_distance:.2%}
• Institutional Volume: {signal.institutional_volume_strength:.2f}

📊 *BIAS*: {safe_get(bias, 'direction', default='N/A')} ({safe_get(bias, 'strength', default=0):.1f})
        """
        
        return self.send_message(message)

    def send_premium_signal_alert(self, signal, bias):
        """Send special alert for premium signals"""
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        
        message = f"""
💎 *PREMIUM SIGNAL DETECTED* 💎

📌 *PAIR*: {signal.pair}
🕒 *Time*: {timestamp}
📊 *Quality Score*: {signal.quality_score}/100
🏷️ *Quality Class*: {signal.quality_class}
🎯 *Priority*: {signal.priority}

📍 *ZONE*: {signal.zone_position}
📈 *VWAP Distance*: {signal.vwap_distance:.2%}
💪 *Institutional Volume*: {signal.institutional_volume_strength:.2f}

🎯 *ENTRY*: {signal.entry}
🛡 *SL*: {signal.sl}
🎯 *TP1*: {signal.tp1}
🎯 *TP2*: {signal.tp2}

📊 *BIAS*: {safe_get(bias, 'direction', default='N/A')} ({safe_get(bias, 'strength', default=0):.1f})
🧠 *Signal Strength*: {signal.strength}

🚨 *HIGH CONFIDENCE SIGNAL*
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

    def send_main_menu(self):
        """Send custom keyboard with main menu commands"""
        keyboard = {
            "keyboard": [
                [{"text": "/status"}, {"text": "/balance"}, {"text": "/drawdown"}],
                [{"text": "/summary"}, {"text": "/settings"}, {"text": "/uptime"}],
                [{"text": "/pause"}, {"text": "/resume"}, {"text": "/help"}],
                [{"text": "/shutdown"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        payload = {
            'chat_id': self.chat_id,
            'text': "Pilih menu:",
            'reply_markup': keyboard
        }
        url = f"{self.base_url}/sendMessage"
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send main menu: {e}")

    def poll_messages(self, timeout=30):
        """Poll for new messages using getUpdates"""
        url = f"{self.base_url}/getUpdates"
        params = {'timeout': timeout}
        if self._last_update_id:
            params['offset'] = self._last_update_id + 1
        try:
            response = requests.get(url, params=params, timeout=timeout+5)
            if response.status_code == 200:
                updates = safe_get(response.json(), 'result', default=[])
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
                self._last_update_id = safe_get(update, 'update_id', default=None)
                if 'message' in update:
                    msg = safe_get(update, 'message', default=None)
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

# Contoh perbaikan pada akses bias dan hasil API Telegram
def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d