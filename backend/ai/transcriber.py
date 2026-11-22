import threading
from pathlib import Path

# Global Whisper model cache
_whisper_lock = threading.Lock()
_whisper_model = None

def load_transcriber(model_name: str = "base"):
    """Lazy-load Whisper model."""
    global _whisper_model, _whisper_lock
    with _whisper_lock:
        if _whisper_model is None:
            try:
                import whisper
                _whisper_model = whisper.load_model(model_name)
                print(f"[Transcriber] Whisper model '{model_name}' loaded.")
            except Exception as e:
                raise RuntimeError(f"Failed to load Whisper: {e}")
        return _whisper_model

def transcribe_audio(audio_path: Path, model_name: str = "base", language: str = None) -> dict:
    """
    Transcribe audio using local Whisper (free, no API key).
    Returns dict with 'text', 'segments', 'language'.
    """
    model = load_transcriber(model_name)

    kwargs = {}
    if language:
        kwargs["language"] = language

    print(f"[Transcriber] Transcribing {audio_path.name}...")
    result = model.transcribe(str(audio_path), **kwargs)

    print(f"[Transcriber] Done. Language: {result.get('language')}, "
          f"Text length: {len(result.get('text', ''))}")
    return result