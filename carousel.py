"""
carousel.py — 3-Slide Carousel Generator
AI with Abdullah — Dark Orange Theme
Generates professional Facebook carousel images using Pillow only (zero API cost)
"""

import io
import re
import textwrap
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─────────────────────────────────────────────────────────────────────────────
#  BRAND COLORS — Dark Orange Theme
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK       = (13,  13,  13)      # Near black background
BG_CARD       = (22,  22,  22)      # Slightly lighter card bg
ORANGE_PRIMARY = (255, 107, 43)     # #FF6B2B — main orange
ORANGE_LIGHT  = (255, 154,  92)     # #FF9A5C — light orange
ORANGE_GLOW   = (255, 107,  43, 40) # Transparent glow
WARM_WHITE    = (245, 237, 214)     # #F5EDD6 — warm white
WARM_GRAY     = (160, 150, 135)     # Muted warm gray for secondary text
DARK_ORANGE_BG = (35,  18,   8)     # Very dark orange tint for accents

SIZE = (1080, 1080)
PAGE_NAME = "AI with Abdullah"

# ─────────────────────────────────────────────────────────────────────────────
#  FONT LOADER
# ─────────────────────────────────────────────────────────────────────────────
FONT_PATHS = {
    "bold":    ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
    "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
}

def load_font(style: str = "bold", size: int = 48) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS.get(style, FONT_PATHS["regular"]):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    """Remove hashtags, emojis, extra spaces."""
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.ellipse([x0, y0, x0 + radius * 2, y0 + radius * 2], fill=fill)
    draw.ellipse([x1 - radius * 2, y0, x1, y0 + radius * 2], fill=fill)
    draw.ellipse([x0, y1 - radius * 2, x0 + radius * 2, y1], fill=fill)
    draw.ellipse([x1 - radius * 2, y1 - radius * 2, x1, y1], fill=fill)


def draw_base(draw: ImageDraw.Draw, w: int, h: int):
    """Draw dark background with subtle orange corner glow."""
    draw.rectangle([0, 0, w, h], fill=BG_DARK)
    # Subtle top-right orange glow
    for i in range(180, 0, -20):
        alpha = max(4, i // 8)
        draw.ellipse([w - i * 2, -i, w + i, i * 2],
                     fill=(*ORANGE_PRIMARY, alpha))
    # Bottom-left subtle glow
    for i in range(120, 0, -20):
        alpha = max(3, i // 10)
        draw.ellipse([-i, h - i, i * 2, h + i],
                     fill=(*ORANGE_LIGHT, alpha))


def draw_brand_bar(draw: ImageDraw.Draw, w: int, h: int):
    """Orange bottom brand bar with page name."""
    bar_h = 72
    draw.rectangle([0, h - bar_h, w, h], fill=ORANGE_PRIMARY)
    # Page name
    font = load_font("bold", 28)
    page_bbox = draw.textbbox((0, 0), PAGE_NAME, font=font)
    page_w = page_bbox[2] - page_bbox[0]
    draw.text(
        ((w - page_w) // 2, h - bar_h + (bar_h - 28) // 2),
        PAGE_NAME, font=font, fill=BG_DARK
    )


def draw_slide_counter(draw: ImageDraw.Draw, w: int, current: int, total: int):
    """Draw slide dots at top right."""
    dot_r = 6
    gap = 20
    total_w = total * dot_r * 2 + (total - 1) * gap
    start_x = w - total_w - 40
    y = 42
    for i in range(total):
        x = start_x + i * (dot_r * 2 + gap)
        color = ORANGE_PRIMARY if i == current else WARM_GRAY
        draw.ellipse([x, y - dot_r, x + dot_r * 2, y + dot_r], fill=color)


def draw_orange_line(draw: ImageDraw.Draw, x: int, y: int, length: int, thickness: int = 4):
    """Draw a horizontal orange accent line."""
    draw.rectangle([x, y, x + length, y + thickness], fill=ORANGE_PRIMARY)


def wrap_text(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list:
    """Word-wrap text to fit max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ─────────────────────────────────────────────────────────────────────────────
#  SLIDE 1 — HOOK SLIDE
# ─────────────────────────────────────────────────────────────────────────────
def make_slide_1_hook(hook_text: str, niche: str) -> bytes:
    """
    Bold hook statement slide.
    Large centered text, orange accent, niche tag.
    """
    img  = Image.new("RGB", SIZE, BG_DARK)
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = SIZE

    draw_base(draw, w, h)

    # Niche tag — top left pill
    niche_clean = clean_text(niche)
    font_tag = load_font("bold", 24)
    tag_bbox = draw.textbbox((0, 0), niche_clean.upper(), font=font_tag)
    tag_w = tag_bbox[2] - tag_bbox[0] + 32
    draw_rounded_rect(draw, (44, 44, 44 + tag_w, 44 + 40), 20,
                      fill=DARK_ORANGE_BG)
    draw.rectangle([44, 44, 48, 84], fill=ORANGE_PRIMARY)  # left accent
    draw.text((60, 52), niche_clean.upper(), font=font_tag, fill=ORANGE_LIGHT)

    # Slide counter
    draw_slide_counter(draw, w, 0, 3)

    # Big quote marks
    font_quote = load_font("bold", 180)
    draw.text((36, 140), "\u201c", font=font_quote,
              fill=(*ORANGE_PRIMARY, 35))

    # Hook text — large, centered
    hook_clean = clean_text(hook_text)
    font_hook = load_font("bold", 58)
    font_hook_sm = load_font("bold", 48)

    # Try to fit in 2-3 lines
    max_w = w - 100
    lines = wrap_text(hook_clean, font_hook, max_w, draw)
    if len(lines) > 3:
        lines = wrap_text(hook_clean, font_hook_sm, max_w, draw)
        font_use = font_hook_sm
    else:
        font_use = font_hook

    line_h = 75
    total_h = len(lines) * line_h
    start_y = (h - total_h) // 2 - 40

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_use)
        lw   = bbox[2] - bbox[0]
        x    = (w - lw) // 2
        y    = start_y + i * line_h
        # Orange on first line, warm white on rest
        color = ORANGE_PRIMARY if i == 0 else WARM_WHITE
        # Shadow
        draw.text((x + 2, y + 2), line, font=font_use,
                  fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font_use, fill=color)

    # Orange accent line below text
    line_y = start_y + total_h + 20
    draw_orange_line(draw, (w - 120) // 2, line_y, 120, 5)

    # "Swipe to read more →" hint
    font_hint = load_font("regular", 26)
    hint = "Swipe to read more \u2192"
    hint_bbox = draw.textbbox((0, 0), hint, font=font_hint)
    hint_w = hint_bbox[2] - hint_bbox[0]
    draw.text(((w - hint_w) // 2, h - 130),
              hint, font=font_hint, fill=WARM_GRAY)

    draw_brand_bar(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  SLIDE 2 — CONTENT SLIDE
# ─────────────────────────────────────────────────────────────────────────────
def make_slide_2_content(body_text: str) -> bytes:
    """
    Content/value slide with numbered points.
    Extracts key lines from body and presents as a list.
    """
    img  = Image.new("RGB", SIZE, BG_DARK)
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = SIZE

    draw_base(draw, w, h)
    draw_slide_counter(draw, w, 1, 3)

    # Section title
    font_title = load_font("bold", 34)
    draw.text((54, 54), "KEY INSIGHTS", font=font_title, fill=ORANGE_PRIMARY)
    draw_orange_line(draw, 54, 100, 160, 4)

    # Extract content lines — clean and split
    clean = clean_text(body_text)
    raw_lines = [l.strip() for l in body_text.split("\n") if l.strip()]
    # Filter out hashtag lines and very short lines
    content_lines = []
    for l in raw_lines:
        cl = clean_text(l)
        if len(cl) > 15 and not cl.startswith("#"):
            content_lines.append(cl)
    content_lines = content_lines[:5]  # Max 5 points

    font_num  = load_font("bold", 42)
    font_body = load_font("regular", 34)
    font_body_sm = load_font("regular", 28)

    y = 140
    padding_x = 54
    max_text_w = w - padding_x - 100

    for i, line in enumerate(content_lines):
        if y > h - 160:
            break

        num_str = str(i + 1)

        # Number circle
        circle_r = 28
        cx, cy = padding_x + circle_r, y + circle_r
        draw.ellipse(
            [cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r],
            fill=ORANGE_PRIMARY
        )
        nb = draw.textbbox((0, 0), num_str, font=load_font("bold", 26))
        nw = nb[2] - nb[0]
        draw.text((cx - nw // 2, cy - 14), num_str,
                  font=load_font("bold", 26), fill=BG_DARK)

        # Text next to number
        text_x = padding_x + circle_r * 2 + 20
        text_w  = w - text_x - 40
        wrapped = wrap_text(line, font_body, text_w, draw)
        if len(wrapped) > 2:
            wrapped = wrap_text(line, font_body_sm, text_w, draw)
            fnt = font_body_sm
            lh  = 38
        else:
            fnt = font_body
            lh  = 46

        for j, wl in enumerate(wrapped[:2]):
            col = WARM_WHITE if j == 0 else WARM_GRAY
            draw.text((text_x, y + j * lh), wl, font=fnt, fill=col)

        block_h = max(circle_r * 2, len(wrapped[:2]) * lh) + 24
        y += block_h

        # Separator line (not after last)
        if i < len(content_lines) - 1:
            draw.rectangle(
                [padding_x, y - 10, w - padding_x, y - 8],
                fill=(*WARM_GRAY, 30)
            )

    draw_brand_bar(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  SLIDE 3 — CTA SLIDE
# ─────────────────────────────────────────────────────────────────────────────
def make_slide_3_cta(cta_text: str) -> bytes:
    """
    CTA slide — bold call to action with follow prompt.
    Full orange accent design.
    """
    img  = Image.new("RGB", SIZE, BG_DARK)
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = SIZE

    draw_base(draw, w, h)
    draw_slide_counter(draw, w, 2, 3)

    # Large orange circle background — centered
    for r in range(320, 0, -40):
        alpha = max(5, r // 15)
        draw.ellipse(
            [(w - r) // 2, (h - r) // 2,
             (w + r) // 2, (h + r) // 2],
            fill=(*ORANGE_PRIMARY, alpha)
        )

    # "Take Action" label
    font_label = load_font("bold", 26)
    label = "TAKE ACTION"
    lb = draw.textbbox((0, 0), label, font=font_label)
    lw = lb[2] - lb[0]
    draw.text(((w - lw) // 2, 200), label, font=font_label, fill=ORANGE_LIGHT)
    draw_orange_line(draw, (w - 80) // 2, 238, 80, 3)

    # Main CTA text
    cta_clean = clean_text(cta_text)
    # Trim to first 2 sentences
    sentences = cta_clean.replace("!", ".").replace("?", ".").split(".")
    cta_short = ". ".join(s.strip() for s in sentences[:2] if s.strip())
    if not cta_short:
        cta_short = cta_clean[:100]

    font_cta = load_font("bold", 48)
    font_cta_sm = load_font("bold", 38)
    max_w = w - 100

    lines = wrap_text(cta_short, font_cta, max_w, draw)
    if len(lines) > 3:
        lines = wrap_text(cta_short, font_cta_sm, max_w, draw)
        fnt = font_cta_sm
        lh  = 58
    else:
        fnt = font_cta
        lh  = 68

    total_h = len(lines) * lh
    start_y = (h - total_h) // 2 - 20

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=fnt)
        lw2  = bbox[2] - bbox[0]
        x    = (w - lw2) // 2
        y    = start_y + i * lh
        draw.text((x + 2, y + 2), line, font=fnt, fill=(0, 0, 0, 100))
        draw.text((x, y), line, font=fnt,
                  fill=ORANGE_PRIMARY if i == 0 else WARM_WHITE)

    # Follow button pill
    follow_text = "Follow AI with Abdullah \u2192"
    font_follow = load_font("bold", 30)
    fb = draw.textbbox((0, 0), follow_text, font=font_follow)
    fw = fb[2] - fb[0]
    pill_pad = 30
    pill_x0 = (w - fw - pill_pad * 2) // 2
    pill_y0 = h - 200
    draw_rounded_rect(
        draw,
        (pill_x0, pill_y0, pill_x0 + fw + pill_pad * 2, pill_y0 + 62),
        31,
        fill=ORANGE_PRIMARY
    )
    draw.text((pill_x0 + pill_pad, pill_y0 + 16),
              follow_text, font=font_follow, fill=BG_DARK)

    draw_brand_bar(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN — Generate 3 slides from post text
# ─────────────────────────────────────────────────────────────────────────────
def generate_carousel(post_text: str, niche: str) -> list[bytes]:
    """
    Split post text into 3 parts and generate carousel slides.
    Returns list of 3 JPEG bytes objects.
    """
    # Split post into sections
    paragraphs = [p.strip() for p in post_text.split("\n\n") if p.strip()]

    if len(paragraphs) >= 3:
        hook_text = paragraphs[0]
        body_text = "\n\n".join(paragraphs[1:-1])
        cta_text  = paragraphs[-1]
    elif len(paragraphs) == 2:
        hook_text = paragraphs[0]
        body_text = paragraphs[1]
        cta_text  = "Follow AI with Abdullah for daily AI insights!"
    else:
        lines = post_text.split("\n")
        hook_text = lines[0] if lines else post_text
        body_text = "\n".join(lines[1:-1]) if len(lines) > 2 else lines[0]
        cta_text  = lines[-1] if len(lines) > 1 else "Follow for more!"

    slide1 = make_slide_1_hook(hook_text, niche)
    slide2 = make_slide_2_content(body_text or post_text)
    slide3 = make_slide_3_cta(cta_text)

    return [slide1, slide2, slide3]
