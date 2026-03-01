import os
import subprocess
import requests
import glob
import sys

# Get secrets from GitHub
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

VIDEO_URL = "https://kingbokeptv.com/video/cane-tiktok-join-tele-lupabelum-17mp4"

print("Starting download...")

# Download video (no -o option)
subprocess.run([
    "python", "-m", "yt_dlp",
    "--cookies", "cookies.txt",
    "--extractor-args", "generic:impersonate",
    VIDEO_URL
], check=True)
print("Download finished.")
print("Scanning downloaded files...")

# Only look for real video files
video_files = (
    glob.glob("*.mp4") +
    glob.glob("*.mkv") +
    glob.glob("*.webm") +
    glob.glob("*.mov")
)

if not video_files:
    print("No video files found.")
    sys.exit(1)

for file in video_files:
    size_bytes = os.path.getsize(file)
    size_gb = size_bytes / (1024**3)

    print(f"Processing: {file} ({size_gb:.2f} GB)")

    if size_bytes > 2 * 1024 * 1024 * 1024:
        print("Skipping file (over 2GB limit)")
        continue

    print("Uploading to Telegram...")

    with open(file, "rb") as f:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendDocument",
            data={"chat_id": CHAT_ID},
            files={"document": f}
        )

    print("Telegram response:", response.text)

    if response.status_code != 200:
        print("Upload failed.")
        sys.exit(1)

    os.remove(file)
    print("Deleted local file.")

print("All done.")