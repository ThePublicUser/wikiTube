import os
import json
import subprocess
import whisper


# ---------------------------------------------------------
# Utility: Run subprocess safely
# ---------------------------------------------------------
def run(cmd):
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


# ---------------------------------------------------------
# Utility: Get duration using ffprobe
# ---------------------------------------------------------
def get_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        path
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


# ---------------------------------------------------------
# PASS 1: Merge background videos (FAST, reusable)
# ---------------------------------------------------------
def merge_bg_videos(
    video_dir,
    output_file,
    width=1080,
    height=1920,
    fps=30
) -> bool:
    os.makedirs(os.path.dirname(output_file), exist_ok=True)


    if not os.path.exists(video_dir):
        print(f"❌ Folder not found: {video_dir}")
        return False

    videos = sorted(
        os.path.abspath(os.path.join(video_dir, f)).replace("\\", "/")
        for f in os.listdir(video_dir)
        if f.lower().endswith(".mp4")
    )

    if not videos:
        print("❌ No videos found")
        return False

    print(f"🎞️ Merging {len(videos)} videos")

    inputs = []
    filters = []

    for i, v in enumerate(videos):
        inputs.extend(["-i", v])
        filters.append(
            f"[{i}:v]"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={fps},"
            f"setsar=1,"
            f"format=yuv420p"
            f"[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(videos)))

    filter_complex = (
        ";".join(filters)
        + f";{concat_inputs}concat=n={len(videos)}:v=1:a=0[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        output_file
    ]

    print("🚀 Merging background videos...")
    print("🧾 FFmpeg command:\n", " ".join(cmd))

    # IMPORTANT: don't swallow stderr during debugging
    subprocess.run(cmd, check=True)

    print(f"✅ Merged video created: {output_file}")
    return True


# ---------------------------------------------------------
# Whisper → ASS subtitles (word-by-word)
# ---------------------------------------------------------
def generate_ass_subtitles(
    audio_path,
    ass_file,
    whisper_model="base",
    language="en"
) -> bool:

    if not os.path.exists(audio_path):
        print(f"❌ Audio not found: {audio_path}")
        return False

    print(f"🧠 Loading Whisper model: {whisper_model}")
    model = whisper.load_model(whisper_model)

    print("🎙️ Transcribing audio...")
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        language=language
    )

    def ass_time(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        cs = int((t % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    ass = """[Script Info]
Title: TikTok Style
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial Black,80,&H0000FFFF,&H00000000,&H80000000,-1,0,1,4,0,5,10,10,80

[Events]
Format: Layer, Start, End, Style, Text
"""

    word_count = 0
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            ass += (
                f"Dialogue: 0,"
                f"{ass_time(w['start'])},"
                f"{ass_time(w['end'])},"
                f"Default,{w['word'].strip()}\n"
            )
            word_count += 1

    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(ass)

    print(f"✅ ASS subtitles created ({word_count} words)")
    return True


# ---------------------------------------------------------
# PASS 2: FINAL render (trim + speed + audio + subtitles)
# ---------------------------------------------------------
def final_render(
    merged_video,
    audio_path,
    ass_file,
    output_path
) -> bool:

    video_dur = get_duration(merged_video)
    audio_dur = get_duration(audio_path)

    speed = 1.0
    trim_end = audio_dur

    if video_dur < audio_dur:
        if video_dur * 1.2 >= audio_dur:
            speed = 1.2
        elif video_dur * 1.25 >= audio_dur:
            speed = 1.25
        else:
            speed = 1.25

    vf = f"setpts=PTS/{speed},trim=0:{trim_end},ass={ass_file}"

    cmd = [
        "ffmpeg", "-y",
        "-i", merged_video,
        "-i", audio_path,
        "-filter_complex", f"[0:v]{vf}[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    print("🚀 Final render...")
    run(cmd)

    print(f"🎉 Final video created: {output_path}")
    return True

def final_videos(content_id,merged_videos_path,ass_files,final_name,bg_root,audio_root):
    print(f"====Processing conent {content_id}==== ")
    merge_bg_videos(bg_root,merged_videos_path)
    generate_ass_subtitles(audio_root,ass_files)
    final_render(merged_videos_path,audio_root,ass_files,final_name)


