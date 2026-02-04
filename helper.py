import os

def get_next_video_path(content_id):
    base_dir = os.path.join("videos", str(content_id))
    os.makedirs(base_dir, exist_ok=True)

    existing = [
        f for f in os.listdir(base_dir)
        if f.startswith("video_") and f.endswith(".mp4")
    ]

    next_index = len(existing) + 1
    return os.path.join(base_dir, f"video_{next_index}.mp4")
