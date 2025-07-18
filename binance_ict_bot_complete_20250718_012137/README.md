# Binance ICT Trading Bot - Complete Package

## 📋 Informasi Package
- Tanggal dibuat: 2025-07-18 01:21:37
- Versi: Complete with all fixes and enhancements
- Status: Ready for deployment

## 🚀 Cara Deploy

### 1. Upload ke Web Horizon
1. Upload semua file ke server Web Horizon Anda
2. Install dependencies: `pip install -r requirements.txt`
3. Jalankan bot: `python bot.py`

### 2. Deploy di VPS Singapore
1. Upload ke VPS di Singapore
2. Jalankan: `bash vps_setup.sh`
3. Bot akan otomatis terinstall dan berjalan

### 3. Manual Mode (jika API diblokir)
1. Jalankan: `python manual_mode_bot.py`
2. Bot akan detect signal tapi tidak execute trade
3. Anda execute trade manual di Binance

## 📁 File Penting
- `bot.py` - Bot utama
- `manual_mode_bot.py` - Mode manual trading
- `web_horizon_fix.py` - Versi khusus Web Horizon
- `quick_diagnostic.py` - Test koneksi Binance
- `TROUBLESHOOTING.md` - Panduan troubleshooting

## 🔧 Troubleshooting
Jika ada masalah, baca file:
- `TROUBLESHOOTING.md`
- `manual_vpn_setup.md`

## 📞 Support
Bot ini sudah dioptimasi untuk:
- Anti spam dan rate limiting
- Error handling yang robust
- Multi-pair trading
- Telegram integration
- ICT methodology dengan enhancements

Semoga trading Anda sukses! 🎯
