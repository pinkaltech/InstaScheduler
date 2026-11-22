from typing import Optional
from tavily import TavilyClient
from ..config import settings

def search_trending(query: str, max_results: int = 8) -> list[dict]:
    """
    Search Tavily for trending content related to query.
    Returns list of result dicts.
    """
    if not settings.TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY not configured. "
            "Get one at tavily.com and add to .env"
        )

    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    print(f"[Tavily] Searching: {query}")

    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_answer=True,
    )

    results = []
    for item in response.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "content": item.get("content", "")[:500],
            "url": item.get("url", ""),
            "score": item.get("score", 0),
        })

    print(f"[Tavily] Found {len(results)} results")
    return results

def extract_hashtags(transcript: str, topic: str,
                     tavily_results: list[dict]) -> list[str]:
    """
    Use LLM + Tavily research to pick relevant trending hashtags.
    """
    client = get_llm_client()

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
        for r in tavily_results[:5]
    )

    prompt = f"""You are a viral hashtag strategist for AI-generated Instagram Reels.

Given:
- TRANSCRIPT excerpt: {transcript[:500]}
- TOPIC: {topic}
- CURRENT TRENDING SEARCH RESULTS:
{snippets}

Pick 8-12 hashtags that would maximize reach for this reel.
Mix:
- 3-4 VERY broad (#fyp #viral #reels #trending #ai)
- 3-4 topic/niche specific
- 2-3 engagement/community tags

Return ONLY comma-separated hashtags like: #ai #viral #fyp #reels ...
No other text, no explanation."""

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()
    tags = [t.strip() for t in raw.split(",") if t.strip().startswith("#")]

    # Deduplicate preserving order
    seen = set()
    unique = []
    for tag in tags:
        lower = tag.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(tag)

    print(f"[Hashtags] Generated {len(unique)} tags")
    return unique[:12]

def get_llm_client():
    """Lazy import to avoid circular dep."""
    from .analyzer import get_llm_client as _get
    return _get()