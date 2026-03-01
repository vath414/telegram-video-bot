import os
import requests
import glob
import sys
import re
import json
import subprocess
from datetime import datetime
from curl_cffi import requests as curl_requests

# ==============================
# CONFIG
# ==============================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HISTORY_FILE = "history.json"
DAILY_LIMIT = 10
MAX_TELEGRAM_MB = 48   # safe limit under 50MB

if not TOKEN or not CHAT_ID:
    print("Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

# ==============================
# HISTORY
# ==============================

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {
                        "sent_urls": data,
                        "last_reset": datetime.now().strftime("%Y-%m-%d"),
                        "daily_count": 0
                    }
                return data
        except:
            pass

    return {
        "sent_urls": [],
        "last_reset": datetime.now().strftime("%Y-%m-%d"),
        "daily_count": 0
    }


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


# ==============================
# SCRAPING
# ==============================

def get_video_links():
    print("Fetching homepage...")
    r = curl_requests.get(
        "https://kingbokeptv.com",
        impersonate="chrome",
        timeout=30
    )

    if r.status_code != 200:
        print("Failed to fetch homepage")
        return []

    links = set(re.findall(
        r"https?://kingbokeptv\.com/video/[^\s\"']+",
        r.text
    ))

    print(f"Found {len(links)} videos")
    return list(links)


def get_direct_video_url(page_url):
    print(f"Fetching page: {page_url}")

    r = curl_requests.get(page_url, impersonate="chrome", timeout=30)
    if r.status_code != 200:
        print("Failed to fetch video page")
        return None

    match = re.search(
        r"https?://kingbokeptv\.com/videos/\d+/stream",
        r.text
    )

    if match:
        print("Direct stream URL found")
        return match.group(0)

    print("No direct video found")
    return None


# ==============================
# DOWNLOAD
# ==============================

def download_file(url, filename):
    print("Downloading video...")

    r = curl_requests.get(
        url,
        impersonate="chrome",
        stream=True,
        timeout=600
    )

    if r.status_code != 200:
        print("Download failed")
        return False

    total = 0
    with open(filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                total += len(chunk)

    print(f"Downloaded: {total / (1024*1024):.2f} MB")
    return True


# ==============================
# COMPRESSION
# ==============================

def compress_video(input_file, output_file):
    print("Compressing video with ffmpeg...")

    try:
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", input_file,
            "-vcodec", "libx264",
            "-preset", "veryfast",
            "-crf", "28",
            "-movflags", "+faststart",
            output_file
        ], check=True)

        size = os.path.getsize(output_file) / (1024*1024)
        print(f"Compressed size: {size:.2f} MB")
        return True

    except Exception as e:
        print(f"Compression failed: {e}")
        return False


# ==============================
# TELEGRAM UPLOAD
# ==============================

def upload_to_telegram(file_path):
    size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if size_mb > MAX_TELEGRAM_MB:
        print(f"File still too large after compression ({size_mb:.2f} MB). Skipping.")
        return False

    print("Uploading to Telegram...")

    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"

    with open(file_path, "rb") as f:
        response = requests.post(
            url,
            data={"chat_id": CHAT_ID},
            files={"video": f},
            timeout=600
        )

    if response.status_code != 200:
        print("Upload failed:", response.text)
        return False

    print("Upload successful")
    return True


# ==============================
# MAIN
# ==============================

def main():
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")

    if history["last_reset"] != today:
        print("New day detected. Resetting counter.")
        history["last_reset"] = today
        history["daily_count"] = 0

    if history["daily_count"] >= DAILY_LIMIT:
        print("Daily limit reached.")
        save_history(history)
        return

    links = get_video_links()
    new_links = [l for l in links if l not in history["sent_urls"]]

    if not new_links:
        print("No new videos.")
        save_history(history)
        return

    page_url = new_links[0]
    print(f"\nProcessing: {page_url}")

    stream_url = get_direct_video_url(page_url)
    if not stream_url:
        return

    original = "temp_video.mp4"
    compressed = "compressed.mp4"

    if download_file(stream_url, original):

        if compress_video(original, compressed):

            if upload_to_telegram(compressed):
                history["sent_urls"].append(page_url)
                history["daily_count"] += 1

        # Cleanup
        if os.path.exists(original):
            os.remove(original)

        if os.path.exists(compressed):
            os.remove(compressed)

    save_history(history)

    print(f"\nDone. Daily count: {history['daily_count']}/{DAILY_LIMIT}")


if __name__ == "__main__":
    main()