import requests
import json
from datetime import datetime
from core.config import config
from utils.logger import logger
import time
import threading

def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d

class TelegramBot:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self._polling_active = False
        self._polling_thread = None
        self.message_handler = None
        self.bot_instance = None  # Reference to main bot instance
        
        # Load last update id from file
        try:
            with open('telegram_offset.txt', 'r') as f:
                self._last_update_id = int(f.read().strip())
        except:
            self._last_update_id = None
    
    def set_bot_instance(self, bot_instance):
        """Set reference to main bot instance"""
        self.bot_instance = bot_instance
    
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
    
    def send_message(self, message, parse_mode="Markdown"):
        """Send message to Telegram with retry"""
        for attempt in range(3):
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
                    error_msg = safe_get(response.json(), 'description', 'Unknown error')
                    logger.error(f"Telegram send failed (attempt {attempt+1}): {error_msg}")
            except Exception as e:
                logger.error(f"Telegram send error (attempt {attempt+1}): {e}")
            time.sleep(2)
        logger.error(f"Telegram send failed after 3 attempts: {message}")
        return False

    # ===== UNIFIED TRADING ALERTS =====
    def send_trade_alert(self, signal, bias, risk, position_size):
        """Unified trade alert with ICT quality information"""
        timestamp = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M WIB")
        
        # Quality indicators
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
        
        # ICT summary
        ict_summary = signal.get_ict_summary() if hasattr(signal, 'get_ict_summary') else {}
        
        message = f"""
📢 *ENTRY SIGNAL DETECTED*

{quality_icon} *QUALITY*: {signal.quality_class} ({signal.quality_score}/100)
{zone_icon} *ZONE*: {signal.zone_position}
📌 *PAIR*: {signal.pair}
🕒 *Waktu*: {timestamp}
📊 *Bias*: {safe_get(bias, 'direction', default='N/A')} ({safe_get(bias, 'strength', default=50):.1f})
🧠 *Signal Strength*: {signal.strength}

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

    # ===== UNIFIED STATUS & MONITORING =====
    def send_status(self, status_type="full"):
        """Unified status command - handles all status requests"""
        if not self.bot_instance:
            return self.send_message("❌ Bot instance not available")
        
        try:
            if status_type == "full" or status_type == "status":
                return self._send_full_status()
            elif status_type == "performance":
                return self._send_performance_report()
            elif status_type == "balance":
                return self._send_balance_info()
            elif status_type == "drawdown":
                return self._send_drawdown_info()
            elif status_type == "positions":
                return self._send_positions_info()
            elif status_type == "settings":
                return self._send_settings_info()
            elif status_type == "summary":
                return self._send_summary_info()
            else:
                return self.send_message("❌ Invalid status type")
        except Exception as e:
            logger.error(f"Error sending status: {e}")
            return self.send_message("❌ Error getting status information")

    def _send_full_status(self):
        """Send comprehensive bot status"""
        if not self.bot_instance:
            return False
            
        try:
            trader = self.bot_instance.trader
            perf = trader.get_enhanced_performance()
            
            message = f"""
🤖 *ARIF BOT STATUS*

📊 *PERFORMANCE*:
• Total Trades: {perf.get('total_trades', 0)}
• Win Rate: {perf.get('win_rate', 0):.1f}%
• Daily PnL: ${perf.get('daily_pnl', 0):.2f}
• Current Drawdown: {trader.get_drawdown():.2f}%

💰 *ACCOUNT*:
• Balance: ${trader.get_account_balance():.2f}
• Active Positions: {perf.get('active_positions', 0)}
• Daily Trades: {trader.get_daily_trades()}

⏱ *SYSTEM*:
• Uptime: {self.bot_instance.get_uptime()}
• Status: {'🟢 Running' if not self.bot_instance.paused else '⏸️ Paused'}
• Market Volatility: {perf.get('market_volatility', 0):.2f}%

🎯 *TODAY'S TARGET*:
• Signals: {config.SIGNAL_TARGET_MIN}-{config.SIGNAL_TARGET_MAX}
• Risk per Trade: {safe_get(self.bot_instance.risk_management, 'default_risk', default=config.DEFAULT_RISK/100)*100:.1f}%
            """
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error in full status: {e}")
            return False

    def _send_performance_report(self):
        """Send detailed performance report"""
        if not self.bot_instance:
            return False
            
        try:
            trader = self.bot_instance.trader
            perf = trader.get_enhanced_performance()
            
            message = f"""
📊 *DETAILED PERFORMANCE*

📈 *TRADING STATS*:
• Total Trades: {perf.get('total_trades', 0)}
• Wins: {perf.get('wins', 0)}
• Losses: {perf.get('losses', 0)}
• Win Rate: {perf.get('win_rate', 0):.1f}%
• Profit Factor: {perf.get('profit_factor', 0):.2f}
• Sharpe Ratio: {perf.get('sharpe_ratio', 0):.2f}

💰 *FINANCIAL*:
• Total PnL: ${perf.get('total_pnl', 0):.2f}
• Daily PnL: ${perf.get('daily_pnl', 0):.2f}
• Max Balance: ${perf.get('max_balance', 0):.2f}
• Current Balance: ${trader.get_account_balance():.2f}

📉 *RISK METRICS*:
• Current Drawdown: {trader.get_drawdown():.2f}%
• Max Drawdown: {trader.get_max_drawdown():.2f}%
• Consecutive Losses: {trader.get_consecutive_losses()}
• Market Volatility: {perf.get('market_volatility', 0):.2f}%

🔄 *ACTIVE*:
• Open Positions: {perf.get('active_positions', 0)}
• Daily Trades: {trader.get_daily_trades()}
            """
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error in performance report: {e}")
            return False

    def _send_balance_info(self):
        """Send balance information"""
        if not self.bot_instance:
            return False
            
        try:
            balance = self.bot_instance.trader.get_account_balance()
            message = f"💰 *ACCOUNT BALANCE*\n\nCurrent USDT: ${balance:.2f}"
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return False

    def _send_drawdown_info(self):
        """Send drawdown information"""
        if not self.bot_instance:
            return False
            
        try:
            trader = self.bot_instance.trader
            current_dd = trader.get_drawdown()
            max_dd = trader.get_max_drawdown()
            
            message = f"""
📉 *DRAWDOWN ANALYSIS*

Current Drawdown: {current_dd:.2f}%
Max Drawdown: {max_dd:.2f}%
Limit: {config.MAX_DRAWDOWN}%

Status: {'🟢 Safe' if current_dd < config.MAX_DRAWDOWN else '🔴 Warning'}
            """
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error getting drawdown: {e}")
            return False

    def _send_positions_info(self):
        """Send active positions information"""
        if not self.bot_instance:
            return False
            
        try:
            active_positions = self.bot_instance.trader.active_positions
            
            if not active_positions:
                return self.send_message("📊 *ACTIVE POSITIONS*\n\nNo active positions")
            
            message = "📊 *ACTIVE POSITIONS*\n\n"
            
            for pos_id, pos in active_positions.items():
                try:
                    pnl = self.bot_instance.trader._calculate_position_pnl(pos)
                    opened_time = (pos.get('opened_at', datetime.utcnow()) + timedelta(hours=7)).strftime('%H:%M WIB')
                    
                    message += f"""
🎯 *{pos['symbol']} {pos['direction']}*
💰 Entry: ${pos['entry']:.2f}
🛑 SL: ${pos['sl']:.2f}
📊 Size: {pos['size']}
📈 PnL: ${pnl:.2f}
⏰ Opened: {opened_time}
                    """
                except Exception as e:
                    logger.error(f"Error processing position {pos_id}: {e}")
                    continue
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return False

    def _send_settings_info(self):
        """Send bot settings information"""
        if not self.bot_instance:
            return False
            
        try:
            settings = self.bot_instance.get_settings()
            return self.send_message(settings)
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return False

    def _send_summary_info(self):
        """Send summary information"""
        if not self.bot_instance:
            return False
            
        try:
            summary = self.bot_instance.get_summary()
            return self.send_message(summary)
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return False

    # ===== UNIFIED MANAGEMENT COMMANDS =====
    def send_management_command(self, command_type):
        """Unified management command handler"""
        if not self.bot_instance:
            return self.send_message("❌ Bot instance not available")
        
        try:
            if command_type == "cleanup":
                return self._handle_cleanup()
            elif command_type == "pause":
                return self._handle_pause()
            elif command_type == "resume":
                return self._handle_resume()
            elif command_type == "shutdown":
                return self._handle_shutdown()
            else:
                return self.send_message("❌ Invalid management command")
        except Exception as e:
            logger.error(f"Error in management command: {e}")
            return self.send_message("❌ Error executing management command")

    def _handle_cleanup(self):
        """Handle cleanup command"""
        try:
            cleaned = self.bot_instance.trader.cleanup_orphaned_positions()
            message = f"🧹 *CLEANUP COMPLETED*\n\nOrphaned positions cleaned: {cleaned}"
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
            return self.send_message("❌ Error during cleanup")

    def _handle_pause(self):
        """Handle pause command"""
        try:
            self.bot_instance.paused = True
            return self.send_message("⏸️ *TRADING PAUSED*\n\nBot will not enter new positions until resumed.")
        except Exception as e:
            logger.error(f"Error pausing: {e}")
            return self.send_message("❌ Error pausing bot")

    def _handle_resume(self):
        """Handle resume command"""
        try:
            self.bot_instance.paused = False
            return self.send_message("▶️ *TRADING RESUMED*\n\nBot is now active and will enter positions normally.")
        except Exception as e:
            logger.error(f"Error resuming: {e}")
            return self.send_message("❌ Error resuming bot")

    def _handle_shutdown(self):
        """Handle shutdown command"""
        try:
            self.send_message("🛑 *SHUTDOWN INITIATED*\n\nBot will shut down safely...")
            self.bot_instance.trader.shutdown()
            return True
        except Exception as e:
            logger.error(f"Error shutting down: {e}")
            return self.send_message("❌ Error shutting down bot")

    # ===== HELPER FUNCTIONS =====
    def send_startup_message(self, bot_version, author):
        """Send startup message"""
        try:
            from datetime import timedelta
            utc_now = datetime.utcnow()
            wib_now = utc_now + timedelta(hours=7)
            
            message = f"""
👋 *ARIF BOT STARTED*

🕒 Waktu: {wib_now.strftime('%Y-%m-%d %H:%M:%S')} WIB
🤖 Version: {bot_version}
👨‍💻 Author: {author}

Status: 🟢 Ready for trading!
            """
            
            self.send_message(message)
            self.send_main_menu()
        except Exception as e:
            logger.error(f"Error sending startup message: {e}")

    def send_error_alert(self, error_msg, error_type="General"):
        """Send error alert"""
        try:
            timestamp = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M WIB")
            message = f"""
🚨 *ERROR ALERT*

Type: {error_type}
Waktu: {timestamp}
Error: {error_msg}

Status: Bot continues running
            """
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending error alert: {e}")

    def send_main_menu(self):
        """Send main menu with inline keyboard"""
        try:
            message = """
🤖 *ARIF BOT - MAIN MENU*

Choose an option:
            """
            
            # Create inline keyboard
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📊 Status", "callback_data": "status"},
                        {"text": "💰 Balance", "callback_data": "balance"}
                    ],
                    [
                        {"text": "📈 Performance", "callback_data": "performance"},
                        {"text": "📉 Drawdown", "callback_data": "drawdown"}
                    ],
                    [
                        {"text": "📋 Positions", "callback_data": "positions"},
                        {"text": "⚙️ Settings", "callback_data": "settings"}
                    ],
                    [
                        {"text": "🧹 Cleanup", "callback_data": "cleanup"},
                        {"text": "⏸️ Pause", "callback_data": "pause"}
                    ],
                    [
                        {"text": "▶️ Resume", "callback_data": "resume"},
                        {"text": "🛑 Shutdown", "callback_data": "shutdown"}
                    ]
                ]
            }
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': json.dumps(keyboard)
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Main menu sent successfully")
                return True
            else:
                logger.error(f"Failed to send main menu: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending main menu: {e}")
            return False

    # ===== POLLING & MESSAGE HANDLING =====
    def poll_messages(self, timeout=30):
        """Poll for new messages"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                'timeout': timeout,
                'offset': self._last_update_id + 1 if self._last_update_id else None
            }
            
            response = requests.get(url, params=params, timeout=timeout + 5)
            if response.status_code == 200:
                updates = response.json().get('result', [])
                for update in updates:
                    self._last_update_id = update['update_id']
                    if 'message' in update:
                        self._handle_message(update['message'])
                    elif 'callback_query' in update:
                        self._handle_callback_query(update['callback_query'])
                
                # Save last update id
                with open('telegram_offset.txt', 'w') as f:
                    f.write(str(self._last_update_id))
                    
        except Exception as e:
            logger.error(f"Error polling messages: {e}")

    def _handle_message(self, message):
        """Handle incoming message"""
        try:
            text = message.get('text', '').strip()
            chat_id = message.get('chat', {}).get('id')
            
            # Check authorization
            if str(chat_id) != str(config.TELEGRAM_CHAT_ID):
                self.send_message("⚠️ Unauthorized access.")
                return
            
            # Process command
            self._process_command(text.lower())
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _handle_callback_query(self, callback_query):
        """Handle callback query from inline keyboard"""
        try:
            data = callback_query.get('data', '')
            chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
            
            # Check authorization
            if str(chat_id) != str(config.TELEGRAM_CHAT_ID):
                self.send_message("⚠️ Unauthorized access.")
                return
            
            # Process callback
            self._process_command(data)
            
            # Answer callback query
            url = f"{self.base_url}/answerCallbackQuery"
            payload = {'callback_query_id': callback_query['id']}
            requests.post(url, json=payload)
            
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")

    def _process_command(self, command):
        """Process unified command system"""
        try:
            # Status commands
            if command in ['/status', 'status']:
                self.send_status("full")
            elif command in ['/performance', 'performance']:
                self.send_status("performance")
            elif command in ['/balance', 'balance']:
                self.send_status("balance")
            elif command in ['/drawdown', 'drawdown']:
                self.send_status("drawdown")
            elif command in ['/positions', 'positions']:
                self.send_status("positions")
            elif command in ['/settings', 'settings']:
                self.send_status("settings")
            elif command in ['/summary', 'summary']:
                self.send_status("summary")
            
            # Management commands
            elif command in ['/cleanup', 'cleanup']:
                self.send_management_command("cleanup")
            elif command in ['/pause', 'pause']:
                self.send_management_command("pause")
            elif command in ['/resume', 'resume']:
                self.send_management_command("resume")
            elif command in ['/shutdown', 'shutdown']:
                self.send_management_command("shutdown")
            
            # Help commands
            elif command in ['/start', '/help', 'help']:
                self._send_help_message()
            elif command in ['/uptime', 'uptime']:
                if self.bot_instance:
                    self.send_message(f"⏱ Uptime: {self.bot_instance.get_uptime()}")
                else:
                    self.send_message("❌ Bot instance not available")
            
            # Unknown command
            else:
                self.send_message(f"⚠️ Unknown command: {command}\nUse /help for available commands.")
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.send_message("❌ Error processing command")

    def _send_help_message(self):
        """Send help message"""
        message = """
📖 *ARIF BOT COMMANDS*

🔍 *STATUS & MONITORING:*
/status - Full bot status
/performance - Detailed performance report
/balance - Account balance
/drawdown - Drawdown analysis
/positions - Active positions
/settings - Bot settings
/summary - Performance summary

⚙️ *MANAGEMENT:*
/cleanup - Clean orphaned positions
/pause - Pause trading
/resume - Resume trading
/shutdown - Shutdown bot

📊 *INFO:*
/uptime - Bot uptime
/help - This help message

💡 *Tips:* Use the inline menu for quick access!
        """
        
        self.send_message(message)
        self.send_main_menu()

    def start_polling(self, handler=None, interval=2):
        """Start polling for messages"""
        if self._polling_active:
            return
        
        self._polling_active = True
        self._polling_thread = threading.Thread(target=self._polling_loop, args=(interval,))
        self._polling_thread.daemon = True
        self._polling_thread.start()
        logger.info("Telegram polling started")

    def stop_polling(self):
        """Stop polling for messages"""
        self._polling_active = False
        if self._polling_thread:
            self._polling_thread.join()
        logger.info("Telegram polling stopped")

    def _polling_loop(self, interval):
        """Polling loop"""
        while self._polling_active:
            try:
                self.poll_messages(timeout=interval)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(interval)

# Global instance
telegram = TelegramBot()