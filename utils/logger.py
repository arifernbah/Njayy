
import logging
from datetime import datetime
import os

# Buat folder log jika belum ada
os.makedirs("logs", exist_ok=True)

# Setup logger
logger = logging.getLogger("ICTBot")
logger.setLevel(logging.INFO)

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
    class TelegramLogHandler(logging.Handler):
        def emit(self, record):
            try:
                from integrations.telegram import telegram
                log_entry = self.format(record)
                if record.levelno >= logging.ERROR:
                    telegram.send_message(f"🚨 *BOT ERROR*\n{log_entry}")
            except:
                pass

    telegram_handler = TelegramLogHandler()
    telegram_handler.setLevel(logging.ERROR)
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)
