#!/bin/bash

# Google Drive Downloader Script
# Usage: ./download_gdrive.sh <file_id> [output_filename]

if [ $# -lt 1 ]; then
    echo "Usage: $0 <file_id> [output_filename]"
    echo "Example: $0 1ABC123DEF456 output.zip"
    echo ""
    echo "Note: Make sure the Google Drive file is set to 'Anyone with the link can view'"
    exit 1
fi

FILE_ID="$1"
OUTPUT_FILENAME="${2:-gdrive_file_${FILE_ID}}"

echo "Downloading file ID: $FILE_ID"
echo "Output filename: $OUTPUT_FILENAME"

# Google Drive direct download URL
URL="https://drive.google.com/uc?id=${FILE_ID}"

# Download using wget
if command -v wget >/dev/null 2>&1; then
    echo "Using wget to download..."
    wget --no-check-certificate -O "$OUTPUT_FILENAME" "$URL"
elif command -v curl >/dev/null 2>&1; then
    echo "Using curl to download..."
    curl -L -o "$OUTPUT_FILENAME" "$URL"
else
    echo "Error: Neither wget nor curl is available"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo "Download completed: $OUTPUT_FILENAME"
    ls -lh "$OUTPUT_FILENAME"
else
    echo "Download failed"
    exit 1
fi