#!/bin/bash
# VPS Setup Script for ICT Bot
# Run this on your VPS (Singapore/Hong Kong)

echo "🚀 VPS Setup for ICT Bot"
echo "=========================="

# Update system
echo "📦 Updating system..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and dependencies
echo "🐍 Installing Python..."
sudo apt-get install -y python3 python3-pip python3-venv git curl

# Create bot user
echo "👤 Creating bot user..."
sudo useradd -m -s /bin/bash botuser
sudo usermod -aG sudo botuser

# Switch to bot user
echo "🔄 Switching to bot user..."
sudo su - botuser << 'EOF'

# Create bot directory
mkdir -p ~/ict_bot
cd ~/ict_bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install python-binance python-telegram-bot requests python-dotenv

# Create .env template
cat > .env.template << 'ENVEOF'
# Binance API (REAL TRADING)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here

# Telegram Bot
TELEGRAM_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Settings
TRADING_PAIRS=BTCUSDT,ETHUSDT,ADAUSDT,BNBUSDT,SOLUSDT,XRPUSDT
MAX_DAILY_TRADES=7
DEFAULT_RISK=1.0
MAX_DRAWDOWN=10.0

# Bot Settings
ENABLE_TELEGRAM=True
LOOP_INTERVAL=60
ENVEOF

echo "✅ Environment template created"
echo "📝 Please edit .env file with your API keys"

# Create systemd service
sudo tee /etc/systemd/system/ict-bot.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=ICT Trading Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/ict_bot
Environment=PATH=/home/botuser/ict_bot/venv/bin
ExecStart=/home/botuser/ict_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ict-bot

echo "✅ Systemd service created"
echo "📋 Next steps:"
echo "1. Upload your bot files to /home/botuser/ict_bot/"
echo "2. Edit .env file with your API keys"
echo "3. Start bot: sudo systemctl start ict-bot"
echo "4. Check status: sudo systemctl status ict-bot"
echo "5. View logs: sudo journalctl -u ict-bot -f"

EOF

echo "🎉 VPS setup completed!"
echo ""
echo "📱 To monitor from your phone:"
echo "- Use Telegram commands: /status, /balance, /test"
echo "- Bot will send notifications to your phone"
echo "- No need for VPN on your phone"
echo ""
echo "🔧 To manage bot:"
echo "- Start: sudo systemctl start ict-bot"
echo "- Stop: sudo systemctl stop ict-bot"
echo "- Restart: sudo systemctl restart ict-bot"
echo "- Logs: sudo journalctl -u ict-bot -f"