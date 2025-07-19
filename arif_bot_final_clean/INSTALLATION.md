# 🚀 ARIF BOT - ICT STRATEGY INSTALLATION GUIDE

## 📋 PREREQUISITES

- Python 3.8 or higher
- Binance API credentials
- Telegram Bot Token (optional)

## 🔧 INSTALLATION STEPS

### 1. Extract Files
```bash
unzip arif_bot_final_clean.zip
cd arif_bot_final_clean
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy template
cp .env.template .env

# Edit configuration
nano .env
```

### 4. Fill in Your Credentials
```env
# API Credentials
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET=your_binance_secret_key_here

# Telegram (optional)
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

### 5. Adjust Trading Parameters
```env
# Quality Thresholds
MIN_QUALITY_SCORE=70        # Minimal quality score (0-100)
MIN_SIGNAL_STRENGTH=70      # Minimal signal strength (0-100)
MIN_BIAS_STRENGTH=35        # Minimal bias strength (0-100)
MIN_REGIME_SCORE=55         # Minimal regime score (0-100)

# Risk Management
DEFAULT_RISK=1.0            # Default risk per trade (%)
REDUCED_RISK=0.5            # Reduced risk saat drawdown (%)
MINIMUM_RISK=0.25           # Minimum risk (%)

# Volatility Range
VOL_RANGE_MIN=0.4           # Minimal volatility
VOL_RANGE_MAX=1.8           # Maximal volatility

# Trading Limits
MAX_DAILY_TRADES=6          # Max trade per hari
MAX_OPEN_POSITIONS=2        # Max posisi aktif
MAX_CONCURRENT_TRADES=2     # Max posisi bersamaan
```

### 6. Start the Bot
```bash
python bot.py
```

## ⚙️ CONFIGURATION EXAMPLES

### Conservative Settings
```env
MIN_QUALITY_SCORE=80
MIN_SIGNAL_STRENGTH=80
DEFAULT_RISK=0.5
MAX_DAILY_TRADES=3
```

### Aggressive Settings
```env
MIN_QUALITY_SCORE=60
MIN_SIGNAL_STRENGTH=60
DEFAULT_RISK=2.0
MAX_DAILY_TRADES=10
```

### Premium Settings
```env
MIN_QUALITY_SCORE=85
MIN_SIGNAL_STRENGTH=85
VOL_RANGE_MIN=0.6
VOL_RANGE_MAX=1.5
```

## 🔍 VERIFICATION

Run verification test to ensure everything is configured correctly:
```bash
python test_final_verification.py
```

## 📱 TELEGRAM COMMANDS

Once bot is running, use these Telegram commands:
- `/start` - Start bot
- `/status` - Check bot status
- `/settings` - View current settings
- `/summary` - View performance summary
- `/stop` - Stop bot

## ⚠️ IMPORTANT NOTES

1. **Risk Warning**: Trading involves risk. Start with small amounts
2. **API Permissions**: Ensure Binance API has futures trading permissions
3. **Test First**: Test on testnet before using real funds
4. **Monitor**: Always monitor bot performance
5. **Backup**: Keep backup of your .env file

## 🆘 TROUBLESHOOTING

### Common Issues:
1. **Import Error**: Install missing dependencies
2. **API Error**: Check API credentials and permissions
3. **Telegram Error**: Verify bot token and chat ID
4. **Config Error**: Check .env file format

### Support:
- Check logs in console output
- Verify all environment variables are set
- Ensure Python version is 3.8+

## 📊 FEATURES

✅ **Real-time WebSocket Trading**
✅ **ICT Strategy Implementation**
✅ **Quality Score Validation**
✅ **Risk Management System**
✅ **Multi-pair Trading**
✅ **Session-based Trading**
✅ **Telegram Integration**
✅ **Price Deviation Validation**
✅ **Comprehensive Logging**

## 🎯 SUCCESS METRICS

- **Quality Score**: ≥ 70 (configurable)
- **Signal Strength**: ≥ 70 (configurable)
- **Win Rate Target**: 60%+
- **Max Daily Trades**: 6 (configurable)
- **Risk per Trade**: 1.0% (configurable)

---

**Happy Trading! 🚀**