# Instagram Reel Scheduler — Full Integration

## What this is
A runnable app: upload a ZIP containing reel videos and the app extracts only video
files, generates a thumbnail for each, queues them for automatic publication, and
removes published video and thumbnail assets after success.

## My verdict on the two repos/architectures you shared

### indic-voice-pipeline (humancto)
- **Use it**: wrap its Whisper/IndicWhisper/Qwen3-ASR engine in our `transcriber.py`.
- **Don't use**: its yt-dlp downloader (we get videos from the ZIP).
- **Doesn't solve**: thumbnails, captions, hashtags, scheduling — we build those.
- **MIT licensed**; respect individual model licenses.
- **Cost**: local models = CPU/RAM/disk, no per-reel API fees.

### ChatGPT's Vercel+Render+Supabase+R2+RunPod architecture
- **Overkill for an MVP**. Good for multi-user production, not for one person testing the pipeline.
- **Simpler path**: single FastAPI + SQLite + local AI (Whisper, Pillow, Pollinations) = $0 running cost.
- Upgrade to cloud only when you need the scheduler to survive laptop shutdown.

## Automatic pipeline per reel
```
ZIP upload
  ├─ Extract video files only (ZIP is not retained)
  ├─ Generate a distinct thumbnail per video
  ├─ Process and automatically schedule each reel
  └─ Publish when due, then remove its video and thumbnail files
```

No separate processing or scheduling button is needed. The uploaded ZIP itself is
not retained; non-video files inside it are ignored. Each reel receives a distinct
public thumbnail URL. Published local source files and their temporary public
copies are removed after Instagram confirms publication.

## Prerequisites
- Python 3.10+ (the venv already exists)
- FFmpeg installed and on PATH (`ffmpeg -version` to verify)
- Activate venv first: `venv\Scripts\activate`

## Install
```
pip install -r requirements.txt
```

## Config
Copy `.env.example` → `.env` and fill in:
- `PUBLIC_BASE_URL` — must be publicly reachable (ngrok for testing, real domain for production)
- `IG_USER_ID`, `IG_ACCESS_TOKEN` — from Meta Developer Portal
- `TAVILY_API_KEY` — from tavily.com
- `LLM_API_KEY` — free Groq key (groq.com) or OpenRouter key

## Run
```
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```
Open http://localhost:8000

## API
- POST /api/upload — upload ZIP and automatically start processing/scheduling
- POST /api/process/{id} — manually reprocess one reel (optional)
- POST /api/process-all — manually process pending reels (optional)
- GET  /api/jobs — list jobs
- POST /api/schedule — manually schedule ready reels (optional)
- POST /api/publish/{id} — publish now
- GET  /api/config — get saved credentials
- POST /api/config — save credentials

## Notes on Meta scheduling
Meta's `published_status=scheduled` support varies by API version/account type.
This app uses a **local scheduler** (background thread polling SQLite) which is fully
reliable regardless of Meta's support. The Reel is published by calling `media_publish`
at the scheduled time.

## Thumbnail generation
The app extracts a frame at two seconds with FFmpeg, then uses Pillow to add a
dark overlay and bold caption text. Each reel's thumbnail is stored separately
and exposed at a distinct public URL.
