import hashlib
import logging
import shutil
import time
from pathlib import Path
from urllib.parse import quote

import requests

from ..config import settings
from ..database import SessionLocal
from ..models import Config

logger = logging.getLogger(__name__)


def _get_config() -> dict:
    db = SessionLocal()
    try:
        configs = {c.key: c.value for c in db.query(Config).all()}
    finally:
        db.close()

    return {
        "IG_USER_ID": configs.get("IG_USER_ID", settings.IG_USER_ID),
        "IG_ACCESS_TOKEN": configs.get("IG_ACCESS_TOKEN", settings.IG_ACCESS_TOKEN),
        "IG_API_VERSION": configs.get("IG_API_VERSION", settings.IG_API_VERSION),
        "PUBLIC_BASE_URL": configs.get("PUBLIC_BASE_URL", settings.PUBLIC_BASE_URL),
    }


def _public_asset_path(source: Path, target_dir: Path) -> Path:
    identity = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:16]
    return target_dir / f"{source.stem}-{identity}{source.suffix}"


def _copy_to_public_dir(local_path: str, target_dir: Path) -> str:
    source = Path(local_path)
    if not source.exists():
        raise FileNotFoundError(f"File not found: {local_path}")

    target_dir.mkdir(parents=True, exist_ok=True)
    destination = _public_asset_path(source, target_dir)
    shutil.copy2(source, destination)

    public_base = _get_config()["PUBLIC_BASE_URL"].rstrip("/")
    return f"{public_base}/{target_dir.name}/{quote(destination.name)}"


def get_video_url(local_path: str) -> str:
    return _copy_to_public_dir(local_path, settings.PROCESSED_DIR)


def get_thumbnail_url(local_path: str) -> str:
    return _copy_to_public_dir(local_path, settings.THUMBNAIL_DIR)


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _remove_managed_file(path: Path, directory: Path) -> None:
    if not _is_within(path, directory):
        logger.warning("Skipped cleanup for path outside %s: %s", directory, path)
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove published asset: %s", path)


def cleanup_published_files(video_path: str, thumbnail_path: str | None) -> None:
    """Remove local inputs and public copies after Instagram confirms publication."""
    assets = [
        (Path(video_path), settings.UPLOAD_DIR / "extracted", settings.PROCESSED_DIR),
    ]
    if thumbnail_path:
        assets.append((Path(thumbnail_path), settings.THUMBNAIL_DIR, settings.THUMBNAIL_DIR))

    for source, source_root, public_root in assets:
        public_copy = _public_asset_path(source, public_root)
        _remove_managed_file(source, source_root)
        _remove_managed_file(public_copy, public_root)


def create_container(video_path: str, caption: str, thumbnail_path: str | None = None) -> str:
    cfg = _get_config()
    print(cfg)
    uid = cfg["IG_USER_ID"]
    token = cfg["IG_ACCESS_TOKEN"]

    if not uid or not token:
        raise RuntimeError("Instagram credentials not configured. Set IG_USER_ID and IG_ACCESS_TOKEN in .env or via /api/config")

    if thumbnail_path is None:
        candidate = Path(video_path).with_suffix(".jpg")
        if not candidate.exists():
            candidate = Path(video_path).with_suffix(".png")
        if candidate.exists():
            thumbnail_path = str(candidate)

    if not thumbnail_path:
        raise ValueError("A thumbnail path is required for Instagram Reel publishing.")

    video_url = get_video_url(video_path)
    thumbnail_url = get_thumbnail_url(thumbnail_path)

    data = {
        "media_type": "REELS",
        "video_url": video_url,
        "cover_url": thumbnail_url,
        "caption": caption,
        "share_to_feed": "true",
    }

    print("[Instagram] Video URL:", video_url)
    print("[Instagram] Thumbnail URL:", thumbnail_url)
    print(DeprecationWarning("This feature is deprecated and will be removed in a future version."))
    resp = requests.post(
        f"https://graph.instagram.com/v26.0/{uid}/media",
        data=data,
        params={"access_token": token},
        timeout=180,
    )

    print("[Instagram] Create response:", resp.status_code)
    print("[Instagram] Create body:", resp.text)

    if resp.status_code >= 400:
        raise RuntimeError(f"Instagram container creation failed: {resp.status_code} {resp.text}")

    container_id = resp.json().get("id")
    if not container_id:
        raise RuntimeError(f"Instagram did not return a container ID: {resp.text}")

    print(f"[Instagram] Container created: {container_id}")
    return container_id


def get_container_status(container_id: str) -> dict:
    cfg = _get_config()
    resp = requests.get(
        f"https://graph.instagram.com/v26.0/{container_id}",
        params={"fields": "status_code,status", "access_token": cfg["IG_ACCESS_TOKEN"]},
        timeout=60,
    )
    print("[Instagram] Status:", resp.status_code)
    print("[Instagram] Status body:", resp.text)
    resp.raise_for_status()
    return resp.json()


def publish_container(container_id: str) -> dict:
    cfg = _get_config()
    resp = requests.post(
        f"https://graph.instagram.com/v26.0/{cfg['IG_USER_ID']}/media_publish",
        data={"creation_id": container_id},
        params={"access_token": cfg["IG_ACCESS_TOKEN"]},
        timeout=180,
    )

    print("[Instagram] Publish status:", resp.status_code)
    print("[Instagram] Publish body:", resp.text)

    if resp.status_code >= 400:
        raise RuntimeError(f"Instagram publish failed: {resp.status_code} {resp.text}")

    return resp.json()


def publish_reel(video_path: str, caption: str, thumbnail_path: str | None = None, max_wait: int = 300) -> dict:
    container_id = create_container(video_path, caption, thumbnail_path=thumbnail_path)
    deadline = time.time() + max_wait

    while time.time() < deadline:
        status = get_container_status(container_id)
        code = status.get("status_code", "")
        print(f"[Instagram] Container status: {code}")

        if code == "FINISHED":
            return publish_container(container_id)
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container failed: {status}")
        time.sleep(5)

    raise TimeoutError(f"Timed out waiting for container {container_id}")


__all__ = [
    "create_container",
    "cleanup_published_files",
    "get_container_status",
    "get_thumbnail_url",
    "get_video_url",
    "publish_container",
    "publish_reel",
]