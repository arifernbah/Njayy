# 🤖 ARIF BOT - ICT Strategy Trading Bot

**Version:** 8.1  
**Author:** arifernbah1  
**Last Update:** 2025-07-19

## 📋 Overview

Arif Bot adalah trading bot otomatis yang mengimplementasikan strategi ICT (Inner Circle Trader) dengan integrasi Binance Futures. Bot ini menggunakan websocket real-time untuk data candle dan memiliki sistem risk management yang komprehensif.

## ✨ Features

### 🔄 Real-time Trading
- **Websocket Integration**: Real-time candle data dari Binance
- **Multi-timeframe Analysis**: Support multiple timeframes (1m, 5m, 15m, 1h, 4h)
- **Dynamic TP/SL**: TP/SL dihitung ulang berdasarkan harga entry real

### 🛡️ Risk Management
- **Max Daily Trades**: Limit jumlah trade per hari
- **Max Open Positions**: Limit posisi aktif bersamaan
- **Circuit Breaker**: Auto-stop saat drawdown berlebihan
- **Dynamic Risk**: Risk adjustment berdasarkan performance

### 📊 ICT Strategy
- **Order Blocks**: Deteksi dan validasi order blocks
- **Liquidity Sweeps**: Identifikasi liquidity sweeps
- **Premium/Discount Zones**: Analisis zona premium/discount
- **Institutional Volume**: Deteksi volume institusional
- **Quality Scoring**: Sistem scoring kualitas sinyal

### 📱 Telegram Integration
- **Real-time Notifications**: Notifikasi entry, TP, SL real-time
- **Command Control**: Kontrol bot via Telegram commands
- **Performance Reports**: Laporan performa detail
- **Status Monitoring**: Monitoring status bot

### 🔧 Advanced Features
- **Auto Pair Selection**: Auto pilih pair berdasarkan volume
- **State Persistence**: State tersimpan saat restart
- **Error Recovery**: Auto recovery dari error
- **Daily Reset**: Auto reset counter harian
- **Position Cleanup**: Auto cleanup orphaned positions

## 📁 Project Structure

```
arif_bot/
├── bot.py                    # Main bot dengan websocket
├── core/
│   └── config.py            # Configuration management
├── execution/
│   └── trader.py            # Trading logic dengan dynamic TP/SL
├── strategies/
│   └── ict_core.py          # ICT strategy implementation
├── integrations/
│   └── telegram.py          # Telegram integration
├── utils/
│   └── logger.py            # Logging system
├── analysis/
│   └── bias.py              # Market bias analysis
├── logs/                    # Consolidated logs
│   ├── ICTBot_YYYYMMDD.log
│   ├── equity.log
│   └── valid_signals.log
├── .env.template            # Environment template
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## 🚀 Installation

### 1. Clone/Download
```bash
# Download dan extract bot
unzip arif_bot_final.zip
cd arif_bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration
```bash
# Copy template dan isi credentials
cp .env.template .env
# Edit .env dengan credentials Anda
nano .env
```

### 4. Run Bot
```bash
python bot.py
```

## ⚙️ Configuration

### API Credentials
```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET=your_binance_secret_key_here
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

### Trading Parameters
```env
DEFAULT_INTERVAL=15m          # Timeframe utama
LEVERAGE=5                    # Leverage default
MAX_DAILY_TRADES=6           # Max trade per hari
MAX_OPEN_POSITIONS=2         # Max posisi aktif
MAX_DRAWDOWN=10.0            # Max drawdown (%)
```

### Risk Management
```env
DEFAULT_RISK=1.0             # Risk default per trade (%)
REDUCED_RISK=0.5             # Risk saat drawdown
MINIMUM_RISK=0.25            # Risk minimum
```

### Signal Filters
```env
MIN_SIGNAL_STRENGTH=70       # Minimal signal strength
MIN_BIAS_STRENGTH=35         # Minimal bias strength
MIN_REGIME_SCORE=55          # Minimal regime score
MIN_QUALITY_SCORE=70         # Minimal quality score
```

## 📱 Telegram Commands

### Status & Monitoring
- `/status` - Status bot dengan metrics lengkap
- `/performance` - Laporan performa detail
- `/balance` - Cek saldo USDT
- `/drawdown` - Cek drawdown saat ini
- `/positions` - Lihat posisi aktif
- `/uptime` - Lama bot berjalan

### Management
- `/settings` - Lihat setting utama bot
- `/cleanup` - Bersihkan orphaned positions
- `/pause` - Pause trading
- `/resume` - Lanjutkan trading
- `/shutdown` - Matikan bot

### Reports
- `/summary` - Ringkasan performa harian
- `/help` - Lihat daftar command

## 📊 Performance Metrics

Bot melacak berbagai metrics performa:
- **Win Rate**: Persentase trade yang profit
- **Profit Factor**: Ratio profit vs loss
- **Sharpe Ratio**: Risk-adjusted return
- **Drawdown**: Maximum drawdown
- **Daily PnL**: Profit/Loss harian
- **Consecutive Losses**: Loss streak

## 🛡️ Safety Features

### Circuit Breaker
- Auto-stop saat 5 consecutive losses
- Auto-stop saat drawdown > 10%
- Auto-stop saat balance < 10 USDT
- Auto-stop saat API connection issues

### Error Recovery
- Auto-reconnect websocket
- Cleanup orphaned positions
- State persistence
- Emergency shutdown

## 📝 Logging

Bot menghasilkan 3 jenis log:
- **ICTBot_YYYYMMDD.log**: Log utama bot
- **equity.log**: Tracking equity
- **valid_signals.log**: Log sinyal valid

## ⚠️ Important Notes

1. **Test First**: Selalu test di testnet sebelum live trading
2. **Risk Management**: Pastikan risk management sesuai dengan capital
3. **Monitoring**: Monitor bot secara regular via Telegram
4. **Backup**: Backup file .env dan state.json secara regular
5. **Updates**: Update bot secara regular untuk bug fixes

## 🆘 Troubleshooting

### Common Issues
1. **Websocket Disconnect**: Bot akan auto-reconnect
2. **API Errors**: Bot akan retry dengan exponential backoff
3. **Position Mismatch**: Bot akan cleanup orphaned positions
4. **Memory Issues**: Bot akan cleanup old data secara otomatis

### Support
- Cek logs di folder `logs/`
- Gunakan command `/status` untuk monitoring
- Restart bot jika ada masalah serius

## 📈 Expected Performance

- **Valid Signals**: 5-15 per hari (tergantung market)
- **Win Rate**: 60-70% (dengan proper risk management)
- **Entry Delay**: <1 detik (websocket)
- **Uptime**: 24/7 dengan auto-recovery

## 🔄 Updates

### Version 8.1 (Latest)
- ✅ Enhanced websocket reconnection
- ✅ Dynamic TP/SL calculation
- ✅ Enhanced error recovery
- ✅ Comprehensive monitoring
- ✅ Auto cleanup features
- ✅ Enhanced Telegram commands

## 📄 License

This bot is for educational purposes. Use at your own risk.

---

**Disclaimer**: Trading involves risk. This bot is not financial advice. Always do your own research and trade responsibly.