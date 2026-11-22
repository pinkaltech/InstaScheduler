"""
Background Scheduler — polls DB every interval and publishes due reels.
"""
import time
import threading
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

from ..models import Reel, JobStatus
from ..database import SessionLocal
from ..instagram import publisher as ig_publisher

DEFAULT_INTERVAL_HOURS = 3


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def auto_schedule_reel(reel_id: int) -> datetime | None:
    """Schedule a newly processed reel in the automatic publishing queue."""
    db = SessionLocal()
    try:
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if not reel or reel.status != JobStatus.READY or reel.scheduled_at is not None:
            return None

        latest_scheduled = db.query(func.max(Reel.scheduled_at)).filter(
            Reel.scheduled_at.isnot(None),
            Reel.status.in_([JobStatus.SCHEDULED, JobStatus.PUBLISHING]),
        ).scalar()
        latest_published = db.query(func.max(Reel.published_at)).filter(
            Reel.published_at.isnot(None),
            Reel.status == JobStatus.PUBLISHED,
        ).scalar()

        last_publish_time = max(
            (_as_utc(value) for value in (latest_scheduled, latest_published) if value),
            default=None,
        )
        now = datetime.now(timezone.utc)
        publish_time = (
            max(now, last_publish_time + timedelta(hours=DEFAULT_INTERVAL_HOURS))
            if last_publish_time
            else now
        )

        reel.scheduled_at = publish_time
        reel.status = JobStatus.SCHEDULED
        db.commit()
        print(f"[Scheduler] Reel {reel_id} automatically scheduled for {publish_time}")
        return publish_time
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def auto_schedule_ready_reels() -> list[int]:
    """Add every ready, unscheduled reel to the automatic queue."""
    db = SessionLocal()
    try:
        reel_ids = [
            reel_id
            for (reel_id,) in db.query(Reel.id)
            .filter(Reel.status == JobStatus.READY, Reel.scheduled_at.is_(None))
            .order_by(Reel.id)
            .all()
        ]
    finally:
        db.close()

    scheduled_ids = []
    for reel_id in reel_ids:
        if auto_schedule_reel(reel_id) is not None:
            scheduled_ids.append(reel_id)
    return scheduled_ids


def schedule_reel(reel_id: int, publish_time: datetime):
    """Schedule a reel to be published at publish_time."""
    db = SessionLocal()
    try:
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if reel:
            reel.scheduled_at = _as_utc(publish_time)
            reel.status = JobStatus.SCHEDULED
            db.commit()
            print(f"[Scheduler] Reel {reel_id} scheduled for {publish_time}")
    finally:
        db.close()

def schedule_batch(reel_ids: list, base_time: datetime, interval_hours: float = 3):
    """Schedule multiple reels across a day."""
    for i, rid in enumerate(reel_ids):
        publish_time = base_time + timedelta(hours=interval_hours * i)
        print(f"[Scheduler] Publish Time for Reel {rid}: {publish_time}")
        schedule_reel(rid, publish_time)

def _process_due_reels():
    """Check DB for due reels and publish them."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = db.query(Reel).filter(
            Reel.scheduled_at <= now,
            Reel.status.in_([JobStatus.SCHEDULED, JobStatus.READY])
        ).all()

        for reel in due:
            try:
                print(f"[Scheduler] Publishing Reel {reel.id}...")
                reel.status = JobStatus.PUBLISHING
                db.commit()

                caption = reel.caption or ""
                if reel.hashtags:
                    caption += "\n\n" + " ".join(reel.hashtags)

                result = ig_publisher.publish_reel(
                    reel.original_path,
                    caption,
                    thumbnail_path=reel.thumbnail_path,
                )

                reel.status = JobStatus.PUBLISHED
                reel.published_at = datetime.now(timezone.utc)
                reel.instagram_media_id = result.get("id")
                db.commit()
                ig_publisher.cleanup_published_files(
                    reel.original_path, reel.thumbnail_path
                )
                print(f"[Scheduler] Reel {reel.id} published successfully!")

            except Exception as e:
                print(f"[Scheduler] Failed Reel {reel.id}: {e}")
                reel.status = JobStatus.FAILED
                reel.error = str(e)
                db.commit()
    finally:
        db.close()

def scheduler_loop(interval_seconds: int = 15):
    """Background loop: check for due reels every N seconds."""
    print(f"[Scheduler] Started. Checking every {interval_seconds}s...")
    while True:
        try:
            _process_due_reels()
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
        time.sleep(interval_seconds)

def start_scheduler(interval: int = 15):
    """Start scheduler in background thread."""
    t = threading.Thread(target=scheduler_loop, args=(interval,), daemon=True)
    t.start()
    print(f"[Scheduler] Background thread started.")
    return t

__all__ = [
    "auto_schedule_ready_reels",
    "auto_schedule_reel",
    "schedule_reel",
    "schedule_batch",
    "start_scheduler",
    "_process_due_reels",
]