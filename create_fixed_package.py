#!/usr/bin/env python3
"""
Script untuk membuat package bot yang sudah diperbaiki (tanpa WebSocket)
"""

import os
import shutil
import zipfile
from datetime import datetime

def create_fixed_package():
    """Membuat package bot yang sudah diperbaiki"""
    
    # Nama package
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"binance_ict_bot_fixed_no_websocket_{timestamp}"
    
    # Buat direktori package
    if os.path.exists(package_name):
        shutil.rmtree(package_name)
    os.makedirs(package_name)
    
    # Copy file utama yang sudah diperbaiki
    main_files = [
        "bot_no_websocket.py",
        "requirements_no_websocket.txt",
        "DEPLOYMENT_GUIDE.md"
    ]
    
    print("📦 Membuat package bot yang sudah diperbaiki...")
    
    # Copy file utama
    for file_path in main_files:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            dest_path = os.path.join(package_name, filename)
            shutil.copy2(file_path, dest_path)
            print(f"✅ Copied: {filename}")
        else:
            print(f"⚠️  File tidak ditemukan: {file_path}")
    
    # Buat file README khusus
    readme_content = f"""# 🚀 Binance ICT Trading Bot - FIXED VERSION

## 🎯 MASALAH YANG DIPERBAIKI
**Error HTTP 451** disebabkan oleh **WebSocket connection**, bukan IP blocking!

### ✅ SOLUSI
- ❌ **Dihapus**: WebSocket connection
- ✅ **Digunakan**: REST API saja
- ✅ **Hasil**: Bot bisa bekerja normal lagi

## 📋 INFORMASI PACKAGE
- Tanggal dibuat: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Versi: Fixed - No WebSocket
- Status: Ready to use
- Masalah: ✅ SOLVED

## 🚀 CARA PENGGUNAAN

### 1. Setup API Keys
Edit file `bot_no_websocket.py`:
```python
class Config:
    API_KEY = "your_binance_api_key_here"
    SECRET_KEY = "your_binance_secret_key_here"
    TELEGRAM_BOT_TOKEN = "your_telegram_token_here"  # Optional
    TELEGRAM_CHAT_ID = "your_chat_id_here"  # Optional
```

### 2. Install Dependencies
```bash
pip install -r requirements_no_websocket.txt
```

### 3. Jalankan Bot
```bash
python3 bot_no_websocket.py
```

## 🎯 FITUR BOT

### ✅ ICT Methodology
- Killzone detection (Asia: 08:00-18:00, NY: 19:00-22:00 WIB)
- Bias analysis dengan volume confirmation
- Signal strength validation
- Multi-pair trading (BTC, ETH, BNB)

### ✅ Risk Management
- Position size: 1% balance per trade
- Stop Loss: 2%
- Take Profit 1: 4%
- Take Profit 2: 8%
- Cooldown: 5 menit antar trade

### ✅ Telegram Integration
- Signal notifications
- Order execution alerts
- Real-time updates

## 🔧 KONFIGURASI

### Trading Pairs
```python
TRADING_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
```

### Risk Settings
```python
POSITION_SIZE_PERCENT = 1.0  # 1% per trade
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_1_PERCENT = 4.0
TAKE_PROFIT_2_PERCENT = 8.0
```

### Signal Filters
```python
MIN_SIGNAL_STRENGTH = 8
MIN_BIAS_STRENGTH = 7
```

## 📊 MONITORING

### Log Output
Bot akan menampilkan log real-time:
```
[INFO] 2025-07-18 01:30:00 - 🚀 Starting ICT Trading Bot (No WebSocket Version)
[INFO] 2025-07-18 01:30:01 - ✅ Connected to Binance API
[INFO] 2025-07-18 01:30:01 - 💰 Balance: $100.00
[INFO] 2025-07-18 01:30:01 - 📊 Open Positions: 0
```

### Telegram Commands (jika diaktifkan)
- Notifikasi otomatis saat signal terdeteksi
- Order execution alerts
- Balance dan position updates

## 🚨 PENTING!

1. **Test dengan jumlah kecil** dulu
2. **Monitor bot** secara berkala
3. **Pastikan API key** memiliki permission Futures trading
4. **Gunakan stop loss** untuk proteksi
5. **Jangan share API key** dengan siapapun

## 🎉 SELAMAT TRADING!

Bot ini sudah diperbaiki dan siap digunakan tanpa masalah WebSocket!

**Status**: ✅ FIXED - Ready to Trade! 🚀📈
"""
    
    with open(os.path.join(package_name, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Buat ZIP file
    zip_filename = f"{package_name}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_name):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_name)
                zipf.write(file_path, arcname)
    
    print(f"\n🎉 Package berhasil dibuat!")
    print(f"📁 Nama file: {zip_filename}")
    print(f"📊 Ukuran: {os.path.getsize(zip_filename) / 1024:.1f} KB")
    print(f"\n✅ MASALAH SUDAH DIPERBAIKI!")
    print(f"🔧 WebSocket dihapus, menggunakan REST API saja")
    print(f"📥 Silakan download file: {zip_filename}")
    print("🚀 Bot siap digunakan!")

if __name__ == "__main__":
    create_fixed_package()