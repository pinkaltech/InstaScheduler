from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _safe_font(size: int):
    candidates = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def generate_thumbnail(frame_path: str, text: str, output_path: str, ai_prompt: str | None = None, settings=None) -> str:
    """Create a simple, reliable Reel thumbnail without extra AI models."""
    frame = Image.open(frame_path).convert("RGB")
    frame = frame.resize((1080, 1920), Image.LANCZOS)

    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 120))
    base = Image.alpha_composite(frame.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(base)
    headline = (text or "REEL").upper()

    title_font = _safe_font(110)
    badge_font = _safe_font(38)

    dark_bar = Image.new("RGBA", (1080, 260), (0, 0, 0, 170))
    base.paste(dark_bar, (0, 700), dark_bar)

    draw.rounded_rectangle((70, 760, 1010, 1200), radius=30, fill=(15, 15, 15, 180))
    draw.rounded_rectangle((110, 720, 270, 760), radius=12, fill=(255, 79, 79, 220))
    draw.text((130, 735), "REEL", font=badge_font, fill=(255, 255, 255, 255))

    wrapped = []
    current = ""
    for word in headline.split():
        candidate = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), candidate, font=title_font)[2]
        if width <= 900:
            current = candidate
        else:
            if current:
                wrapped.append(current)
            current = word
    if current:
        wrapped.append(current)

    y = 820
    for line in wrapped[:3]:
        draw.text((120, y), line, font=title_font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 200))
        y += 120

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output, "JPEG", quality=92, optimize=True)
    return str(output)


__all__ = ["generate_thumbnail"]