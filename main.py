import os
import json
import asyncio
from read_input import read_input
from generate_audio import generate_audio
from generate_bg import download_bg_video
from helper import get_next_video_path
from make_videos import final_videos
from yt_schedule import upload_video_to_yt , get_authenticated_service
import time
from datetime import datetime, timedelta, timezone
import shutil



AUDIO_DIR = "audio"
VIDEOS_DIR = "final_videos"
SUBTITLE_DIR = "subtitles"
BG_VIDEOS='videos'

async def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(SUBTITLE_DIR, exist_ok=True)


    json_data = read_input()
    
    output_file = "output.json"

    data = []

    if json_data and json_data != "[]":
        data = json.loads(json_data)
    elif os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    if not data:
        print("No entries found for today.")
        return

    print(f"{len(data)} contents found. Generating audio...")

    for item in data:
        content_id = item.get("id")
        content_text = item.get("content", "").strip()
        bg_videos = item.get("bg_vedios", [])

        if not content_text:
            print(f"Skipping ID {content_id} (empty content)")
            continue

        audio_path = os.path.join(AUDIO_DIR, f"audio_{content_id}.mp3")

        if not os.path.exists(audio_path):
            await generate_audio(
                text=content_text,
                output_file=audio_path,
                voice="en-US-JennyNeural"
            )
            print(f"Audio generated for ID {content_id}")

        # Download BG videos
        for bg in bg_videos:
            try:
                video_path = get_next_video_path(content_id)               
                download_bg_video(bg, video_path)
                print(f"Downloaded {video_path}")

            except Exception as e:
                print(f"Failed downloading BG video for ID {content_id}: {e}")

    for item in data:
        content_id = item.get("id")
        merged_videos_path = f"final_videos/merged_{content_id}.mp4"
        ass_files = f"subtitles/tiktok_style_{content_id}.ass"
        final_name = f"final_videos/shorts_{content_id}.mp4"
        bg_root = f"videos/{content_id}"
        audio_root=f"audio/audio_{content_id}.mp3"
        final_videos(content_id,merged_videos_path,ass_files,final_name,bg_root,audio_root)

    TOTAL_MINUTES = 24 * 60  # 1440
    video_count = len(data)
    gap_minutes = TOTAL_MINUTES // video_count

    if video_count == 0:
        raise ValueError("No videos to schedule")
    
    start_time = datetime.now(timezone.utc).replace(
    hour=0, minute=0, second=0, microsecond=0
)
    yt= get_authenticated_service()
    for index, item in enumerate(data):
        content_id = item.get("id")
        title = item.get("title")
        description = item.get("description")        
        tags = item.get("tags")
        hashtags = " ".join(
            tag.strip() if tag.strip().startswith("#") else f"#{tag.strip()}"
            for tag in tags
            if tag.strip()
        )
        final_description = description.strip()
        if hashtags:
            final_description += "\n\n" + hashtags

        keywords = item.get("keywords")
        vedio_path=f"final_videos/shorts_{content_id}.mp4"
        
        scheduled_time = (
        start_time + timedelta(minutes=index * gap_minutes)
    ).isoformat(timespec="seconds")
       
        yt_upload=upload_video_to_yt(yt,vedio_path,title,final_description,keywords,scheduled_time)
        print(yt_upload)
            




if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    folders = [AUDIO_DIR, VIDEOS_DIR, SUBTITLE_DIR, BG_VIDEOS]
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Deleted {folder}")
        else:
            print(f"{folder} does not exist, skipping")
    

