# Instagram Reel Scheduler — Full Integration

## What this is
A complete, runnable MVP: upload a ZIP of reel videos → the backend processes each reel
(transcription → content AI → thumbnail → Tavily hashtags → schedule → publish to Instagram).

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

## Pipeline per reel
```
reel.mp4
  │
  ├─ FFmpeg → audio.wav + frame.png
  ├─ Whisper (local) → transcript
  ├─ LLM (Groq free / OpenRouter / local) → {topic, hook, caption, thumbnail_text, keywords}
  ├─ Pollinations (free) + Pillow → trendy thumbnail with bold text
  ├─ Tavily agent → trending hashtags
  └─ Scheduler → publish to Instagram via Meta Graph API
```

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
- POST /api/upload — upload ZIP
- POST /api/process/{id} — process one reel
- POST /api/process-all — process all uploaded reels
- GET  /api/jobs — list jobs
- POST /api/schedule — schedule reels (reel_ids, base_time, interval_hours)
- POST /api/publish/{id} — publish now
- GET  /api/config — get saved credentials
- POST /api/config — save credentials

## Notes on Meta scheduling
Meta's `published_status=scheduled` support varies by API version/account type.
This app uses a **local scheduler** (background thread polling SQLite) which is fully
reliable regardless of Meta's support. The Reel is published by calling `media_publish`
at the scheduled time.

## Free thumbnail approach (why this works)
Trendy modern reels are usually: a video frame + gradient overlay + big bold text.
We do exactly that:
1. Extract best frame via FFmpeg
2. Optionally generate AI background via Pollinations (free)
3. Composite dark overlay + Instagram-red accent bar + bold white text with shadow
Result looks like a modern Reel thumbnail, costs $0, works offline.
