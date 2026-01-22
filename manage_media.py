import requests
import subprocess
import os

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime, timezone

ALLOWED_LICENSES = {"Public domain", "CC-BY", "CC0", "CC BY 3.0"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# download vedio and convert to mp4
def download_and_convert(video_url):
    temp = "source_video" + os.path.splitext(video_url)[1]
    final = "video.mp4"

    print("⬇ Downloading original video...")
    with requests.get(video_url, headers=HEADERS, stream=True) as r:
        r.raise_for_status()
        with open(temp, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

    print("🎬 Converting (audio preserved)...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", temp,
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        final
    ], check=True)

    os.remove(temp)
    return final

# Change date in the thumnail 
def draw_text_with_spacing(draw, text, position, font, fill, spacing=0):
    """
    Draw text with custom letter spacing.
    spacing: number of pixels between letters
    """
    x, y = position
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        # move x by character width + spacing
        char_width = font.getbbox(char)[2] - font.getbbox(char)[0]
        x += char_width + spacing


# Get background image from the video 
def grab_thumbnail(video, out="background.png", ts="00:00:05"):
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", ts,
        "-i", video,
        "-frames:v", "1",
        "-q:v", "2",
        out
    ], check=True)
    return out

#Add background image to the thumnail template
def create_thumbnail(template_path, output_path, background_path, date_text, 
                     color_to_replace=(12, 192, 223), blur_radius=3, font_path="CarterOne.ttf",
                     font_size=54, letter_spacing=9, text_y_offset=150):
    """
    Replace a specific color in template with background and add date text
    with custom letter spacing.
    """
    # Load images
    template = Image.open(template_path).convert("RGBA")
    background = Image.open(background_path).convert("RGBA").resize(template.size)

    # Apply blur to background
    background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Replace template color with background pixels
    template_pixels = template.load()
    background_pixels = background.load()
    width, height = template.size

    for x in range(width):
        for y in range(height):
            r, g, b, a = template_pixels[x, y]
            if (r, g, b) == color_to_replace:
                template_pixels[x, y] = background_pixels[x, y]

    # Draw date text with letter spacing
    draw = ImageDraw.Draw(template)
    font = ImageFont.truetype(font_path, font_size)

    # Calculate starting x to center text with spacing
    total_width = sum((font.getbbox(c)[2] - font.getbbox(c)[0] + letter_spacing) for c in date_text) - letter_spacing
    x = (width - total_width) // 2 - 35
    y = height - text_y_offset

    draw_text_with_spacing(draw, date_text, (x, y), font, fill=(0,0,0,255), spacing=letter_spacing)

    # Save output
    template.save(output_path)
    print(f"Thumbnail saved: {output_path}")
    return output_path


def get_media(manual_date=None):
    """
    Fetch Media of the Day from Wikimedia Commons.
    
    manual_date: str or int in 'YYYYMMDD' format for testing.
                 If None, uses today's month/day and loops back through years until a video is found.
                 
    Returns a dict with video info, or None if no video found.
    """
    # Determine MMDD for lookup
    if manual_date:
        raw_str = str(manual_date)
        if len(raw_str) != 8:
            raise ValueError("manual_date must be in 'YYYYMMDD' format")
        mmdd = raw_str[4:8]  # extract month+day
    else:
        now = datetime.now(timezone.utc)
        mmdd = now.strftime("%m%d")

    # Loop from current year down to 2015 (or adjust as needed)
    for year in range(datetime.now().year, 2014, -1):
        raw_date = f"{year}{mmdd}"
        media = video_of_the_day(raw_date)
        if media:
            dt = datetime.strptime(raw_date, "%Y%m%d")
            media["date"] = dt.strftime("%d %b %Y").upper()
            print(f"✔ Found MOTD for {raw_date}")
            return media

    print(f"⚠ No video found for MMDD={mmdd} in recent years")
    return None

def video_of_the_day(date_str):
    feed_url = f"https://commons.wikimedia.org/wiki/Special:FeedItem/motd/{date_str}000000/en"
    r = requests.get(feed_url, headers=HEADERS)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.content, "html.parser")
    video = soup.find("video")
    if not video:
        return None

    filename = video.get("data-mwtitle")
    if not filename:
        return None

    desc_tag = soup.find("div", class_="description")
    description = desc_tag.get_text(strip=True) if desc_tag else ""

    # ===== Commons API (SOURCE OF TRUTH) =====
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "format": "json"
    }

    data = requests.get(api_url, headers=HEADERS, params=params).json()
    page = next(iter(data["query"]["pages"].values()))
    info = page["imageinfo"][0]

    metadata = info.get("extmetadata", {})
    license_name = metadata.get("LicenseShortName", {}).get("value", "")
    if license_name not in ALLOWED_LICENSES:
        return None
    license_url = metadata.get("LicenseUrl", {}).get("value", "")
    actual_title = metadata.get("ObjectName", {}).get("value") or metadata.get("Title", {}).get("value") or filename
    author_html = metadata.get("Artist", {}).get("value", "Unknown")
    author = clean_author(author_html)
    yt_description = f"""
        📽 Video Title: {actual_title}
        🖋 Author / Creator: {author}
        📄 License: {license_name}
        🔗 License Details: {license_url}
        🌐 Source / Original File: https://commons.wikimedia.org/wiki/File:{filename}
        🎥Source / Original Video : {info["url"]}

        📝 Description:
        {description}

        ⚠️ This media is sourced from Wikimedia Commons Media of the Day. It is free to use commercially under the above license. Please attribute the creator as specified.
        """
    return {
        "title": actual_title,
        "video_url": info["url"], 
        "author": author,
        "license": license_name,
        "license_url": license_url,
        "description": yt_description,
        "filename": filename
    }

def clean_author(author_html):
    soup = BeautifulSoup(author_html, "html.parser")
    a = soup.find("a")
    if a:
        return f"{a.get_text(strip=True)} ({a.get('href')})"
    return soup.get_text(strip=True)