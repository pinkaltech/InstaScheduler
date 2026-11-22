import json
import ollama


MODEL = "llama3.2-vision"


def analyze_reel(frames: list[str], transcript: str):

    prompt = f"""
You are an expert Instagram Reels content analyst.

Analyze the provided Reel frames together with
the transcript.

TRANSCRIPT:
{transcript}

Your job is to understand what this Reel is about.

Generate:

1. topic
2. target audience
3. main idea
4. strongest hook
5. short thumbnail text
6. thumbnail visual concept
7. Instagram caption
8. keywords

IMPORTANT:

Thumbnail text:
- maximum 7 words
- attention grabbing
- natural English
- suitable for a modern technology/AI Reel
- don't use fake claims
- don't promise virality

Caption:
- 2 to 4 short paragraphs
- natural Instagram style
- explain the actual Reel
- engaging but not spammy
- DO NOT generate hashtags

Return ONLY valid JSON.

Format:

{{
    "topic": "...",
    "target_audience": "...",
    "main_idea": "...",
    "hook": "...",
    "thumbnail_text": "...",
    "thumbnail_visual_concept": "...",
    "caption": "...",
    "keywords": []
}}
"""

    message = {"role": "user", "content": prompt, "images": frames}

    response = ollama.chat(model=MODEL, messages=[message])

    text = response["message"]["content"]

    # Remove accidental markdown fences
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


json_dict = analyze_reel()
