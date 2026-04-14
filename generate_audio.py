"""
Mr. Helmet TTS Audio Generator
使用 Edge TTS (微软免费) 生成马来语销售话术音频
输出: helmet_sales_audio.mp3 + segments.json
"""

import asyncio
import json
import os
import io
import struct
import sys

# Edge TTS voice options for Malay:
# ms-MY-YasminNeural (female, professional)
# ms-MY-OsmanNeural (male, professional)
VOICE = "ms-MY-YasminNeural"
SCRIPT_FILE = "sales_script.txt"
OUTPUT_MP3 = "helmet_sales_audio.mp3"
OUTPUT_SEGMENTS = "segments.json"


def read_script(filepath):
    """Read and split script into paragraphs by double newline."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read().strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


async def generate_segment(text, voice, output_path):
    """Generate audio for a single paragraph and collect word boundaries."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    word_boundaries = []

    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "offset": chunk["offset"],       # in ticks (100ns units)
                    "duration": chunk["duration"],   # in ticks
                    "text": chunk["text"]
                })

    # Calculate segment duration from word boundaries
    if word_boundaries:
        last = word_boundaries[-1]
        # offset and duration are in 100-nanosecond ticks
        end_ticks = last["offset"] + last["duration"]
        duration_sec = end_ticks / 10_000_000  # convert ticks to seconds
    else:
        duration_sec = 0

    return duration_sec, word_boundaries


def get_mp3_duration_from_file(filepath):
    """Estimate MP3 duration by file size and bitrate, or use actual frame parsing."""
    file_size = os.path.getsize(filepath)
    # Edge TTS outputs ~48kbps on average, but let's use a more robust method
    # For simplicity, estimate from file size assuming ~48kbps
    # 48000 bits/sec = 6000 bytes/sec
    # A more accurate approach: use the word boundary data instead
    return file_size / 6000  # rough estimate in seconds


async def main():
    try:
        import edge_tts
    except ImportError:
        print("Error: edge-tts not installed. Run: pip install edge-tts")
        sys.exit(1)

    # Read script
    if not os.path.exists(SCRIPT_FILE):
        print(f"Error: {SCRIPT_FILE} not found")
        sys.exit(1)

    paragraphs = read_script(SCRIPT_FILE)
    print(f"Found {len(paragraphs)} paragraphs")

    # Generate audio for each paragraph
    segments = []
    temp_files = []
    cumulative_time = 0.0

    for i, para in enumerate(paragraphs):
        temp_path = f"_temp_segment_{i}.mp3"
        temp_files.append(temp_path)

        print(f"  Generating segment {i+1}/{len(paragraphs)}...")
        duration_sec, boundaries = await generate_segment(para, VOICE, temp_path)

        # Use actual audio file for more accurate duration
        # The word boundary duration is the speech duration
        # But audio file may have trailing silence
        actual_file_duration = get_mp3_duration_from_file(temp_path)

        # Use the larger of word-boundary duration and file-based estimate
        # Word boundaries are more accurate for speech content
        segment_duration = max(duration_sec, actual_file_duration) if duration_sec > 0 else actual_file_duration

        # Add a small gap between segments (0.3s)
        gap = 0.3 if i < len(paragraphs) - 1 else 0

        segments.append({
            "start": round(cumulative_time, 1),
            "end": round(cumulative_time + segment_duration, 1),
            "text": para
        })

        cumulative_time += segment_duration + gap
        print(f"    Duration: {segment_duration:.1f}s (cumulative: {cumulative_time:.1f}s)")

    # Concatenate all MP3 segments into one file
    print(f"\nConcatenating {len(temp_files)} segments...")
    with open(OUTPUT_MP3, "wb") as outfile:
        for tf in temp_files:
            with open(tf, "rb") as infile:
                outfile.write(infile.read())

    # Clean up temp files
    for tf in temp_files:
        os.remove(tf)

    # Write segments.json
    with open(OUTPUT_SEGMENTS, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    # Summary
    total_size = os.path.getsize(OUTPUT_MP3)
    total_duration = segments[-1]["end"] if segments else 0

    print(f"\n{'='*50}")
    print(f"Generation complete!")
    print(f"  Audio: {OUTPUT_MP3} ({total_size/1024/1024:.1f} MB)")
    print(f"  Duration: {total_duration:.0f}s ({total_duration/60:.1f} min)")
    print(f"  Segments: {OUTPUT_SEGMENTS} ({len(segments)} paragraphs)")
    print(f"  Voice: {VOICE}")

    if total_size > 10 * 1024 * 1024:
        print(f"  WARNING: MP3 exceeds 10MB limit!")
    if total_duration < 60:
        print(f"  NOTE: Audio is shorter than expected (< 1 min)")


if __name__ == "__main__":
    asyncio.run(main())
