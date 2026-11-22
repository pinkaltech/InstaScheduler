import subprocess
import json
from pathlib import Path


PIPELINE_SCRIPT = Path(
    r"D:\Projects\Scheduler\Instagram\whisper_transcribe.py"
).resolve()


def transcribe_video(
    video_path: str,
    output_dir: str,
    language: str | None = None,
):
    video_path = Path(video_path).resolve()
    output_dir = Path(output_dir).resolve()

    # ---------------------------------------------------------
    # Validate paths
    # ---------------------------------------------------------

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found:\n{video_path}")

    if not PIPELINE_SCRIPT.exists():
        raise FileNotFoundError(f"Whisper script not found:\n{PIPELINE_SCRIPT}")

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Video:")
    print(video_path)

    print(f"\nWhisper script:")
    print(PIPELINE_SCRIPT)

    print(f"\nOutput directory:")
    print(output_dir)

    # ---------------------------------------------------------
    # Build command
    # ---------------------------------------------------------

    command = [
        "python",
        str(PIPELINE_SCRIPT),
        "transcribe",
        str(video_path),
        "--model",
        "base",
        "--output-dir",
        str(output_dir),
    ]

    if language:
        command.extend(["--language", language])

    print("\nRunning command:")
    print("=" * 70)

    print(subprocess.list2cmdline(command))

    print("=" * 70)

    # ---------------------------------------------------------
    # Run Whisper
    # ---------------------------------------------------------

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # ---------------------------------------------------------
    # Show stdout
    # ---------------------------------------------------------

    print("\nWHISPER STDOUT")
    print("=" * 70)

    if result.stdout:
        print(result.stdout)
    else:
        print("(empty)")

    # ---------------------------------------------------------
    # Show stderr
    # ---------------------------------------------------------

    print("\nWHISPER STDERR")
    print("=" * 70)

    if result.stderr:
        print(result.stderr)
    else:
        print("(empty)")

    # ---------------------------------------------------------
    # Check return code
    # ---------------------------------------------------------

    print("\nWHISPER EXIT CODE:")
    print(result.returncode)

    if result.returncode != 0:
        raise RuntimeError(f"Whisper failed with exit code {result.returncode}")

    # ---------------------------------------------------------
    # Look for generated JSON
    # ---------------------------------------------------------

    print("\nFILES CREATED")
    print("=" * 70)

    files = list(output_dir.iterdir())

    if not files:
        print("(No files created)")
    else:
        for file in files:
            print(file.name)

    json_files = list(output_dir.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(
            "\nWhisper exited successfully, but no JSON file was created."
        )

    # ---------------------------------------------------------
    # Pick JSON file
    # ---------------------------------------------------------

    json_file = json_files[-1]

    print("\nUsing JSON:")
    print(json_file)

    # ---------------------------------------------------------
    # Read JSON
    # ---------------------------------------------------------

    with open(json_file, "r", encoding="utf-8") as f:
        result_json = json.load(f)

    return result_json


# =========================================================
# MAIN
# =========================================================

result = transcribe_video(
    r"C:\Users\RathodPinkal\Downloads\short ai tiktok video #viral #video #storytelling #ai #tiktok #reels #animation #shorts  #stories ⚡🙏.mp4",
    r"D:\Projects\Scheduler\Instagram\output\transcript",
)


# =========================================================
# PRINT TRANSCRIPT
# =========================================================

print("\n")
print("=" * 70)
print("TRANSCRIPT")
print("=" * 70)

print(result["text"])

print("=" * 70)
