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
from carousel import generate_carousel

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
    tone     = slot["tone"]
    niche    = slot["niche"]
    variation = slot["variation"]

    # Vary post length based on slot
    length_guide = {
        "Emotional":         "Medium-long (200-280 words). Tell a mini-story. Make it personal and deep.",
        "Educational":       "Long and detailed (250-320 words). Teach step by step. Give real examples.",
        "Bold/Controversial": "Short and punchy (120-180 words). Every word must hit hard. No fluff.",
    }.get(variation, "Medium (180-250 words).")

    niche_context = {
        "AI & Tech": "Reference REAL AI tools (ChatGPT, Gemini, Midjourney, Copilot, Claude, Sora). Give specific use cases. Share surprising facts about AI that people don't know.",
        "Motivation": "Share a SPECIFIC life struggle or mindset shift. Reference real scenarios: job loss, rejection, staying up at 2am, feeling behind in life. Be raw and honest.",
        "ASMR / Satisfying": "Describe SPECIFIC sensory experiences: the sound of rain on glass, kinetic sand, soap cutting, slime stretching. Make the reader feel it physically.",
    }.get(niche, "Be specific, real, and detailed.")

    return f"""You are Pakistan's top viral Facebook content writer with 500K+ page followers.
Your secret: you write like a real human, not a bot. Every post feels personal and specific.

LANGUAGE:
{lang_ins}

NICHE: {niche}
NICHE GUIDE: {niche_context}

HOOK TYPE: {hook['name']}
HOOK PSYCHOLOGY: {hook['psychology']}
VARIATION: {variation}
TONE: {tone}/10 {"(aggressive, bold, debate-starting)" if tone >= 7 else "(warm, relatable, honest)" if tone <= 4 else "(confident, direct, clear)"}

LENGTH: {length_guide}

POST STRUCTURE:

PART 1 — HOOK (1-2 lines)
Must stop the scroll instantly. Use {hook['name']} psychology.
Be specific. NOT vague. Name real things, real feelings, real situations.

PART 2 — BODY (3-6 lines depending on length)
Go DEEP. Don't just state — explain, expand, give examples.
Each line = one clear idea. Build emotional momentum.
Reference specific details: tools, numbers, situations, feelings.

PART 3 — PUNCH (1-2 lines)
Land the unexpected angle. Say what others won't say.
This is the line people screenshot and share.

PART 4 — CTA (2-3 lines)
Natural, conversational — NOT salesy.
Ask a question OR give a direct instruction.
End with: {hashtags}

ABSOLUTE RULES:
1. Return ONLY the post. No labels. No "Here is your post:".
2. BANNED WORDS — instant reject: {banned}
3. NO generic opener: "In today's world", "The truth is", "Most people don't know"
4. Every line must be SPECIFIC. Vague = fail. Generic = fail.
5. Write like you're texting a close friend who needs to hear this.
6. Minimum 3 blank lines between sections for readability.
7. 3-6 emojis placed naturally — not forced.

Start directly with the hook now:"""


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
    "AI & Tech":         "cinematic close-up of glowing holographic AI brain, deep space background, neon blue purple light rays, ultra detailed 8k, dramatic shadows, no text",
    "Motivation":        "cinematic portrait of determined person standing at cliff edge at sunset, golden hour god rays, silhouette against burning sky, ultra realistic 8k, no text",
    "ASMR / Satisfying": "extreme macro close-up of iridescent liquid mercury droplets on black surface, rainbow caustics, studio lighting, ultra sharp 8k, perfectly symmetrical, no text",
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
    url     = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&nologo=true&enhance=true&model=flux&seed={seed}"
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
def post_carousel_to_facebook(page_id: str, token: str,
                              slides: list, caption: str) -> dict:
    """
    Post 3-slide carousel to Facebook feed.
    Each slide uploaded as unpublished photo, then attached to one feed post.
    """
    try:
        photo_ids = []
        for i, img_bytes in enumerate(slides):
            r = requests.post(
                f"https://graph.facebook.com/v19.0/{page_id}/photos",
                data={"access_token": token, "published": "false"},
                files={"source": (f"slide_{i+1}.jpg", img_bytes, "image/jpeg")},
                timeout=45,
            )
            pid = r.json().get("id")
            if not pid:
                print(f"  Slide {i+1} upload failed: {r.json()}")
                continue
            photo_ids.append(pid)
            print(f"  Slide {i+1} uploaded: {pid}")

        if not photo_ids:
            return {"success": False, "error": "All slides failed to upload"}

        # Attach all photos to one feed post
        data = {"message": caption, "access_token": token}
        for i, pid in enumerate(photo_ids):
            data[f"attached_media[{i}]"] = f'{{"media_fbid":"{pid}"}}'

        feed_r = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/feed",
            data=data,
            timeout=30,
        )
        feed_data = feed_r.json()
        if "id" in feed_data:
            return {"success": True, "id": feed_data["id"]}

        return {"success": False, "error": feed_data.get("error", {}).get("message", "Unknown")}

    except Exception as e:
        return {"success": False, "error": str(e)}
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
    """
    Two-step: upload photo unpublished → attach to feed post.
    Feed post appears in timeline and followers' feeds.
    """
    try:
        # Step 1 — Upload photo unpublished
        upload_r = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/photos",
            params={"access_token": token},
            data={"published": "false"},
            files={"source": ("post.jpg", img_bytes, "image/jpeg")},
            timeout=45,
        )
        upload_data = upload_r.json()
        photo_id = upload_data.get("id")
        print(f"  Photo upload response: {upload_data}")

        if not photo_id:
            print("  Photo upload failed — posting text only")
            return post_text_to_facebook(page_id, token, caption)

        # Step 2 — Attach to feed post using JSON body
        feed_r = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/feed",
            params={"access_token": token},
            json={
                "message": caption,
                "attached_media": [{"media_fbid": photo_id}]
            },
            timeout=30,
        )
        feed_data = feed_r.json()
        print(f"  Feed post response: {feed_data}")

        if "id" in feed_data:
            return {"success": True, "id": feed_data["id"]}

        # Last fallback — text only (always shows in feed)
        print("  Feed attach failed — text only fallback")
        return post_text_to_facebook(page_id, token, caption)

    except Exception as e:
        print(f"  Exception: {e}")
        return post_text_to_facebook(page_id, token, caption)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
#  TRENDING CONTENT SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

PAKISTAN_NEWS_FEEDS = [
    "https://www.dawn.com/feeds/home",
    "https://geo.tv/rss/top-stories",
    "https://arynews.tv/feed/",
    "https://www.thenews.com.pk/rss/1/1",
]

TRENDING_TOPICS_FALLBACK = [
    "AI technology Pakistan",
    "Pakistan economy 2026",
    "Social media trends Pakistan",
    "Tech jobs Pakistan",
    "Startup Pakistan",
]


def fetch_trending_topic() -> dict:
    """
    Fetch trending topic from Pakistan news RSS feeds.
    Returns: {"title": str, "summary": str, "source": str}
    Falls back to Google Trends if RSS fails.
    """
    # Try pytrends first — Google Trends Pakistan
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=300)  # PKT = UTC+5
        pt.build_payload(kw_list=[""], geo="PK", timeframe="now 1-d")
        trending = pt.trending_searches(pn="pakistan")
        if trending is not None and len(trending) > 0:
            topic = str(trending.iloc[random.randint(0, min(4, len(trending)-1))][0])
            print(f"  🔥 Google Trend (PK): {topic}")
            return {"title": topic, "summary": f"Trending in Pakistan: {topic}", "source": "Google Trends"}
    except Exception as e:
        print(f"  pytrends failed: {e}")

    # Try RSS feeds
    try:
        import xml.etree.ElementTree as ET
        feed_url = random.choice(PAKISTAN_NEWS_FEEDS)
        r = requests.get(feed_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            items = root.findall(".//item")
            if items:
                item = items[random.randint(0, min(4, len(items)-1))]
                title   = item.findtext("title", "").strip()
                summary = item.findtext("description", "").strip()
                # Clean HTML tags
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                if title:
                    print(f"  📰 RSS topic: {title[:60]}")
                    return {"title": title, "summary": summary, "source": feed_url}
    except Exception as e:
        print(f"  RSS failed: {e}")

    # Fallback
    topic = random.choice(TRENDING_TOPICS_FALLBACK)
    print(f"  📌 Fallback topic: {topic}")
    return {"title": topic, "summary": topic, "source": "fallback"}


def generate_trending_post(trend: dict, api_key: str) -> str | None:
    """Generate a viral Facebook post about a trending topic using Groq."""
    prompt = f"""You are a viral Pakistani Facebook content creator.

A trending topic in Pakistan right now: "{trend['title']}"
Context: {trend['summary'][:200]}

Write a viral Facebook post about this trend. Rules:
- Start with a SHOCKING or CURIOSITY hook related to this specific trend
- 4 parts: Hook → Value → Punch → CTA
- Mix of English and Roman Urdu (Hinglish style)
- Tone: Bold, opinionated, makes people stop scrolling
- 2-5 emojis naturally placed
- End with 4-5 relevant hashtags including #Pakistan
- Max 12 words per line
- NO generic phrases like "believe in yourself", "work hard", "game changer"
- Be SPECIFIC to this trend — mention real details

Return ONLY the post. No preamble."""

    for attempt in range(3):
        try:
            r = requests.post(
                GROQ_API_URL,
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": round(0.85 + attempt * 0.05, 2),
                    "max_tokens": 600,
                },
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=30,
            )
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                if len(text) > 150 and not any(p in text.lower() for p in BANNED_PHRASES[:8]):
                    return text
                print(f"  Attempt {attempt+1}: quality check failed — retrying")
        except Exception as e:
            print(f"  Attempt {attempt+1} error: {e}")
    return None


def generate_trending_image_prompt(trend: dict, post_text: str, api_key: str) -> str:
    """Use Groq to make a specific image prompt for the trending topic."""
    clean_post = re.sub(r"#\w+", "", post_text)
    clean_post = re.sub(r"[^\x00-\x7F]+", " ", clean_post).strip()[:200]

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an AI image prompt engineer. Write ONE ultra-specific image prompt. Max 80 words. No text in image. Return ONLY the prompt."},
                    {"role": "user", "content": f"Trending topic: {trend['title']}\nPost: {clean_post}\n\nWrite a dramatic, cinematic, photorealistic image prompt for this topic. No text. No words in image:"},
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
                prompt += ", no text, no words, photorealistic, 8k"
            return prompt
    except Exception:
        pass
    return f"dramatic cinematic photo about {trend['title']}, Pakistan, photorealistic, no text, 8k"


def run_trending_post(groq_key: str, fb_token: str, fb_page: str):
    """Full trending post pipeline — fetch trend → generate → image → post."""
    print(f"\n{'='*50}")
    print(f"  🔥 TRENDING AUTO POST")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}")

    # Step 1: Find trending topic
    print("\n📡 Fetching trending topic from Pakistan...")
    trend = fetch_trending_topic()
    print(f"  Topic: {trend['title']}")

    # Step 2: Generate post
    print("\n📝 Generating viral post about trend...")
    text = generate_trending_post(trend, groq_key)
    if not text:
        print("❌ Could not generate trending post")
        sys.exit(1)
    print(f"✅ Post generated ({len(text)} chars)")
    print(f"\n--- PREVIEW ---\n{text[:250]}...\n---")

    # Step 3: Generate carousel
    print("\n🎨 Generating carousel slides...")
    try:
        slides = generate_carousel(text, "News & Trends")
        print(f"  ✅ {len(slides)} slides ready")
    except Exception as e:
        print(f"  Carousel failed: {e}")
        slides = []

    # Step 4: Post to Facebook
    print("\n📤 Posting to Facebook...")
    if slides:
        result = post_carousel_to_facebook(fb_page, fb_token, slides, text)
        if not result["success"]:
            print(f"  Carousel failed: {result['error']} — text fallback")
            result = post_text_to_facebook(fb_page, fb_token, text)
    else:
        result = post_text_to_facebook(fb_page, fb_token, text)

    if result["success"]:
        print(f"\n✅ TRENDING POST PUBLISHED! ID: {result['id']}")
        print(f"   Topic: {trend['title']}")
    else:
        print(f"\n❌ FAILED: {result['error']}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=["morning", "afternoon", "evening", "trending"])
    args = parser.parse_args()

    groq_key = os.environ.get("GROQ_API_KEY", "")
    fb_token = os.environ.get("FB_PAGE_TOKEN", "")
    fb_page  = os.environ.get("FB_PAGE_ID", "")

    # Validate secrets
    if not groq_key:
        print("❌ GROQ_API_KEY not set in GitHub Secrets")
        sys.exit(1)
    if not fb_token or not fb_page:
        print("❌ FB_PAGE_TOKEN or FB_PAGE_ID not set in GitHub Secrets")
        sys.exit(1)

    # ── Trending slot — special flow ──
    if args.slot == "trending":
        run_trending_post(groq_key, fb_token, fb_page)
        return

    # ── Regular slots ──
    slot = SLOTS[args.slot]

    print(f"\n{'='*50}")
    print(f"  Auto Post — {slot['label']}")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Niche: {slot['niche']} | Lang: {slot['language']}")
    print(f"{'='*50}")

    # Step 1: Generate post
    print("\n📝 Generating post...")
    text = generate_post(slot, groq_key)
    if not text:
        print("❌ Failed to generate non-generic post after all retries")
        sys.exit(1)
    print(f"✅ Post generated ({len(text)} chars)")
    print(f"\n--- POST PREVIEW ---\n{text[:200]}...\n---")

    # Step 2: Generate carousel slides
    print("\n🎨 Generating carousel slides...")
    try:
        slides = generate_carousel(text, slot["niche"])
        print(f"  ✅ {len(slides)} slides generated")
    except Exception as e:
        print(f"  Carousel failed: {e} — will try single image fallback")
        slides = []

    # Step 3: Post to Facebook
    print("\n📤 Posting to Facebook...")
    if slides:
        result = post_carousel_to_facebook(fb_page, fb_token, slides, text)
        if not result["success"]:
            print(f"  Carousel post failed: {result['error']} — falling back to text")
            result = post_text_to_facebook(fb_page, fb_token, text)
    else:
        # Single image fallback
        img_bytes = download_image(slot["niche"], text, groq_key)
        if img_bytes:
            result = post_image_to_facebook(fb_page, fb_token, img_bytes, text)
            if not result["success"]:
                result = post_text_to_facebook(fb_page, fb_token, text)
        else:
            result = post_text_to_facebook(fb_page, fb_token, text)

    if result["success"]:
        print(f"\n✅ POSTED SUCCESSFULLY! ID: {result['id']}")
    else:
        print(f"\n❌ FAILED: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
