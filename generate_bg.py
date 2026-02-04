import os
import random
import requests
from dotenv import load_dotenv

# ────────────────────────────────
# Load environment variables
# ────────────────────────────────
load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

PEXELS_VIDEO_API = "https://api.pexels.com/videos/search"
PIXABAY_VIDEO_API = "https://pixabay.com/api/videos/"

MIN_DURATION = 10
MAX_DURATION = 15
MAX_WIDTH = 1080
TIMEOUT = 30


# ────────────────────────────────
# Utility: download file
# ────────────────────────────────
def download_file(url: str, save_path: str):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with requests.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


# ────────────────────────────────
# PEXELS
# ────────────────────────────────
def download_from_pexels(keyword: str, save_path: str):
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY not set")

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": keyword,
        "orientation": "portrait",
        "per_page": 20
    }

    r = requests.get(PEXELS_VIDEO_API, headers=headers, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()

    videos = [
        v for v in data.get("videos", [])
        if MIN_DURATION <= v.get("duration", 0) <= MAX_DURATION
    ]

    if not videos:
        raise RuntimeError("No Pexels videos in 10–15s range")

    video = random.choice(videos)

    files = [
        f for f in video["video_files"]
        if f["height"] > f["width"] and f["width"] <= MAX_WIDTH
    ]

    if not files:
        raise RuntimeError("No suitable vertical ≤1080p Pexels video")

    best = max(files, key=lambda x: x["width"])
    download_file(best["link"], save_path)


# ────────────────────────────────
# PIXABAY
# ────────────────────────────────
def download_from_pixabay(keyword: str, save_path: str):
    if not PIXABAY_API_KEY:
        raise RuntimeError("PIXABAY_API_KEY not set")

    params = {
        "key": PIXABAY_API_KEY,
        "q": keyword,
        "video_type": "film",
        "per_page": 20
    }

    r = requests.get(PIXABAY_VIDEO_API, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()

    hits = [
        h for h in data.get("hits", [])
        if MIN_DURATION <= h.get("duration", 0) <= MAX_DURATION
    ]

    if not hits:
        raise RuntimeError("No Pixabay videos in 10–15s range")

    video = random.choice(hits)

    candidates = [
        v for v in video["videos"].values()
        if v["height"] > v["width"] and v["width"] <= MAX_WIDTH
    ]

    if not candidates:
        raise RuntimeError("No suitable vertical ≤1080p Pixabay video")

    best = max(candidates, key=lambda x: x["width"])
    download_file(best["url"], save_path)


# ────────────────────────────────
# Public API
# ────────────────────────────────
def download_bg_video(keyword: str, output_path: str):
    """
    Download a vertical background video (10–15s, ≤1080p).
    Randomly tries Pexels or Pixabay, falls back automatically.
    """
    sources = [download_from_pexels, download_from_pixabay]
    random.shuffle(sources)

    for source in sources:
        name = "Pexels" if source == download_from_pexels else "Pixabay"
        try:
            source(keyword, output_path)
            print(f"✅ {name} success → {output_path}")
            return output_path
        except Exception as e:
            print(f"⚠️ {name} failed: {e}")

    print(f"❌ Failed to download video for '{keyword}'")
    return None


