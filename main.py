import os
import subprocess
import requests
import glob
import sys

# Get secrets from GitHub
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

VIDEO_URL = "https://kingbokeptv.com/video/cane-tiktok-join-tele-lupabelum-17mp4"

def download_video(url):
    print(f"Starting download for: {url}")
    
    # Base command with chrome impersonation to bypass Cloudflare
    cmd = [
        "python3", "-m", "yt_dlp",
        "--no-check-certificate",
        "--extractor-args", "generic:impersonate=chrome",
    ]
    
    # Only use cookies if the file exists and is not empty
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        print("Using cookies.txt for authentication.")
        cmd.extend(["--cookies", "cookies.txt"])
    else:
        print("No valid cookies.txt found. Proceeding without cookies.")
    
    cmd.append(url)
    
    try:
        subprocess.run(cmd, check=True)
        print("Download finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error: yt-dlp failed with exit code {e.returncode}")
        # Try a fallback without impersonation if it failed
        print("Attempting fallback download without impersonation...")
        fallback_cmd = ["python3", "-m", "yt_dlp", "--no-check-certificate", url]
        try:
            subprocess.run(fallback_cmd, check=True)
            print("Fallback download finished successfully.")
        except subprocess.CalledProcessError:
            print("Error: Fallback download also failed.")
            sys.exit(1)

def upload_to_telegram(file_path):
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    
    print(f"Processing: {file_path} ({size_mb:.2f} MB)")
    
    if size_bytes > 2 * 1024 * 1024 * 1024:
        print(f"Skipping {file_path}: File size exceeds Telegram's 2GB limit.")
        return False

    print(f"Uploading {file_path} to Telegram...")
    
    # Use sendVideo for better playback, fallback to sendDocument if needed
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    
    try:
        with open(file_path, "rb") as f:
            files = {"video": f}
            data = {"chat_id": CHAT_ID, "caption": f"Downloaded: {os.path.basename(file_path)}"}
            response = requests.post(url, data=data, files=files, timeout=600) # 10 min timeout
            
        if response.status_code != 200:
            print(f"Upload failed with status {response.status_code}: {response.text}")
            # Fallback to sendDocument
            print("Attempting fallback to sendDocument...")
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