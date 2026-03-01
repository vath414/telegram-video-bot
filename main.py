import os
import subprocess
import requests
import glob

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

OUTPUT_TEMPLATE = "%(title)s.%(ext)s"
URL_FILE = "urls.txt"

print("Starting download...")

# Download using yt-dlp with cookies and batch file
VIDEO_URL = "https://kingbokep.wiki/indonesia/ketika-hanya-ada-kita-berdua-dirumah-majikan-lagi-liburan/"

subprocess.run([
    "yt-dlp",
    "-o", OUTPUT_TEMPLATE,
    "--cookies", "cookies.txt",
    VIDEO_URL
], check=True)

print("Download finished.")
print("Scanning downloaded files...")

# Find all files in directory
files = glob.glob("*")

for file in files:
    if file in ["main.py", "urls.txt", "cookies.txt"]:
        continue

    if os.path.isdir(file):
        continue

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

    os.remove(file)
    print("Deleted local file.")

print("All done.")