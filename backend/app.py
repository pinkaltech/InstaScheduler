import logging
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import SessionLocal, init_db
from .instagram import publisher as ig_publisher
from .models import Config, JobStatus, Reel
from .scheduler import scheduler as sched_mod
from .video.processor import extract_audio, extract_frame
from .video.thumbnail import generate_thumbnail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Instagram Reel Scheduler")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.__init__()
for d in (settings.UPLOAD_DIR, settings.PROCESSED_DIR, settings.THUMBNAIL_DIR):
    d.mkdir(parents=True, exist_ok=True)

app.mount("/processed", StaticFiles(directory=str(settings.PROCESSED_DIR)), name="processed")
app.mount("/thumbnails", StaticFiles(directory=str(settings.THUMBNAIL_DIR)), name="thumbnails")


def _to_job_dict(reel: Reel) -> dict:
    thumbnail_url = None
    if reel.thumbnail_path and reel.status != JobStatus.PUBLISHED:
        try:
            thumbnail_relative_path = Path(reel.thumbnail_path).relative_to(
                settings.THUMBNAIL_DIR
            )
        except ValueError:
            logger.warning("Thumbnail path is outside the thumbnail directory: %s", reel.thumbnail_path)
        else:
            thumbnail_url = f"/thumbnails/{thumbnail_relative_path.as_posix()}"

    return {
        "id": reel.id,
        "filename": reel.filename,
        "status": reel.status.value if reel.status else None,
        "topic": reel.topic,
        "hook": reel.hook,
        "caption": reel.caption,
        "hashtags": reel.hashtags or [],
        "thumbnail": thumbnail_url,
        "scheduled_at": reel.scheduled_at.isoformat() if reel.scheduled_at else None,
        "published_at": reel.published_at.isoformat() if reel.published_at else None,
        "error": reel.error,
    }


async def _process_single_reel(reel_id: int):
    db = SessionLocal()
    try:
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if not reel:
            return

        reel.status = JobStatus.RUNNING
        db.commit()

        video_path = Path(reel.original_path)
        print(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        processed_dir = settings.PROCESSED_DIR / str(reel_id)
        processed_dir.mkdir(parents=True, exist_ok=True)

        # audio_path = processed_dir / "audio.wav"
        # extract_audio(video_path, audio_path)

        frame_path = processed_dir / "frame.jpg"
        print(frame_path)
        extract_frame(video_path, frame_path, "00:00:02")

        reel.transcript = "" 
        reel.topic = "Instagram Reel"
        reel.hook = "Hook"
        reel.caption = reel.caption or "My new Reel"
        reel.hashtags = ["#reels", "#instagram", "#viral"]

        thumb_path = settings.THUMBNAIL_DIR / str(reel_id) / "thumbnail.jpg"
        thumbnail_text = f"{reel.caption or 'REEL'} #{reel_id}"
        generate_thumbnail(str(frame_path), thumbnail_text, str(thumb_path), settings=settings)
        reel.thumbnail_path = str(thumb_path)
        reel.processed_path = str(processed_dir)
        reel.status = JobStatus.READY
        reel.error = None
        db.commit()
        sched_mod.auto_schedule_reel(reel_id)
        logger.info("[Pipeline] Reel %s fully processed", reel_id)

    except Exception as exc:
        logger.exception("[Pipeline] Error for Reel %s", reel_id)
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if reel:
            reel.status = JobStatus.FAILED
            reel.error = str(exc)
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def _start():
    init_db()
    try:
        sched_mod.start_scheduler(interval=15)
    except Exception as exc:  # pragma: no cover
        logger.warning("Scheduler did not start: %s", exc)


def _video_destination(member_name: str, extract_dir: Path) -> Path:
    archive_path = PurePosixPath(member_name.replace("\\", "/"))
    if (
        archive_path.is_absolute()
        or not archive_path.parts
        or any(part in (".", "..") for part in archive_path.parts)
        or ":" in archive_path.parts[0]
    ):
        raise HTTPException(400, f"Unsafe video path in ZIP: {member_name}")

    destination = (extract_dir / Path(*archive_path.parts)).resolve()
    try:
        destination.relative_to(extract_dir.resolve())
    except ValueError as exc:
        raise HTTPException(400, f"Unsafe video path in ZIP: {member_name}") from exc
    return destination


@app.post("/api/upload")
async def upload_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Upload a .zip file")

    video_exts = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
    extract_dir = settings.UPLOAD_DIR / "extracted" / uuid4().hex
    extract_dir.mkdir(parents=True, exist_ok=False)
    videos = []
    try:
        file.file.seek(0)
        with zipfile.ZipFile(file.file, "r") as archive:
            for entry in archive.infolist():
                if entry.is_dir() or Path(entry.filename.replace("\\", "/")).suffix.lower() not in video_exts:
                    continue
                destination = _video_destination(entry.filename, extract_dir)
                if destination.exists():
                    raise HTTPException(400, f"Duplicate video path in ZIP: {entry.filename}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                videos.append(destination)
    except zipfile.BadZipFile as exc:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise HTTPException(400, "The uploaded file is not a valid ZIP archive") from exc
    except Exception:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise

    if not videos:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise HTTPException(400, "No video files found in ZIP")

    db = SessionLocal()
    try:
        reels = []
        for video in videos:
            reel = Reel(
                filename=video.name,
                original_path=str(video),
                status=JobStatus.PENDING,
                hashtags=[],
            )
            db.add(reel)
            reels.append(reel)
        db.commit()
        for reel in reels:
            db.refresh(reel)
        jobs = [_to_job_dict(reel) for reel in reels]
        for reel in reels:
            background_tasks.add_task(_process_single_reel, reel.id)
        return {"ok": True, "count": len(jobs), "processing": len(jobs), "jobs": jobs}
    except Exception:
        db.rollback()
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise
    finally:
        db.close()


@app.post("/api/process/{reel_id}")
async def process_reel(reel_id: int, background_tasks: BackgroundTasks):
    db = SessionLocal()
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    db.close()
    if not reel:
        raise HTTPException(404, "Reel not found")
    background_tasks.add_task(_process_single_reel, reel_id)
    return {"ok": True, "reel_id": reel_id, "message": "Processing started"}


@app.post("/api/process-all")
async def process_all(background_tasks: BackgroundTasks):
    db = SessionLocal()
    pending = (
        db.query(Reel)
        .filter(Reel.status.in_([JobStatus.PENDING, JobStatus.FAILED]))
        .order_by(Reel.id)
        .all()
    )
    ids = [reel.id for reel in pending]
    db.close()
    for reel_id in ids:
        try:
            print(reel_id)
            background_tasks.add_task(_process_single_reel, reel_id)
        except Exception as  exc:
            print(exc)
    return {"ok": True, "processing": len(ids), "ids": ids}


@app.post("/api/schedule")
async def schedule_reels():
    scheduled_ids = sched_mod.auto_schedule_ready_reels()
    return {"ok": True, "scheduled": len(scheduled_ids), "reel_ids": scheduled_ids}


@app.post("/api/publish/{reel_id}")
async def publish_now(reel_id: int):
    db = SessionLocal()
    try:
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if not reel:
            raise HTTPException(404, "Reel not found")
        if reel.status not in (JobStatus.READY, JobStatus.SCHEDULED):
            raise HTTPException(400, f"Cannot publish (status={reel.status.value if reel.status else None})")

        caption = reel.caption or ""
        if reel.hashtags:
            caption = (caption + "\n\n" + " ".join(reel.hashtags)).strip()

        video_path = reel.original_path
        thumbnail_path = reel.thumbnail_path
        result = ig_publisher.publish_reel(video_path, caption, thumbnail_path=thumbnail_path)
        reel.status = JobStatus.PUBLISHED
        reel.published_at = datetime.now(timezone.utc)
        reel.instagram_media_id = result.get("id")
        db.commit()
        ig_publisher.cleanup_published_files(video_path, thumbnail_path)
        return {"ok": True, "ig_post_id": result.get("id")}
    except HTTPException:
        raise
    except Exception as exc:
        reel.status = JobStatus.FAILED
        reel.error = str(exc)
        db.commit()
        raise HTTPException(500, str(exc))
    finally:
        db.close()


@app.get("/api/jobs")
async def list_jobs():
    db = SessionLocal()
    try:
        reels = db.query(Reel).order_by(Reel.id).all()
        return {"reels": [_to_job_dict(reel) for reel in reels]}
    finally:
        db.close()


@app.post("/api/config")
async def save_config(request: Request):
    body = await request.json()
    db = SessionLocal()
    try:
        for key, value in body.items():
            existing = db.query(Config).filter(Config.key == key).first()
            if existing:
                existing.value = str(value)
            else:
                db.add(Config(key=key, value=str(value)))
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/config")
async def get_config():
    db = SessionLocal()
    try:
        configs = db.query(Config).all()
        result = {item.key: item.value for item in configs}
        if "IG_ACCESS_TOKEN" in result:
            token = result["IG_ACCESS_TOKEN"]
            result["IG_ACCESS_TOKEN"] = token[:8] + "..." + token[-4:] if len(token) > 12 else "***"
        return result
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    with open(index_path, encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/health")
async def health():
    return {"status": "ok"}