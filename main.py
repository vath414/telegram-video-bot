import os
import subprocess
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
        # Based on investigation, it looks like /videos/ID/stream
        match = re.search(r"https?://kingbokeptv\.com/videos/\d+/stream", r.text)
        if match:
            direct_url = match.group(0)
            print(f"Found direct video URL: {direct_url}")
            return direct_url
        
        # Fallback: look for any .mp4 link
        mp4_matches = re.findall(r"https?://[^\s\"']+\.mp4", r.text)
        if mp4_matches:
            # Filter out common false positives
            for url in mp4_matches:
                if "kingbokeptv.com" in url and "/video/" not in url:
                    print(f"Found potential mp4 URL: {url}")
                    return url
                    
        print("Could not find direct video URL in page source.")
        return None
    except Exception as e:
        print(f"Error during URL extraction: {e}")
        return None

def download_video(url):
    # Try to get the direct stream URL first
    direct_url = get_direct_video_url(url)
    
    # If we found a direct URL, use it. Otherwise, try the original URL with yt-dlp
    target_url = direct_url if direct_url else url
    print(f"Starting download for: {target_url}")
    
    # Build yt-dlp command
    cmd = [
        "python3", "-m", "yt_dlp",
        "--no-check-certificate",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--extractor-args", "generic:impersonate=chrome",
    ]
    
    # Only use cookies if the file exists and is not empty
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        print("Using cookies.txt for authentication.")
        cmd.extend(["--cookies", "cookies.txt"])
    
    cmd.append(target_url)
    
    try:
        subprocess.run(cmd, check=True)
        print("Download finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error: yt-dlp failed with exit code {e.returncode}")
        if not direct_url:
            print("Since no direct URL was found, this failure is expected due to Cloudflare.")
        sys.exit(1)

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
    download_video(VIDEO_URL)
    
    print("Scanning for downloaded video files...")
    video_extensions = ["*.mp4", "*.mkv", "*.webm", "*.mov", "*.avi"]
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(ext))
    
    if not video_files:
        print("No video files found in the current directory.")
        sys.exit(1)
    
    success_count = 0
    for file in video_files:
        if upload_to_telegram(file):
            os.remove(file)
            print(f"Deleted local file: {file}")
            success_count += 1
        else:
            print(f"Failed to process: {file}")
            
    print(f"Task completed. Successfully processed {success_count} out of {len(video_files)} files.")

if __name__ == "__main__":
    main()