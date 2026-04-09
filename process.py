#!/usr/bin/env python3
"""
TikTok Video Processor
Applies FFmpeg transformations to prepare videos for reposting.
Requires explicit permission from original creators before use.
"""

import os
import subprocess
import argparse
import random
import sys
from pathlib import Path


def process_video(input_path: str, output_path: str, options: dict = {}):
    """Apply FFmpeg transformations to a video."""

    # Randomize small values to make each output unique
    speed = options.get("speed", round(random.uniform(0.94, 0.97), 3))
    brightness = options.get("brightness", round(random.uniform(0.03, 0.07), 3))
    saturation = options.get("saturation", round(random.uniform(1.05, 1.15), 3))
    contrast = options.get("contrast", round(random.uniform(1.03, 1.07), 3))
    flip = options.get("flip", True)
    volume = options.get("volume", round(random.uniform(1.02, 1.08), 3))

    audio_tempo = round(1 / speed, 4)  # Match audio to video speed

    vf_filters = [
        "scale=1080:1920:force_original_aspect_ratio=decrease",
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
    ]

    if flip:
        vf_filters.append("hflip")

    vf_filters.append(
        f"eq=brightness={brightness}:saturation={saturation}:contrast={contrast}"
    )
    vf_filters.append(f"setpts={speed}*PTS")

    vf_string = ",".join(vf_filters)
    af_string = f"atempo={audio_tempo},volume={volume}"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf_string,
        "-af", af_string,
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    print(f"Processing: {input_path}")
    print(f"  Speed: {speed} | Flip: {flip} | Brightness: {brightness}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-300:]}")
        return False

    print(f"  Done -> {output_path}")
    return True


def batch_process(input_dir: str, output_dir: str):
    """Process all MP4 files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    videos = list(input_path.glob("*.mp4")) + list(input_path.glob("*.mov"))

    if not videos:
        print(f"No MP4/MOV files found in {input_dir}")
        return

    print(f"Found {len(videos)} videos to process\n")

    success, failed = 0, 0
    for video in videos:
        out_file = output_path / f"processed_{video.name}"
        if process_video(str(video), str(out_file)):
            success += 1
        else:
            failed += 1

    print(f"\nDone: {success} processed, {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch video processor for TikTok")
    parser.add_argument("--input", default="/app/input", help="Input folder")
    parser.add_argument("--output", default="/app/output", help="Output folder")
    parser.add_argument("--file", help="Process a single file")
    args = parser.parse_args()

    if args.file:
        out = str(Path(args.output) / f"processed_{Path(args.file).name}")
        Path(args.output).mkdir(parents=True, exist_ok=True)
        process_video(args.file, out)
    else:
        batch_process(args.input, args.output)
