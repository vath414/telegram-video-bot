import os
import requests
import glob
import sys
import re
import json
from datetime import datetime
from curl_cffi import requests as curl_requests

# Get secrets from GitHub
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HISTORY_FILE = "history.json"
DAILY_LIMIT = 10

if not TOKEN or not CHAT_ID:
    print("Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                # Handle both old format (list) and new format (dict)
                if isinstance(data, list):
                    return {"sent_urls": data, "last_reset": datetime.now().strftime("%Y-%m-%d"), "daily_count": 0}
                return data
        except Exception as e:
            print(f"Error loading history: {e}")
    return {"sent_urls": [], "last_reset": datetime.now().strftime("%Y-%m-%d"), "daily_count": 0}

def save_history(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)
    except Exception as e:
        print(f"Error saving history: {e}")

def get_video_links():
    print("Fetching home page to find video links...")
    try:
        r = curl_requests.get("https://kingbokeptv.com", impersonate="chrome", timeout=30)
        if r.status_code != 200:
            print(f"Failed to fetch home page: HTTP {r.status_code}")
            return []
        
        links = set(re.findall(r"https?://kingbokeptv\.com/video/[^\s\"'\'']+", r.text))
        print(f"Found {len(links)} total video links on the page.")
        return list(links)
    except Exception as e:
        print(f"Error fetching video links: {e}")
        return []

def get_direct_video_url(page_url):
    print(f"Fetching page to find direct video URL: {page_url}")
    try:
        r = curl_requests.get(page_url, impersonate="chrome", timeout=30)
        if r.status_code != 200:
            print(f"Failed to fetch page: HTTP {r.status_code}")
            return None
        
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
        r = curl_requests.get(url, impersonate="chrome", stream=True, timeout=600)
        if r.status_code != 200:
            print(f"Failed to download video: HTTP {r.status_code}")
            return False
        
        total_downloaded = 0
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    total_downloaded += len(chunk)
        
        print(f"Download finished: {filename} ({total_downloaded / (1024 * 1024):.2f} MB)")
        return True
    except Exception as e:
        print(f"Error during download: {e}")
        return False

def upload_to_telegram(file_path):
    size_bytes = os.path.getsize(file_path)
    if size_bytes > 2 * 1024 * 1024 * 1024:
        print(f"Skipping {file_path}: File size exceeds 2GB.")
        return False

    print(f"Uploading {file_path} to Telegram...")
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    
    try:
        with open(file_path, "rb") as f:
            files = {"video": f}
            data = {"chat_id": CHAT_ID}
            response = requests.post(url, data=data, files=files, timeout=600)
            
        if response.status_code != 200:
            print(f"Upload failed: {response.text}")
            url_doc = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
            with open(file_path, "rb") as f:
                files_doc = {"document": f}
                response = requests.post(url_doc, data=data, files=files_doc, timeout=600)
                
        return response.status_code == 200
    except Exception as e:
        print(f"Error during upload: {e}")
        return False

def main():
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Reset daily count if it's a new day
    if history.get("last_reset") != today:
        print(f"New day detected ({today}). Resetting daily count.")
        history["last_reset"] = today
        history["daily_count"] = 0
    
    # Check if we've already reached the daily limit
    if history["daily_count"] >= DAILY_LIMIT:
        print(f"Daily limit of {DAILY_LIMIT} videos reached. Skipping this run.")
        save_history(history)
        return

    all_links = get_video_links()
    
    # Filter out already downloaded videos
    new_links = [link for link in all_links if link not in history["sent_urls"]]
    print(f"Found {len(new_links)} new videos. Daily count: {history['daily_count']}/{DAILY_LIMIT}")
    
    if not new_links:
        print("No new videos found.")
        save_history(history)
        return
    
    # Process only 1 video per run
    page_url = new_links[0]
    print(f"\n--- Processing: {page_url} ---")
    
    direct_url = get_direct_video_url(page_url)
    if direct_url:
        filename = "temp_video.mp4"
        if download_file_with_curl_cffi(direct_url, filename):
            if upload_to_telegram(filename):
                print("Successfully uploaded to Telegram.")
                history["sent_urls"].append(page_url)
                history["daily_count"] += 1
            else:
                print("Failed to upload to Telegram.")
            
            if os.path.exists(filename):
                os.remove(filename)
    
    save_history(history)
    print(f"\nTask completed. Daily count is now {history['daily_count']}/{DAILY_LIMIT}.")

if __name__ == "__main__":
    main()