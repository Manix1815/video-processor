#!/usr/bin/env python3
import os
import subprocess
import argparse
import random
import json
from pathlib import Path


def check_metadata(filepath: str):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    tags = data.get("format", {}).get("tags", {})
    if tags:
        print(f"  ⚠️  Metadatos restantes: {tags}")
    else:
        print(f"  ✅ Sin metadatos detectables")


def process_video(input_path: str, output_path: str, options: dict = {}):

    speed = options.get("speed", round(random.uniform(0.94, 0.97), 3))
    brightness = options.get("brightness", round(random.uniform(0.03, 0.07), 3))
    saturation = options.get("saturation", round(random.uniform(1.05, 1.15), 3))
    contrast = options.get("contrast", round(random.uniform(1.03, 1.07), 3))
    flip = options.get("flip", True)
    volume = options.get("volume", round(random.uniform(1.02, 1.08), 3))

    audio_tempo = round(1 / speed, 4)

    # Fecha de creación aleatoria falsa
    fake_date = f"2024-0{random.randint(1,9)}-{random.randint(10,28)}T{random.randint(10,20)}:{random.randint(10,59)}:00Z"

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
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-metadata", f"creation_time={fake_date}",
        "-vf", vf_string,
        "-af", af_string,
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "mp4",
        "-movflags", "+faststart",
        output_path
    ]

    print(f"\nProcessing: {input_path}")
    print(f"  Speed: {speed} | Flip: {flip} | Brightness: {brightness} | Saturation: {saturation}")
    print(f"  Fake date: {fake_date}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-300:]}")
        return False

    print(f"  Done -> {output_path}")
    check_metadata(output_path)
    return True


def batch_process(input_dir: str, output_dir: str):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    videos = (
        list(input_path.glob("*.mp4")) +
        list(input_path.glob("*.mov")) +
        list(input_path.glob("*.MP4")) +
        list(input_path.glob("*.MOV"))
    )

    if not videos:
        print(f"No MP4/MOV files found in {input_dir}")
        return

    print(f"Found {len(videos)} videos to process")

    success, failed = 0, 0
    for video in videos:
        out_file = output_path / f"processed_{video.stem}.mp4"
        if process_video(str(video), str(out_file)):
            success += 1
        else:
            failed += 1

    print(f"\n{'='*40}")
    print(f"Finished: {success} processed, {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch video processor")
    parser.add_argument("--input", default="/app/data/input", help="Input folder")
    parser.add_argument("--output", default="/app/data/output", help="Output folder")
    parser.add_argument("--file", help="Process a single file")
    args = parser.parse_args()

    if args.file:
        out = str(Path(args.output) / f"processed_{Path(args.file).stem}.mp4")
        Path(args.output).mkdir(parents=True, exist_ok=True)
        process_video(args.file, out)
    else:
        batch_process(args.input, args.output)
