import requests
import json
from datetime import datetime, timedelta
from core.config import config
from utils.logger import logger
import time
import threading
from collections import defaultdict, deque
import hashlib

class TelegramBot:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self._polling_active = False
        self._polling_thread = None
        self._last_update_id = None
        self.message_handler = None
        
        # Anti-spam system
        self.message_queue = deque(maxlen=50)  # Queue untuk batching
        self.sent_messages = {}  # Track sent messages untuk duplicate detection
        self.rate_limits = defaultdict(list)  # Rate limiting per message type
        self.last_notification = {}  # Last notification time per type
        self.batch_timer = None
        self.batch_interval = 30  # Batch messages every 30 seconds
        
        # Message priorities
        self.priorities = {
            'CRITICAL': 1,    # Errors, SL hits, major issues
            'HIGH': 2,        # Entry/Exit signals, TP hits
            'MEDIUM': 3,      # Status updates, balance info
            'LOW': 4,         # Debug info, minor updates
            'DEBUG': 5        # Detailed logs, verbose info
        }
        
        # Rate limit settings (messages per time window)
        self.rate_limits_config = {
            'CRITICAL': {'max': 10, 'window': 300},    # 10 per 5 minutes
            'HIGH': {'max': 20, 'window': 300},        # 20 per 5 minutes
            'MEDIUM': {'max': 15, 'window': 600},      # 15 per 10 minutes
            'LOW': {'max': 10, 'window': 900},         # 10 per 15 minutes
            'DEBUG': {'max': 5, 'window': 1800}        # 5 per 30 minutes
        }
        
        # Cooldown periods (seconds between same type messages)
        self.cooldowns = {
            'CRITICAL': 60,   # 1 minute
            'HIGH': 120,      # 2 minutes
            'MEDIUM': 300,    # 5 minutes
            'LOW': 600,       # 10 minutes
            'DEBUG': 1800     # 30 minutes
        }
        
        # Start batch processing
        self._start_batch_processor()
        
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
    
    def _start_batch_processor(self):
        """Start background batch processor"""
        def batch_loop():
            while True:
                try:
                    self._process_batch()
                    time.sleep(self.batch_interval)
                except Exception as e:
                    logger.error(f"Batch processor error: {e}")
                    time.sleep(10)
        
        batch_thread = threading.Thread(target=batch_loop, daemon=True)
        batch_thread.start()
    
    def _process_batch(self):
        """Process queued messages in batches"""
        if not self.message_queue:
            return
            
        # Group messages by priority
        batches = defaultdict(list)
        while self.message_queue:
            msg_data = self.message_queue.popleft()
            priority = msg_data.get('priority', 'MEDIUM')
            batches[priority].append(msg_data)
        
        # Send batches in priority order
        for priority in sorted(self.priorities.keys(), key=lambda x: self.priorities[x]):
            if batches[priority]:
                self._send_batch(batches[priority], priority)
    
    def _send_batch(self, messages, priority):
        """Send a batch of messages"""
        if len(messages) == 1:
            # Single message, send directly
            self._send_single_message(messages[0])
        else:
            # Multiple messages, combine into summary
            self._send_batch_summary(messages, priority)
    
    def _send_batch_summary(self, messages, priority):
        """Send a summary of multiple messages"""
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        
        summary = f"📊 *BATCH UPDATE - {priority}*\n"
        summary += f"🕒 *Time*: {timestamp}\n"
        summary += f"📝 *Messages*: {len(messages)}\n\n"
        
        # Group by message type
        type_counts = defaultdict(int)
        for msg in messages:
            msg_type = msg.get('type', 'General')
            type_counts[msg_type] += 1
        
        for msg_type, count in type_counts.items():
            summary += f"• {msg_type}: {count}\n"
        
        summary += f"\n🤖 *Bot Status*: Active"
        
        self._send_single_message({
            'message': summary,
            'priority': priority,
            'type': 'Batch Summary'
        })
    
    def _send_single_message(self, msg_data):
        """Send a single message with all checks"""
        message = msg_data['message']
        priority = msg_data.get('priority', 'MEDIUM')
        msg_type = msg_data.get('type', 'General')
        
        # Check if message is disabled
        if not config.ENABLE_TELEGRAM:
            logger.info(f"Telegram disabled. Message: {message[:100]}...")
            return True
        
        # Check rate limits
        if not self._check_rate_limit(priority):
            logger.warning(f"Rate limit exceeded for {priority} messages")
            return False
        
        # Check cooldown
        if not self._check_cooldown(msg_type, priority):
            logger.info(f"Cooldown active for {msg_type}")
            return False
        
        # Check for duplicates
        if self._is_duplicate(message, priority):
            logger.info(f"Duplicate message detected: {msg_type}")
            return True
        
        # Send message
        success = self._send_raw_message(message)
        if success:
            self._record_sent_message(message, priority, msg_type)
        
        return success
    
    def _check_rate_limit(self, priority):
        """Check if message is within rate limits"""
        now = time.time()
        window = self.rate_limits_config[priority]['window']
        max_messages = self.rate_limits_config[priority]['max']
        
        # Clean old entries
        self.rate_limits[priority] = [t for t in self.rate_limits[priority] if now - t < window]
        
        # Check if limit exceeded
        if len(self.rate_limits[priority]) >= max_messages:
            return False
        
        # Add current timestamp
        self.rate_limits[priority].append(now)
        return True
    
    def _check_cooldown(self, msg_type, priority):
        """Check if enough time has passed since last similar message"""
        now = time.time()
        cooldown = self.cooldowns[priority]
        
        key = f"{msg_type}_{priority}"
        last_time = self.last_notification.get(key, 0)
        
        if now - last_time < cooldown:
            return False
        
        self.last_notification[key] = now
        return True
    
    def _is_duplicate(self, message, priority):
        """Check if message is duplicate"""
        # Create hash of message content
        msg_hash = hashlib.md5(message.encode()).hexdigest()
        
        # Check if we've sent this recently
        now = time.time()
        if msg_hash in self.sent_messages:
            last_sent = self.sent_messages[msg_hash]['time']
            count = self.sent_messages[msg_hash]['count']
            
            # Allow duplicates after 1 hour, but track count
            if now - last_sent < 3600:
                if count >= 3:  # Max 3 duplicates per hour
                    return True
                self.sent_messages[msg_hash]['count'] += 1
            else:
                # Reset after 1 hour
                self.sent_messages[msg_hash] = {'time': now, 'count': 1}
        else:
            self.sent_messages[msg_hash] = {'time': now, 'count': 1}
        
        return False
    
    def _record_sent_message(self, message, priority, msg_type):
        """Record sent message for tracking"""
        msg_hash = hashlib.md5(message.encode()).hexdigest()
        self.sent_messages[msg_hash] = {
            'time': time.time(),
            'count': 1,
            'priority': priority,
            'type': msg_type
        }
    
    def _send_raw_message(self, message):
        """Send raw message to Telegram with retry"""
        for attempt in range(3):
            try:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
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
        
        logger.error(f"Telegram send failed after 3 attempts")
        return False
    
    def send_message(self, message, priority='MEDIUM', msg_type='General', immediate=False):
        """Send message with anti-spam protection"""
        if immediate:
            # Send immediately for critical messages
            return self._send_single_message({
                'message': message,
                'priority': priority,
                'type': msg_type
            })
        else:
            # Queue for batch processing
            self.message_queue.append({
                'message': message,
                'priority': priority,
                'type': msg_type,
                'timestamp': time.time()
            })
            return True
    
    def send_critical(self, message, msg_type='Critical'):
        """Send critical message immediately"""
        return self.send_message(message, priority='CRITICAL', msg_type=msg_type, immediate=True)
    
    def send_high_priority(self, message, msg_type='High Priority'):
        """Send high priority message"""
        return self.send_message(message, priority='HIGH', msg_type=msg_type)
    
    def send_medium_priority(self, message, msg_type='Medium Priority'):
        """Send medium priority message"""
        return self.send_message(message, priority='MEDIUM', msg_type=msg_type)
    
    def send_low_priority(self, message, msg_type='Low Priority'):
        """Send low priority message"""
        return self.send_message(message, priority='LOW', msg_type=msg_type)
    
    def send_debug(self, message, msg_type='Debug'):
        """Send debug message (lowest priority)"""
        return self.send_message(message, priority='DEBUG', msg_type=msg_type)
    
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
        
        return self.send_high_priority(message, msg_type='Trade Alert')
    
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
        
        # Determine priority based on status
        if status in ['closed_profit', 'closed_loss']:
            priority = 'HIGH'
        else:
            priority = 'MEDIUM'
        
        return self.send_message(message, priority=priority, msg_type='Trade Update')
    
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
        
        return self.send_medium_priority(message, msg_type='Daily Summary')
    
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
        
        return self.send_critical(message, msg_type=f'Error: {error_type}')
    
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
        
        return self.send_medium_priority(message, msg_type='Bot Startup')
    
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
        
        return self.send_low_priority(message, msg_type='Session Info')

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

    def get_stats(self):
        """Get anti-spam statistics"""
        return {
            'queue_size': len(self.message_queue),
            'sent_messages': len(self.sent_messages),
            'rate_limits': {k: len(v) for k, v in self.rate_limits.items()},
            'last_notifications': self.last_notification
        }

# Create global telegram instance
telegram = TelegramBot()