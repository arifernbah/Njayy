#!/usr/bin/env python3
"""
Auto Upload Script untuk BashUpload.com
Upload file arif_bot_final_clean.zip secara otomatis
"""

import requests
import os
import sys
from pathlib import Path

def upload_to_bashupload(file_path):
    """Upload file ke bashupload.com"""
    try:
        # URL bashupload
        url = "https://bashupload.com/"
        
        # Cek file exists
        if not os.path.exists(file_path):
            print(f"❌ File tidak ditemukan: {file_path}")
            return None
        
        # File size
        file_size = os.path.getsize(file_path)
        print(f"📁 File: {file_path}")
        print(f"📊 Size: {file_size} bytes")
        
        # Upload file
        print("🔄 Uploading ke bashupload.com...")
        
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/zip')}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            # Extract download link dari response
            content = response.text
            
            # Cari link download (biasanya dalam format tertentu)
            if 'https://' in content:
                # Extract URL dari response
                lines = content.split('\n')
                for line in lines:
                    if 'https://' in line and 'bashupload.com' in line:
                        download_link = line.strip()
                        print(f"✅ Upload berhasil!")
                        print(f"🔗 Download Link: {download_link}")
                        return download_link
            
            print("⚠️ Upload berhasil tapi link tidak ditemukan dalam response")
            print("📄 Response content:")
            print(content)
            return None
            
        else:
            print(f"❌ Upload gagal. Status code: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error saat upload: {e}")
        return None

def main():
    """Main function"""
    print("🚀 Arif Bot - Auto Upload to BashUpload.com")
    print("=" * 50)
    
    # File path
    file_path = "arif_bot_final_clean.zip"
    
    # Cek apakah file ada di current directory
    if not os.path.exists(file_path):
        # Coba cari di workspace
        workspace_path = "/workspace/arif_bot_final_clean.zip"
        if os.path.exists(workspace_path):
            file_path = workspace_path
        else:
            print("❌ File arif_bot_final_clean.zip tidak ditemukan!")
            print("📁 Cari di:")
            print(f"   - Current directory: {os.getcwd()}")
            print(f"   - Workspace: {workspace_path}")
            return
    
    # Upload file
    download_link = upload_to_bashupload(file_path)
    
    if download_link:
        print("\n🎉 Upload berhasil!")
        print(f"🔗 Link Download: {download_link}")
        print("\n📋 Copy link di atas untuk share dengan pengguna")
    else:
        print("\n❌ Upload gagal. Coba lagi atau gunakan cara manual.")

if __name__ == "__main__":
    main()