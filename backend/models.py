
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ---------- ENUMS ----------

class ReelStatus(str, PyEnum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"


class ScheduledPostStatus(str, PyEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(str, PyEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def enum_column(enum_class, name):
    """Store enum values such as 'scheduled', not Python member names."""
    return SQLEnum(
        enum_class,
        name=name,
        native_enum=False,
        values_callable=lambda cls: [item.value for item in cls],
    )


# ---------- INSTAGRAM ACCOUNTS ----------

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instagram_user_id = Column(String(128), nullable=False, unique=True)
    username = Column(String(255), nullable=True)

    # Store an ENCRYPTED token, never a plain-text access token.
    access_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    scheduled_posts = relationship(
        "ScheduledPost", back_populates="account"
    )


# ---------- REELS / VIDEO FILES ----------

class Reel(Base):
    __tablename__ = "reels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)

    original_path = Column(String(512), nullable=False)
    processed_path = Column(String(512), nullable=True)
    thumbnail_path = Column(String(512), nullable=True)

    # Object-storage keys, e.g. Cloudflare R2 keys.
    # These are not local computer paths.
    original_storage_key = Column(String(512), nullable=True)
    processed_storage_key = Column(String(512), nullable=True)
    thumbnail_storage_key = Column(String(512), nullable=True)

    file_size_bytes = Column(BigInteger, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Optional future AI fields; not required by the initial MVP.
    transcript = Column(Text, nullable=True)
    topic = Column(Text, nullable=True)
    hook = Column(Text, nullable=True)

    # User can enter these manually for the first version.
    caption = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=False, default=list)

    status = Column(
        enum_column(JobStatus, "job_status"),
        nullable=False,
        default=JobStatus.PENDING,
    )
    error = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    instagram_media_id = Column(String(128), nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    scheduled_posts = relationship(
        "ScheduledPost", back_populates="reel"
    )


# ---------- SCHEDULED PUBLISHING ----------

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    reel_id = Column(
        Integer, ForeignKey("reels.id"), nullable=False, index=True
    )
    account_id = Column(
        Integer,
        ForeignKey("instagram_accounts.id"),
        nullable=False,
        index=True,
    )

    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        enum_column(ScheduledPostStatus, "scheduled_post_status"),
        nullable=False,
        default=ScheduledPostStatus.PENDING,
        index=True,
    )

    # Instagram's published media ID for this particular post.
    instagram_media_id = Column(String(128), nullable=True)

    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    reel = relationship("Reel", back_populates="scheduled_posts")
    account = relationship(
        "InstagramAccount", back_populates="scheduled_posts"
    )
    jobs = relationship("Job", back_populates="scheduled_post")


# ---------- BACKGROUND JOBS ----------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Examples: extract_zip, validate_video, publish_reel
    job_type = Column(String(64), nullable=False)

    reel_id = Column(Integer, ForeignKey("reels.id"), nullable=True)
    scheduled_post_id = Column(
        Integer, ForeignKey("scheduled_posts.id"), nullable=True
    )

    status = Column(
        enum_column(JobStatus, "job_status"),
        nullable=False,
        default=JobStatus.QUEUED,
        index=True,
    )

    # Optional input data for the worker.
    payload = Column(JSON, nullable=False, default=dict)

    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    run_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    locked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    scheduled_post = relationship("ScheduledPost", back_populates="jobs")

    __table_args__ = (
        Index("ix_jobs_status_run_at", "status", "run_at"),
    )


class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(128), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


__all__ = [
    "Base",
    "Config",
    "InstagramAccount",
    "Job",
    "JobStatus",
    "Reel",
    "ReelStatus",
    "ScheduledPost",
    "ScheduledPostStatus",
]




# from datetime import datetime
# from enum import Enum
# from sqlalchemy import (
#     Column, Integer, String, Text, DateTime, Enum as SQLEnum, ForeignKey, JSON
# )
# from sqlalchemy.orm import relationship, declarative_base

# Base = declarative_base()

# class JobStatus(str, Enum):
#     PENDING = "pending"
#     EXTRACTING = "extracting"
#     TRANSCRIBING = "transcribing"
#     ANALYZING = "analyzing"
#     THUMBNAIL = "thumbnail"
#     HASHTAGS = "hashtags"
#     READY = "ready"
#     SCHEDULED = "scheduled"
#     PUBLISHING = "publishing"
#     PUBLISHED = "published"
#     FAILED = "failed"

# class Reel(Base):
#     __tablename__ = "reels"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     filename = Column(String(255), nullable=False)
#     original_path = Column(String(512), nullable=False)
#     processed_path = Column(String(512), nullable=True)
#     thumbnail_path = Column(String(512), nullable=True)
#     transcript = Column(Text, nullable=True)
#     topic = Column(Text, nullable=True)
#     hook = Column(Text, nullable=True)
#     caption = Column(Text, nullable=True)
#     hashtags = Column(JSON, nullable=True)
#     status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
#     error = Column(Text, nullable=True)
#     scheduled_at = Column(DateTime, nullable=True)
#     published_at = Column(DateTime, nullable=True)
#     instagram_media_id = Column(String(128), nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# class Config(Base):
#     __tablename__ = "config"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     key = Column(String(128), unique=True, nullable=False)
#     value = Column(Text, nullable=True)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    
    