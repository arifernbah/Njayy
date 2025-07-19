#!/usr/bin/env python3
"""
Google Drive Downloader Script
Usage: python3 gdrive_downloader.py <file_id> <output_filename>
"""

import urllib.request
import urllib.error
import sys
import os

def download_from_gdrive(file_id, output_filename):
    """
    Download a file from Google Drive using the file ID
    """
    # Google Drive direct download URL
    url = f"https://drive.google.com/uc?id={file_id}"
    
    print(f"Downloading file ID: {file_id}")
    print(f"Output filename: {output_filename}")
    
    try:
        # Start the download
        print("Starting download...")
        urllib.request.urlretrieve(url, output_filename)
        print(f"Download completed: {output_filename}")
        return True
        
    except urllib.error.URLError as e:
        print(f"Error downloading file: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def extract_file_id_from_url(url):
    """
    Extract file ID from Google Drive sharing URL
    """
    if '/file/d/' in url:
        # Format: https://drive.google.com/file/d/FILE_ID/view
        start = url.find('/file/d/') + 8
        end = url.find('/', start)
        return url[start:end]
    elif 'id=' in url:
        # Format: https://drive.google.com/open?id=FILE_ID
        start = url.find('id=') + 3
        end = url.find('&', start)
        if end == -1:
            end = len(url)
        return url[start:end]
    else:
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 gdrive_downloader.py <file_id_or_url> [output_filename]")
        print("Example: python3 gdrive_downloader.py 1ABC123DEF456 output.zip")
        print("\nNote: Make sure the Google Drive file is set to 'Anyone with the link can view'")
        sys.exit(1)
    
    input_arg = sys.argv[1]
    
    # Check if input is a URL or file ID
    if input_arg.startswith('http'):
        file_id = extract_file_id_from_url(input_arg)
        if not file_id:
            print("Could not extract file ID from URL")
            sys.exit(1)
    else:
        file_id = input_arg
    
    # Determine output filename
    if len(sys.argv) >= 3:
        output_filename = sys.argv[2]
    else:
        output_filename = f"gdrive_file_{file_id}"
    
    # Download the file
    success = download_from_gdrive(file_id, output_filename)
    sys.exit(0 if success else 1)