import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    DATABASE_URL: str = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or ""
    print(f"Database URL: {DATABASE_URL}")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    IG_USER_ID: str = os.getenv("IG_USER_ID", "")
    IG_ACCESS_TOKEN: str = os.getenv("IG_ACCESS_TOKEN", "")
    IG_API_VERSION: str = os.getenv("IG_API_VERSION", "v26.0")

    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    WHISPER_LANGUAGE: str | None = os.getenv("WHISPER_LANGUAGE") or None

    POLLINATIONS_ENABLED: bool = os.getenv("POLLINATIONS_ENABLED", "false").lower() == "true"

    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    THUMBNAIL_DIR: Path = BASE_DIR / "data" / "thumbnails"

    def __init__(self):
        for d in (self.UPLOAD_DIR, self.PROCESSED_DIR, self.THUMBNAIL_DIR):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()