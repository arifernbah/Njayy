# 🚀 INSTALLATION GUIDE - ARIF BOT FINAL WIB

## 📋 **Prerequisites**

### **System Requirements**
- **Python 3.8 or higher**
- **Internet connection** for real-time trading
- **Binance Futures account** with API access
- **Telegram Bot Token** (from @BotFather)

### **Required Accounts**
1. **Binance Futures Account**
   - Create account at [binance.com](https://binance.com)
   - Enable Futures trading
   - Generate API key and secret

2. **Telegram Bot**
   - Message @BotFather on Telegram
   - Create new bot with `/newbot`
   - Get bot token

## 🔧 **Installation Steps**

### **Step 1: Download & Extract**
```bash
# Download the zip file
# Extract to your preferred directory
unzip arif_bot_final_wib.zip
cd arif_bot_final_wib
```

### **Step 2: Install Dependencies**
```bash
# Install Python dependencies
pip install -r requirements.txt
```

### **Step 3: Configure Environment**
```bash
# Copy example environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env
```

### **Step 4: Configure .env File**
```env
# Binance API Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Trading Configuration
DEFAULT_RISK=1.0
LEVERAGE=5
MAX_DRAWDOWN=10.0

# Signal Filters
MIN_QUALITY_SCORE=70
MIN_SIGNAL_STRENGTH=70
MIN_BIAS_STRENGTH=35
MIN_REGIME_SCORE=55

# Session Times (WIB)
LONDON_START=07:00
LONDON_END=16:00
NY_START=14:00
NY_END=23:00
ASIA_START=00:00
ASIA_END=09:00

# Trading Pairs
TRADING_PAIRS=BTCUSDT,ETHUSDT,ADAUSDT,BNBUSDT,SOLUSDT,XRPUSDT
```

### **Step 5: Get Telegram Chat ID**
```bash
# Start the bot temporarily to get your chat ID
python bot.py

# Send a message to your bot
# Check the console output for your chat ID
# Update .env file with the correct chat ID
```

### **Step 6: Test Configuration**
```bash
# Test the bot configuration
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('✅ Environment loaded successfully')
print(f'API Key: {os.getenv(\"BINANCE_API_KEY\")[:10]}...')
print(f'Bot Token: {os.getenv(\"TELEGRAM_BOT_TOKEN\")[:10]}...')
"
```

## 🚀 **Running the Bot**

### **Start the Bot**
```bash
# Start the main bot
python bot.py
```

### **Verify Startup**
1. **Check console output** for successful startup
2. **Check Telegram** for startup message
3. **Verify connection** to Binance and Telegram

### **Expected Telegram Message**
```
👋 ARIF BOT STARTED

🕒 Waktu: 2024-01-15 08:00:00 WIB
🤖 Version: 2.1.0
👨‍💻 Author: Arif

Status: 🟢 Ready for trading!
```

## 📱 **Telegram Bot Usage**

### **Main Menu Commands**
- **📊 Status** - Full bot status
- **💰 Balance** - Account balance
- **📈 Performance** - Detailed performance
- **📋 Positions** - Active positions
- **⚙️ Settings** - Bot configuration
- **⏸️ Pause** - Pause trading
- **▶️ Resume** - Resume trading
- **🛑 Shutdown** - Safe shutdown

### **Text Commands**
- `/status` - Full bot status
- `/performance` - Performance report
- `/balance` - Account balance
- `/positions` - Active positions
- `/settings` - Bot settings
- `/pause` - Pause trading
- `/resume` - Resume trading
- `/shutdown` - Shutdown bot
- `/help` - Show help message

## 🔍 **Monitoring & Alerts**

### **Real-time Alerts**
- **Signal Detection** - Quality signals with WIB time
- **Entry Execution** - Real entry prices and details
- **TP1/TP2 Execution** - Profit taking notifications
- **Stop Loss** - Loss protection alerts
- **Error Alerts** - System error notifications

### **Status Monitoring**
- **Account Balance** - Real-time balance updates
- **Performance Metrics** - Win rate, PnL, drawdown
- **Active Positions** - Current open trades
- **System Status** - Bot health and uptime

## ⚙️ **Configuration Options**

### **Risk Management**
```env
# Risk per trade (0.1% - 5%)
DEFAULT_RISK=1.0

# Maximum drawdown before circuit breaker
MAX_DRAWDOWN=10.0

# Leverage for futures trading
LEVERAGE=5
```

### **Signal Filters**
```env
# Minimum quality score (0-100)
MIN_QUALITY_SCORE=70

# Minimum signal strength (0-10)
MIN_SIGNAL_STRENGTH=70

# Minimum bias strength (0-10)
MIN_BIAS_STRENGTH=35

# Minimum regime score (0-10)
MIN_REGIME_SCORE=55
```

### **Trading Sessions (WIB Time)**
```env
# London Session
LONDON_START=07:00
LONDON_END=16:00

# New York Session
NY_START=14:00
NY_END=23:00

# Asia Session
ASIA_START=00:00
ASIA_END=09:00
```

## 🔒 **Safety Features**

### **Circuit Breaker**
- **Automatic pause** when drawdown exceeds limit
- **Telegram alert** for circuit breaker activation
- **Manual resume** required after circuit breaker

### **Error Handling**
- **Automatic retry** for API failures
- **Graceful degradation** for network issues
- **Detailed logging** for troubleshooting

### **Position Management**
- **Real-time monitoring** of all positions
- **Automatic cleanup** of orphaned positions
- **Margin validation** before trade execution

## 📊 **Performance Tracking**

### **Metrics Available**
- **Win Rate** - Percentage of profitable trades
- **Total PnL** - Overall profit/loss
- **Daily PnL** - Daily profit/loss
- **Drawdown** - Current and maximum drawdown
- **Sharpe Ratio** - Risk-adjusted returns
- **Profit Factor** - Win/loss ratio

### **Reporting**
- **Real-time updates** via Telegram
- **Daily summaries** with performance metrics
- **Detailed logs** for analysis
- **Export capabilities** for external analysis

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **Connection Errors**
```bash
# Check internet connection
ping binance.com

# Verify API keys
python -c "from binance.client import Client; print('API test')"
```

#### **Telegram Issues**
```bash
# Verify bot token
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# Check chat ID
# Send message to bot and check console output
```

#### **Configuration Issues**
```bash
# Validate .env file
python -c "from dotenv import load_dotenv; load_dotenv(); print('Config OK')"
```

### **Log Files**
- **Main logs** - `logs/` directory
- **Signal logs** - `logs/valid_signals.log`
- **Rejected signals** - `logs/rejected_signals.log`
- **Error logs** - Console output

## 📞 **Support**

### **Documentation**
- **README.md** - Main documentation
- **CHANGELOG.md** - Version history
- **INSTALLATION.md** - This guide

### **Testing**
- **Test scripts** included for verification
- **Configuration validation** on startup
- **Health checks** during operation

### **Updates**
- **Regular updates** for improvements
- **Bug fixes** and security patches
- **Feature enhancements** based on feedback

---

## 🎯 **Quick Start Checklist**

- [ ] **Downloaded** and extracted zip file
- [ ] **Installed** Python dependencies
- [ ] **Configured** .env file with API keys
- [ ] **Set up** Telegram bot and got chat ID
- [ ] **Tested** configuration
- [ ] **Started** bot successfully
- [ ] **Received** Telegram startup message
- [ ] **Verified** all commands work

---

**🎉 Congratulations! Your Arif Bot Final WIB is ready for trading! 🇮🇩**

**⏰ All times displayed in WIB for optimal Indonesian user experience!**