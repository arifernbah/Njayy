#!/usr/bin/env python3
"""
Script untuk membantu download bot trading yang sudah siap
dari VPS ini ke komputer lokal user
"""

import os
import shutil
import zipfile
from datetime import datetime

def create_complete_package():
    """Membuat package lengkap bot trading"""
    
    # Nama package
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"binance_ict_bot_complete_{timestamp}"
    
    # Buat direktori package
    if os.path.exists(package_name):
        shutil.rmtree(package_name)
    os.makedirs(package_name)
    
    # Copy file utama
    main_files = [
        "arif_zip_extracted/bot.py",
        "arif_zip_extracted/requirements.txt",
        "arif_zip_extracted/quick_diagnostic.py",
        "arif_zip_extracted/manual_mode_bot.py",
        "arif_zip_extracted/web_horizon_simple.py",
        "arif_zip_extracted/web_horizon_fix.py",
        "arif_zip_extracted/quick_fix.py",
        "arif_zip_extracted/alternative_solution.py",
        "arif_zip_extracted/setup_vpn.py",
        "arif_zip_extracted/test_connection.py",
        "arif_zip_extracted/vps_setup.sh",
        "arif_zip_extracted/manual_vpn_setup.md",
        "arif_zip_extracted/TROUBLESHOOTING.md",
        "arif_zip_extracted/ICT_TECHNICAL_ANALYSIS_ENHANCEMENT.md",
        "arif_zip_extracted/ANTI_SPAM_SYSTEM.md",
        "arif_zip_extracted/SL_ACCURACY_IMPROVEMENTS.md"
    ]
    
    # Copy direktori
    directories = [
        "arif_zip_extracted/core",
        "arif_zip_extracted/utils", 
        "arif_zip_extracted/analysis",
        "arif_zip_extracted/strategies",
        "arif_zip_extracted/execution",
        "arif_zip_extracted/integrations"
    ]
    
    print("📦 Membuat package bot trading...")
    
    # Copy file utama
    for file_path in main_files:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            dest_path = os.path.join(package_name, filename)
            shutil.copy2(file_path, dest_path)
            print(f"✅ Copied: {filename}")
        else:
            print(f"⚠️  File tidak ditemukan: {file_path}")
    
    # Copy direktori
    for dir_path in directories:
        if os.path.exists(dir_path):
            dirname = os.path.basename(dir_path)
            dest_dir = os.path.join(package_name, dirname)
            shutil.copytree(dir_path, dest_dir)
            print(f"✅ Copied directory: {dirname}")
        else:
            print(f"⚠️  Directory tidak ditemukan: {dir_path}")
    
    # Buat file README
    readme_content = f"""# Binance ICT Trading Bot - Complete Package

## 📋 Informasi Package
- Tanggal dibuat: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
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
    print(f"\n📥 Silakan download file: {zip_filename}")
    print("🚀 Upload ke server Anda dan jalankan bot!")

if __name__ == "__main__":
    create_complete_package()