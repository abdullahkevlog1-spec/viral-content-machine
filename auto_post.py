"""
auto_post.py — Standalone scheduler for GitHub Actions
Runs independently of Streamlit. No UI needed.
Called by .github/workflows/auto_post.yml on cron schedule.

Usage:
    python auto_post.py --slot morning    # 9 AM post
    python auto_post.py --slot afternoon  # 2 PM post
    python auto_post.py --slot evening    # 9 PM post

Secrets required (GitHub Actions Secrets):
    GROQ_API_KEY       — from console.groq.com
    FB_PAGE_TOKEN      — Facebook Page Access Token
    FB_PAGE_ID         — Facebook Page ID
"""

import os
import sys
import json
import random
import argparse
import requests
import urllib.parse
import re
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG — 3 daily slots
# ─────────────────────────────────────────────────────────────────────────────
SLOTS = {
    "morning": {
        "label":     "🌅 Subah 9:00 AM",
        "niche":     "AI & Tech",
        "hook_id":   "curiosity",
        "tone":      7,
        "variation": "Bold/Controversial",
        "language":  "English",
    },
    "afternoon": {
        "label":     "☀️ Dopahar 2:00 PM",
        "niche":     "Motivation",
        "hook_id":   "bold_claim",
        "tone":      8,
        "variation": "Bold/Controversial",
        "language":  "Roman Urdu",
    },
    "evening": {
        "label":     "🌙 Raat 9:00 PM",
        "niche":     "ASMR / Satisfying",
        "hook_id":   "relatable_pain",
        "tone":      5,
        "variation": "Emotional",
        "language":  "Hinglish",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  GROQ CONFIG
# ─────────────────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

HOOKS = {
    "curiosity":       {"name": "🔍 Curiosity Gap",       "psychology": "Brain is compelled to close open information loops"},
    "bold_claim":      {"name": "⚡ Bold Claim",           "psychology": "Pattern interrupt forces the brain to stop scrolling"},
    "relatable_pain":  {"name": "💔 Relatable Pain",      "psychology": "Mirror neurons fire when people feel deeply understood"},
    "controversy":     {"name": "🔥 Controversy",         "psychology": "Challenges beliefs, triggers debate and strong reactions"},
    "fear_loss":       {"name": "😨 Fear / Loss",         "psychology": "Loss aversion is 2x stronger than desire to gain"},
    "authority_data":  {"name": "🎓 Authority + Data",    "psychology": "Authority bias boosts credibility instantly"},
    "story_hook":      {"name": "📖 Story Hook",          "psychology": "Humans are wired to follow narrative arcs"},
    "shocking_stat":   {"name": "📊 Shocking Statistic",  "psychology": "Creates social comparison and urgency"},
}

LANGUAGE_INSTRUCTIONS = {
    "English": "Write the ENTIRE post in clear, punchy English.",
    "Roman Urdu": """Write the ENTIRE post in Roman Urdu (Urdu words written in English letters).
Example: "Yaar, kya tumne kabhi socha hai ke AI tera kaam chheen sakti hai?"
Every word must be Roman Urdu. Do NOT mix English sentences.""",
    "Hinglish": """Write the ENTIRE post in Hinglish (natural Hindi/Urdu + English mix).
Example: "Bhai, AI ne seriously sab kuch change kar diya hai."
Sound like a smart Pakistani/Indian friend texting.""",
}

NICHE_HASHTAGS = {
    "AI & Tech":         "#AI #ArtificialIntelligence #Tech #ChatGPT #MachineLearning",
    "Motivation":        "#Motivation #Success #Pakistan #Growth #Mindset",
    "ASMR / Satisfying": "#ASMR #Satisfying #Relaxing #Aesthetic #Vibes",
}

BANNED_PHRASES = [
    "stay motivated", "work hard every day", "never give up", "believe in yourself",
    "just keep going", "you can do it", "dream big", "hustle every day",
    "be positive", "success is a journey", "be the best version of yourself",
    "in today's world", "game changer", "think outside the box",
    "the future is bright", "most people don't realize", "it's no secret",
    "at the end of the day", "as we all know",
]

# ─────────────────────────────────────────────────────────────────────────────
#  CONTENT GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def build_prompt(slot: dict) -> str:
    hook     = HOOKS.get(slot["hook_id"], HOOKS["curiosity"])
    lang_ins = LANGUAGE_INSTRUCTIONS.get(slot["language"], LANGUAGE_INSTRUCTIONS["English"])
    hashtags = NICHE_HASHTAGS.get(slot["niche"], "#AI #Tech #Pakistan")
    banned   = ", ".join(f'"{p}"' for p in BANNED_PHRASES[:12])

    return f"""You are an elite viral Facebook content strategist.

LANGUAGE — CRITICAL:
{lang_ins}

PARAMETERS:
- Niche: {slot['niche']}
- Hook Style: {hook['name']} — {hook['psychology']}
- Variation: {slot['variation']}
- Tone Level: {slot['tone']}/10 (1=safe, 10=aggressive/provocative)

POST STRUCTURE — 4 parts, blank line between each:

[HOOK] — One scroll-stopping line using {hook['name']} psychology
[VALUE] — 2-3 short lines with real insight. One idea per line.
[PUNCH] — 1-2 lines hitting from a fresh angle
[CTA] — One natural call to action. End with: {hashtags}

RULES:
1. Return ONLY the post text. No labels. No preamble.
2. Max 12 words per line. Short = mobile-friendly.
3. 2-5 emojis used naturally.
4. BANNED (instant fail): {banned}
5. Do NOT start with "In today's", "The truth is", "Most people".
6. Be SPECIFIC. Generic = fail. Rewrite until it feels fresh.

Write now. Start with the hook:"""


def is_generic(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in BANNED_PHRASES)


def is_too_short(text: str) -> bool:
    return len(text.strip()) < 150


def generate_post(slot: dict, api_key: str, max_retries: int = 4) -> str | None:
    for attempt in range(max_retries):
        temp = round(0.82 + attempt * 0.07, 2)
        try:
            r = requests.post(
                GROQ_API_URL,
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": build_prompt(slot)}],
                    "temperature": temp,
                    "max_tokens": 600,
                    "top_p": 0.92,
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if r.status_code != 200:
                print(f"  Groq error {r.status_code}: {r.text[:100]}")
                continue
            text = r.json()["choices"][0]["message"]["content"].strip()
            if is_too_short(text):
                print(f"  Attempt {attempt+1}: too short ({len(text)} chars) — retrying")
                continue
            if is_generic(text):
                print(f"  Attempt {attempt+1}: generic detected — retrying")
                continue
            return text
        except Exception as e:
            print(f"  Attempt {attempt+1} exception: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  IMAGE GENERATION
# ─────────────────────────────────────────────────────────────────────────────
NICHE_BASE_STYLES = {
    "AI & Tech":         "dark dramatic tech aesthetic, glowing neon blue and purple circuits, cinematic 8k",
    "Motivation":        "epic cinematic landscape, lone figure on mountain peak at golden hour, dramatic god rays",
    "ASMR / Satisfying": "extreme macro close-up satisfying texture, pastel rainbow colors, perfect symmetry, 8k",
}


def generate_image_prompt(niche: str, post_text: str, api_key: str) -> str:
    clean = re.sub(r"#\w+", "", post_text)
    clean = re.sub(r"[^\x00-\x7F]+", "", clean).strip()[:250]
    base  = NICHE_BASE_STYLES.get(niche, "cinematic dramatic professional photography, 8k")

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an AI image prompt engineer. Write ONE ultra-specific Stable Diffusion image prompt. Max 80 words. No text/words in image. Return ONLY the prompt."},
                    {"role": "user", "content": f"Niche: {niche}\nPost: {clean}\nStyle: {base}\n\nWrite prompt:"},
                ],
                "temperature": 0.7,
                "max_tokens": 120,
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code == 200:
            prompt = r.json()["choices"][0]["message"]["content"].strip()
            if "no text" not in prompt.lower():
                prompt += ", no text, no words, photorealistic"
            return prompt
    except Exception:
        pass
    return f"{base}, no text, no words, photorealistic, 8k"


def add_text_overlay(img_bytes: bytes, post_text: str, page_name: str = "AI with Abdullah") -> bytes:
    """Add hook text + watermark overlay on image using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io, textwrap, re

        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        w, h = img.size

        lines = [l.strip() for l in post_text.split("\n") if l.strip()]
        hook = lines[0] if lines else ""
        hook = re.sub(r"#\w+", "", hook).strip()
        hook = re.sub(r"[^\x00-\x7F]+", " ", hook).strip()
        if len(hook) > 70:
            hook = hook[:67] + "..."

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_ov  = ImageDraw.Draw(overlay)
        grad_h   = int(h * 0.45)
        for i in range(grad_h):
            alpha = int(210 * (i / grad_h))
            draw_ov.line([(0, h - grad_h + i), (w, h - grad_h + i)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        fs_hook = max(36, w // 22)
        fs_wm   = max(18, w // 55)
        try:
            font_hook = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs_hook)
            font_wm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", fs_wm)
        except Exception:
            font_hook = ImageFont.load_default()
            font_wm   = ImageFont.load_default()

        wrapped = textwrap.fill(hook, width=max(20, w // (fs_hook // 2))).split("\n")
        line_h  = fs_hook + 10
        text_y  = h - len(wrapped) * line_h - int(h * 0.07)
        for line in wrapped:
            bbox   = draw.textbbox((0, 0), line, font=font_hook)
            text_w = bbox[2] - bbox[0]
            x = (w - text_w) // 2
            draw.text((x + 3, text_y + 3), line, font=font_hook, fill=(0, 0, 0, 180))
            draw.text((x, text_y), line, font=font_hook, fill=(255, 255, 255, 255))
            text_y += line_h

        wm_bbox = draw.textbbox((0, 0), page_name, font=font_wm)
        draw.text((w - (wm_bbox[2] - wm_bbox[0]) - 20, h - fs_wm - 15), page_name, font=font_wm, fill=(255, 255, 255, 160))

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=92)
        return buf.getvalue()
    except Exception as e:
        print(f"  Overlay failed: {e}")
        return img_bytes


def download_image(niche: str, post_text: str, api_key: str) -> bytes | None:
    prompt  = generate_image_prompt(niche, post_text, api_key)
    encoded = urllib.parse.quote(prompt)
    seed    = random.randint(1, 999999)
    url     = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true&enhance=true&model=flux&seed={seed}"
    print(f"  Image prompt: {prompt[:80]}...")
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            raw = r.content
            print(f"  Image downloaded: {len(raw)//1024}KB — applying overlay...")
            return add_text_overlay(raw, post_text)
    except Exception as e:
        print(f"  Image download failed: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  FACEBOOK POSTING
# ─────────────────────────────────────────────────────────────────────────────
def post_text_to_facebook(page_id: str, token: str, text: str) -> dict:
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/feed",
            data={"message": text, "access_token": token},
            timeout=15,
        )
        data = r.json()
        if "id" in data:
            return {"success": True, "id": data["id"]}
        return {"success": False, "error": data.get("error", {}).get("message", "Unknown")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def post_image_to_facebook(page_id: str, token: str, img_bytes: bytes, caption: str) -> dict:
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/photos",
            data={"caption": caption, "access_token": token},
            files={"source": ("post.jpg", img_bytes, "image/jpeg")},
            timeout=45,
        )
        data = r.json()
        if "id" in data or "post_id" in data:
            return {"success": True, "id": data.get("post_id", data.get("id"))}
        return {"success": False, "error": data.get("error", {}).get("message", "Unknown")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=["morning", "afternoon", "evening"])
    args = parser.parse_args()

    slot     = SLOTS[args.slot]
    groq_key = os.environ.get("GROQ_API_KEY", "")
    fb_token = os.environ.get("FB_PAGE_TOKEN", "")
    fb_page  = os.environ.get("FB_PAGE_ID", "")

    print(f"\n{'='*50}")
    print(f"  Auto Post — {slot['label']}")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Niche: {slot['niche']} | Lang: {slot['language']}")
    print(f"{'='*50}")

    # Validate secrets
    if not groq_key:
        print("❌ GROQ_API_KEY not set in GitHub Secrets")
        sys.exit(1)
    if not fb_token or not fb_page:
        print("❌ FB_PAGE_TOKEN or FB_PAGE_ID not set in GitHub Secrets")
        sys.exit(1)

    # Step 1: Generate post
    print("\n📝 Generating post...")
    text = generate_post(slot, groq_key)
    if not text:
        print("❌ Failed to generate non-generic post after all retries")
        sys.exit(1)
    print(f"✅ Post generated ({len(text)} chars)")
    print(f"\n--- POST PREVIEW ---\n{text[:200]}...\n---")

    # Step 2: Generate + download image
    print("\n🎨 Generating image...")
    img_bytes = download_image(slot["niche"], text, groq_key)

    # Step 3: Post to Facebook
    print("\n📤 Posting to Facebook...")
    if img_bytes:
        result = post_image_to_facebook(fb_page, fb_token, img_bytes, text)
        if not result["success"]:
            print(f"  Image post failed: {result['error']} — falling back to text")
            result = post_text_to_facebook(fb_page, fb_token, text)
    else:
        print("  No image — posting text only")
        result = post_text_to_facebook(fb_page, fb_token, text)

    if result["success"]:
        print(f"\n✅ POSTED SUCCESSFULLY! ID: {result['id']}")
    else:
        print(f"\n❌ FAILED: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
