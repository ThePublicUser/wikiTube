import edge_tts
import asyncio
import os
import uuid

async def generate_audio(
    text,
    output_file,
    voice="en-US-JennyNeural",
    chunk_size=500
):
    """
    Generate TTS audio from long text using Edge TTS.
    Handles chunking, merging, and cleanup safely.
    """

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Basic text cleaning
    text = text.replace("``", '"').replace("''", '"')

    # Split text into chunks (by words)
    words = text.split()
    chunks = [
        ' '.join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]

    temp_files = []
    unique_prefix = uuid.uuid4().hex[:8]

    try:
        # Generate audio chunks
        for i, chunk in enumerate(chunks):
            communicate = edge_tts.Communicate(chunk, voice)

            temp_file = f"temp_{unique_prefix}_{i}.mp3"
            await communicate.save(temp_file)
            temp_files.append(temp_file)

            # Prevent rate-limiting
            await asyncio.sleep(0.5)

        # Merge chunks into final audio
        with open(output_file, "wb") as outfile:
            for temp_file in temp_files:
                with open(temp_file, "rb") as infile:
                    outfile.write(infile.read())

        print(f"✅ Audio created: {output_file}")

    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    return output_file
