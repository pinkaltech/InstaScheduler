import json
from pathlib import Path
from openai import OpenAI
from ..config import settings

_client = None

def get_llm_client():
    """Get OpenAI-compatible client (Groq free tier by default)."""
    global _client
    if _client is None:
        if not settings.LLM_API_KEY:
            raise RuntimeError(
                "LLM_API_KEY not set. Get a free Groq key at groq.com "
                "or set LLM_API_KEY in .env"
            )
        _client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    return _client

# Prompt for generating reel content from transcript + frame description
ANALYZE_PROMPT = """You are a viral Instagram Reel analyst. Given a video transcript,
produce a JSON object with EXACTLY these fields:

{
  "topic": "short topic (3-5 words)",
  "hook": "punchy opening line that grabs attention (1 sentence)",
  "caption": "Instagram caption (2-4 sentences, engaging, include a question)",
  "thumbnail_text": "2-5 words ALL CAPS for thumbnail",
  "keywords": ["list", "of", "5-8", "keywords"],
  "vibe": "motivation|humor|education|drama|inspiration|tips",
  "target_audience": "who this appeals to"
}

Return ONLY valid JSON, no markdown fences, no explanation."""

def analyze_content(transcript: str, frame_path: str = None) -> dict:
    """
    Analyze transcript + frame to generate reel content.
    Returns dict with topic, hook, caption, thumbnail_text, keywords, vibe.
    """
    client = get_llm_client()

    # Read frame for vision analysis if available
    frame_context = ""
    if frame_path and Path(frame_path).exists():
        frame_context = f"Frame image available at: {frame_path}"

    user_prompt = f"""TRANSCRIPT:
{transcript[:3000]}

FRAME CONTEXT:
{frame_context or "No frame provided"}

Analyze this reel content and return JSON."""

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": ANALYZE_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=800,
    )

    raw = response.choices[0].message.content.strip()
    # Clean markdown fences if any
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError as e:
        print(f"[Analyzer] JSON parse error: {e}")
        print(f"[Analyzer] Raw response: {raw[:200]}")
        # Return fallback
        return {
            "topic": "viral reel",
            "hook": "",
            "caption": transcript[:100],
            "thumbnail_text": "WATCH THIS",
            "keywords": ["reel", "viral"],
            "vibe": "tips",
        }