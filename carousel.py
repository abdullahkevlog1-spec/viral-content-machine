"""
carousel.py — 3-Slide Carousel Generator
Modern warm light editorial theme optimized for readable social carousels.
"""

import io
import re
from PIL import Image, ImageDraw, ImageFont

BG_DARK = (250, 246, 238)
BG_CARD = (255, 255, 255)
ORANGE_PRIMARY = (230, 114, 44)
ORANGE_LIGHT = (245, 160, 90)
WARM_WHITE = (35, 35, 35)
WARM_GRAY = (110, 110, 110)
DARK_ORANGE_BG = (255, 239, 224)

SIZE = (1080, 1080)
PAGE_NAME = "AI with Abdullah"

FONT_PATHS = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def load_font(style="bold", size=48):
    for path in FONT_PATHS.get(style, FONT_PATHS["regular"]):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def clean_text(text):
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def wrap(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def quality_score_visual(text):
    score = 60
    wc = len(text.split())
    if wc <= 20:
        score += 15
    if any(x in text.lower() for x in ["how", "why", "secret", "mistake", "before"]):
        score += 15
    return min(100, score)


def create_slide(text, subtitle=""):
    img = Image.new("RGB", SIZE, BG_DARK)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    title_font = load_font("bold", 72)
    body_font = load_font("regular", 42)
    small_font = load_font("bold", 28)

    cleaned = clean_text(text)
    lines = wrap(draw, cleaned, title_font, 880)
    if len(lines) > 4:
        title_font = load_font("bold", 58)
        lines = wrap(draw, cleaned, title_font, 880)

    y = 180
    for i, line in enumerate(lines[:4]):
        color = ORANGE_PRIMARY if i == 0 else WARM_WHITE
        draw.text((100, y), line, font=title_font, fill=color)
        y += 100

    if subtitle:
        sub_lines = wrap(draw, subtitle, body_font, 850)
        for line in sub_lines[:3]:
            draw.text((100, y + 30), line, font=body_font, fill=WARM_GRAY)
            y += 55

    draw.rectangle([80, 900, 1000, 905], fill=ORANGE_PRIMARY)
    draw.text((100, 940), PAGE_NAME, font=small_font, fill=WARM_GRAY)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def generate_carousel(post_text: str, niche: str):
    paragraphs = [p.strip() for p in post_text.split("\n\n") if p.strip()]

    hook = paragraphs[0] if paragraphs else post_text
    body = paragraphs[1] if len(paragraphs) > 1 else "Save this post and follow for more insights"
    cta = paragraphs[-1] if len(paragraphs) > 2 else "Comment your thoughts below"

    if quality_score_visual(hook) < 70:
        hook = f"Before you ignore this... {hook}"

    slide1 = create_slide(hook, niche)
    slide2 = create_slide(body, "Key takeaway")
    slide3 = create_slide(cta, "Follow for more")

    return [slide1, slide2, slide3]
