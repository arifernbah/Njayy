import requests
import time
from core.config import config
from integrations.telegram import telegram

class TelegramCommandListener:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.offset = None
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def poll_commands(self):
        """Polling for Telegram commands"""
        url = f"{self.base_url}/getUpdates"
        if self.offset:
            url += f"?offset={self.offset + 1}"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                telegram.send_message(f"⚠️ Gagal polling Telegram: {response.status_code}")
                return

            data = response.json()

            for update in data.get("result", []):
                self.offset = update["update_id"]
                message = update["message"]["text"]
                self.handle_command(message)

        except Exception as e:
            telegram.send_message(f"🚨 Command polling error: {e}")

    def handle_command(self, message):
        """Handle supported Telegram commands"""
        message = message.strip().lower()

        # Only allow from correct chat_id (optional, uncomment if needed)
        # if str(self.chat_id) != str(config.TELEGRAM_CHAT_ID):
        #     telegram.send_message("⚠️ Unauthorized access.")
        #     return

        if message == "/status":
            telegram.send_message("✅ *Bot status*: Aktif dan berjalan", parse_mode="Markdown")

        elif message == "/balance":
            from execution.trader import EnhancedICTTrader
            trader = EnhancedICTTrader()
            balance = trader.get_account_balance()
            telegram.send_message(f"💰 *Saldo USDT saat ini*: {balance}", parse_mode="Markdown")

        elif message == "/drawdown":
            from execution.trader import EnhancedICTTrader
            trader = EnhancedICTTrader()
            drawdown = trader.get_drawdown()
            telegram.send_message(f"📉 *Drawdown saat ini*: {drawdown:.2f}%", parse_mode="Markdown")

        elif message == "/help":
            telegram.send_message("""
📖 *Daftar Perintah:*
/status - Cek status bot
/balance - Cek saldo USDT
/drawdown - Cek drawdown saat ini
/help - Lihat daftar command

Perintah lanjutan dapat ditambahkan nanti seperti /summary, /pause, dll.
""", parse_mode="Markdown")

        elif message == "/shutdown":
            telegram.send_message("🛑 *Bot akan dimatikan...*", parse_mode="Markdown")
            exit(0)

        else:
            telegram.send_message(f"⚠️ *Perintah tidak dikenali:* {message}", parse_mode="Markdown")


import threading

def start_command_listener(bot=None):
    listener = TelegramCommandListener()

    def run_polling():
        while True:
            listener.poll_commands()
            time.sleep(5)  # polling interval

    thread = threading.Thread(target=run_polling, daemon=True)
    thread.start()
