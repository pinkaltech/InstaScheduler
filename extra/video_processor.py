import subprocess
from pathlib import Path


def get_duration(video_path: str) -> float:

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=True)

    return float(result.stdout.strip())


def extract_frames(video_path: str, output_dir: str, num_frames: int = 8):

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    duration = get_duration(video_path)
    print(duration)
    frames = []

    for i in range(num_frames):
        timestamp = duration * i / (num_frames - 1) if num_frames > 1 else 0
        timestamp = min(timestamp, max(0, duration - 0.1))

        output = output_dir / f"frame_{i:02d}.png"

        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            print("FFmpeg failed:")
            print(result.stderr)
            raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}")

        frames.append(str(output))

    return frames


frames = extract_frames(
    "C:\\Users\\RathodPinkal\\Downloads\\short ai tiktok video #viral #video #storytelling #ai #tiktok #reels #animation #shorts  #stories ⚡🙏.mp4",
    "frames/reel1",
)

print(frames)
