import os

from datetime import datetime, timezone

from manage_media import download_and_convert
from manage_media import get_media
from manage_media import grab_thumbnail
from manage_media import create_thumbnail
from youtube import upload_video_to_yt
from youtube import set_thumbnail

if __name__ == "__main__":
    media = get_media()
    print(media)
    if not media:
        raise RuntimeError("Failed to get the video of the day")
    
    video = download_and_convert(media["video_url"])
    if not video:
        raise RuntimeError("Failed to download and convert the video")
    
    bg = grab_thumbnail(video)
    if not bg:
        raise RuntimeError("Failed to grab background image")
    
    thumnail = create_thumbnail(
        template_path="template.png",
        output_path="thumbnail_output.png",
        background_path=bg,
        date_text=media["date"]
    )

    if not thumnail:
        raise RuntimeError("Fialed to create a thumnail")
    
    response  =upload_video_to_yt(
        video,
        media['title'],
        media['description']
    )
    if not response:
        raise RuntimeError("failed to upload vedio")
    thumbnail_response = set_thumbnail(response['id'],thumnail)
    if not thumbnail_response:
        raise RuntimeError("Failed to set thumbnail")
    os.remove(video)
    os.remove(thumnail)
   

    
    




