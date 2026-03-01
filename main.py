import os
import requests
import glob
import sys
import re
from curl_cffi import requests as curl_requests

# Get secrets from GitHub
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

VIDEO_URL = "https://kingbokeptv.com/video/cane-tiktok-join-tele-lupabelum-17mp4"

def get_direct_video_url(page_url):
    print(f"Fetching page to find direct video URL: {page_url}")
    try:
        # Use curl-cffi to bypass Cloudflare
        r = curl_requests.get(page_url, impersonate="chrome", timeout=30)
        if r.status_code != 200:
            print(f"Failed to fetch page: HTTP {r.status_code}")
            return None
        
        # Look for the stream URL pattern
        match = re.search(r"https?://kingbokeptv\.com/videos/\d+/stream", r.text)
        if match:
            direct_url = match.group(0)
            print(f"Found direct video URL: {direct_url}")
            return direct_url
        
        print("Could not find direct video URL in page source.")
        return None
    except Exception as e:
        print(f"Error during URL extraction: {e}")
        return None

def download_file_with_curl_cffi(url, filename):
    print(f"Downloading video using curl-cffi: {url}")
    try:
        # Use curl-cffi to download the file in chunks
        # Note: curl-cffi's Response object is not a context manager
        r = curl_requests.get(url, impersonate="chrome", stream=True, timeout=600)
        
        if r.status_code != 200:
            print(f"Failed to download video: HTTP {r.status_code}")
            return False
        
        total_downloaded = 0
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=65536): # 64KB chunks
                if chunk:
                    f.write(chunk)
                    total_downloaded += len(chunk)
                    # Log progress every 5MB
                    if total_downloaded % (5 * 1024 * 1024) < 65536:
                        print(f"Downloaded: {total_downloaded / (1024 * 1024):.2f} MB")
        
        print(f"Download finished: {filename} (Total: {total_downloaded / (1024 * 1024):.2f} MB)")
        return True
    except Exception as e:
        print(f"Error during download: {e}")
        return False

def upload_to_telegram(file_path):
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    
    print(f"Processing: {file_path} ({size_mb:.2f} MB)")
    
    if size_bytes > 2 * 1024 * 1024 * 1024:
        print(f"Skipping {file_path}: File size exceeds Telegram's 2GB limit.")
        return False

    print(f"Uploading {file_path} to Telegram...")
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    
    try:
        with open(file_path, "rb") as f:
            files = {"video": f}
            data = {"chat_id": CHAT_ID, "caption": f"Downloaded: {os.path.basename(file_path)}"}
            response = requests.post(url, data=data, files=files, timeout=600)
            
        if response.status_code != 200:
            print(f"Upload failed with status {response.status_code}: {response.text}")
            url_doc = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
            with open(file_path, "rb") as f:
                files_doc = {"document": f}
                response = requests.post(url_doc, data=data, files=files_doc, timeout=600)
                
        if response.status_code == 200:
            print(f"Successfully uploaded: {file_path}")
            return True
        else:
            print(f"Final upload attempt failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"An error occurred during upload: {str(e)}")
        return False

def main():
    direct_url = get_direct_video_url(VIDEO_URL)
    if not direct_url:
        print("Failed to find direct video URL. Exiting.")
        sys.exit(1)
    
    filename = "video.mp4"
    if download_file_with_curl_cffi(direct_url, filename):
        if upload_to_telegram(filename):
            os.remove(filename)
            print(f"Deleted local file: {filename}")
        else:
            print(f"Failed to upload: {filename}")
            sys.exit(1)
    else:
        print("Failed to download video.")
        sys.exit(1)
            
    print("Task completed successfully.")

if __name__ == "__main__":
    main()