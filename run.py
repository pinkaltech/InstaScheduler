"""Run the Instagram Reel Scheduler backend."""
import uvicorn
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    # Check for .env
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        print(f"[INFO] Loading .env from {env_path}")

    # Check requirements
    req_path = Path(__file__).parent.parent / "requirements.txt"
    if req_path.exists():
        print(f"[INFO] Requirements: {req_path}")

    print("=" * 50)
    print("Starting Instagram Reel Scheduler Backend")
    print("=" * 50)
    print("Website: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Admin: http://localhost:8000")
    print("=" * 50)

    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        access_log=True,
    )