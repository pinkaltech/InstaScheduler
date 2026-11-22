from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
    connect_args = {}
else:
    sqlite_path = settings.BASE_DIR / "data" / "app.db"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    connect_args = {"check_same_thread": False}

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db():
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
