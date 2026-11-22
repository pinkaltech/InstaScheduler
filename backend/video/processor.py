import os
import shutil
from pathlib import Path
import subprocess
import logging

import imageio_ffmpeg

from .thumbnail import generate_thumbnail

logger = logging.getLogger(__name__)


def _ffmpeg_executable() -> str:
    configured_path = os.getenv("FFMPEG_PATH")
    if configured_path:
        if Path(configured_path).is_file():
            return configured_path
        raise FileNotFoundError(f"FFMPEG_PATH does not point to a file: {configured_path}")

    executable = shutil.which("ffmpeg")
    return executable or imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """Extract audio as WAV for Whisper."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg_executable(), "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr}")
    return output_path

def extract_frame(video_path: Path, output_path: Path, timestamp: str = "00:00:02") -> Path:
    """Extract a single frame from video."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(output_path)
    cmd = [
        _ffmpeg_executable(), "-y", "-ss", timestamp,
        "-i", str(video_path), "-vframes", "1",
        "-q:v", "2", str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed: {result.stderr}")
    return output_path

def process_reel_video(reel_id: int, video_path: Path, settings) -> dict:
    """
    Full video processing pipeline:
    1. Extract audio → transcribe (handled by caller)
    2. Extract frame for thumbnail base
    3. Generate trendy thumbnail with text overlay
    Returns dict with paths and metadata.
    """
    processed_dir = settings.PROCESSED_DIR / str(reel_id)
    thumbnail_dir = settings.THUMBNAIL_DIR / str(reel_id)
    processed_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    # Extract frame at 2 seconds (usually past intro)
    frame_path = processed_dir / "frame.jpg"
    extract_frame(video_path, frame_path, "00:00:02")

    # Generate thumbnail (will be called after AI gives us text)
    # This is a placeholder; actual thumbnail generation happens in analyzer
    thumb_path = thumbnail_dir / "thumbnail.jpg"

    return {
        "frame_path": str(frame_path),
        "thumb_path": str(thumb_path),
        "processed_dir": str(processed_dir),
    }

__all__ = ["extract_audio", "extract_frame", "process_reel_video", "generate_thumbnail"]