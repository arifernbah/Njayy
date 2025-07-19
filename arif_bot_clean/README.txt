ARIF BOT - Trading Bot

Quick Start:
1. Install dependencies: pip install -r requirements.txt
2. Set up .env file with your API keys
3. Run: python3 bot.py

Features:
- ICT-based trading signals
- Telegram integration with inline keyboard
- Risk management with circuit breaker
- Position monitoring and cleanup
- Real-time market data via WebSocket

Structure:
- bot.py: Main bot class
- core/config.py: Configuration
- execution/trader.py: Trading logic
- integrations/telegram.py: Telegram interface
- utils/logger.py: Logging utilities