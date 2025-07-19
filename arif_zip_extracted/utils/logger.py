
import logging
from datetime import datetime
import os
import time
from core.config import config

# Buat folder log jika belum ada
os.makedirs("logs", exist_ok=True)

# Setup logger
logger = logging.getLogger("ICTBot")

# Set log level from config
log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
logger.setLevel(log_level)

# Hindari duplikat handler saat re-import
if not logger.handlers:
    # File handler
    log_filename = f'logs/ICTBot_{datetime.now().strftime("%Y%m%d")}.log'
    fh = logging.FileHandler(log_filename)
    ch = logging.StreamHandler()

    # Format log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Pasang handler
    logger.addHandler(fh)
    logger.addHandler(ch)

    # ✅ Telegram handler jika level ERROR
    _last_telegram_error = {}

    def send_telegram_error(message, error_type="general", cooldown=300):
        global _last_telegram_error
        now = time.time()
        if error_type not in _last_telegram_error or now - _last_telegram_error[error_type] > cooldown:
            from integrations.telegram import telegram
            telegram.send_message(message)
            _last_telegram_error[error_type] = now
        # else: hanya log ke file, tidak kirim ke Telegram

    class TelegramLogHandler(logging.Handler):
        def emit(self, record):
            try:
                from integrations.telegram import telegram
                log_entry = self.format(record)
                if record.levelno >= logging.ERROR:
                    # Gunakan anti-spam error
                    send_telegram_error(f"🚨 BOT ERROR\n{log_entry}", error_type=record.levelname, cooldown=300)
            except Exception as e:
                logger.error(f"TelegramLogHandler error: {e}")

    telegram_handler = TelegramLogHandler()
    telegram_handler.setLevel(logging.ERROR)
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)
