# Google Drive Downloader

Script untuk mengunduh file dari Google Drive menggunakan file ID atau URL sharing.

## Cara Menggunakan

### 1. Menggunakan Script Python
```bash
python3 gdrive_downloader.py <file_id> [output_filename]
```

### 2. Menggunakan Script Bash
```bash
./download_gdrive.sh <file_id> [output_filename]
```

## Contoh Penggunaan

### Dari File ID
```bash
# Menggunakan Python script
python3 gdrive_downloader.py 1ABC123DEF456 output.zip

# Menggunakan Bash script
./download_gdrive.sh 1ABC123DEF456 output.zip
```

### Dari URL Google Drive
```bash
# URL format: https://drive.google.com/file/d/FILE_ID/view
python3 gdrive_downloader.py "https://drive.google.com/file/d/1ABC123DEF456/view" output.zip

# URL format: https://drive.google.com/open?id=FILE_ID
python3 gdrive_downloader.py "https://drive.google.com/open?id=1ABC123DEF456" output.zip
```

## Cara Mendapatkan File ID

1. **Dari URL Sharing Google Drive:**
   - Buka file di Google Drive
   - Klik "Share" (Bagikan)
   - Klik "Copy link" (Salin tautan)
   - URL akan terlihat seperti: `https://drive.google.com/file/d/FILE_ID/view`
   - `FILE_ID` adalah bagian yang Anda butuhkan

2. **Dari URL yang sudah ada:**
   - Jika URL: `https://drive.google.com/file/d/1ABC123DEF456/view`
   - File ID: `1ABC123DEF456`

## Penting!

**Pastikan file di Google Drive sudah diatur ke "Anyone with the link can view" (Siapa pun dengan tautan dapat melihat)**

Jika tidak, download akan gagal dengan error "Access Denied".

## Troubleshooting

### Error "Access Denied"
- Pastikan file sudah di-share dengan permission "Anyone with the link can view"
- Coba buka URL di browser untuk memastikan file bisa diakses

### Error "File not found"
- Periksa kembali File ID
- Pastikan file masih ada di Google Drive

### Download lambat atau terputus
- Gunakan koneksi internet yang stabil
- Untuk file besar, script akan mencoba melanjutkan download

## Dependencies

- **Python script:** Hanya menggunakan library standar Python
- **Bash script:** Memerlukan `wget` atau `curl` (biasanya sudah terinstal di Linux)