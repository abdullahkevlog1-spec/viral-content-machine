"""
auto_post.py — Standalone scheduler for GitHub Actions.

Regular auto-post slots now use engine.py as the single source of truth for:
- hooks
- niche profiles
- prompt generation
- anti-generic quality checks
- image generation fallback
"""

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime

import requests

from carousel import generate_carousel
from engine import (
    generate_single,
    generate_and_download_image,
    get_hook_by_id,
    is_generic,
    is_too_short,
    post_image_to_facebook as engine_post_image_to_facebook,
)

# ── Agent import — safe fallback agar agent.py missing ho ──
try:
    from agent import AgentDecision
    _agent = AgentDecision()
    AGENT_ENABLED = True
    print("  [Agent] Quality gate: ENABLED")
except Exception as _agent_err:
    _agent = None
    AGENT_ENABLED = False
    print(f"  [Agent] Disabled (import failed: {_agent_err})")

SLOTS = {
    "morning": {
        "label": "🌅 Subah 9:00 AM",
        "niche": "AI & Tech",
        "hook_id": "curiosity",
        "tone": 7,
        "variation": "Bold/Controversial",
        "language": "English",
    },
    "afternoon": {
        "label": "☀️ Dopahar 2:00 PM",
        "niche": "Motivation",
        "hook_id": "bold_claim",
        "tone": 8,
        "variation": "Bold/Controversial",
        "language": "Roman Urdu",
    },
    "evening": {
        "label": "🌙 Raat 9:00 PM",
        "niche": "ASMR / Satisfying",
        "hook_id": "relatable_pain",
        "tone": 5,
        "variation": "Emotional",
        "language": "Hinglish",
    },
}

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v19.0")

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


def generate_post(slot: dict, api_key: str) -> str | None:
    hook = get_hook_by_id(slot["hook_id"])
    result = generate_single(
        niche=slot["niche"],
        hook_style=hook,
        variation=slot["variation"],
        tone_level=slot["tone"],
        api_key=api_key,
        max_retries=4,
        language=slot.get("language", "English"),
    )

    if result.get("error"):
        print(f"  Engine error: {result['error']}")
        return None

    text = (result.get("text") or "").strip()
    if not text:
        print("  Engine returned empty text")
        return None

    if result.get("flagged_generic"):
        print("  Warning: engine flagged output as generic after retries")

    return text


def post_text_to_facebook(page_id: str, token: str, message: str) -> dict:
    try:
        r = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed",
            data={"message": message, "access_token": token},
            timeout=30,
        )
        data = r.json()
        print(f"  FB text response: {data}")
        if "id" in data:
            return {"success": True, "id": data["id"]}
        return {
            "success": False,
            "error": data.get("error", {}).get("message", str(data)),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def merge_slides(slides: list) -> bytes:
    from PIL import Image
    import io

    TARGET_W = 1080
    images = []
    for slide in slides:
        try:
            img = Image.open(io.BytesIO(slide)).convert("RGB")
            if img.width != TARGET_W:
                ratio = TARGET_W / img.width
                img = img.resize(
                    (TARGET_W, int(img.height * ratio)), Image.LANCZOS
                )
            images.append(img)
        except Exception as e:
            print(f"  Slide merge warning: {e}")

    if not images:
        return b""

    total_h = sum(img.height for img in images)
    merged = Image.new("RGB", (TARGET_W, total_h), (13, 13, 13))
    y = 0
    for img in images:
        merged.paste(img, (0, y))
        y += img.height

    buf = io.BytesIO()
    merged.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def post_carousel_to_facebook(page_id: str, token: str, slides: list, caption: str) -> dict:
    if not slides:
        return {"success": False, "error": "No carousel slides generated"}

    photo_ids = []
    for i, img_bytes in enumerate(slides):
        try:
            r = requests.post(
                f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/photos",
                data={"access_token": token, "published": "false"},
                files={"source": (f"slide_{i + 1}.jpg", img_bytes, "image/jpeg")},
                timeout=45,
            )
            data = r.json()
            pid = data.get("id")
            if pid:
                photo_ids.append(pid)
                print(f"  Slide {i + 1} uploaded: {pid}")
            else:
                print(f"  Slide {i + 1} failed: {data}")
        except Exception as e:
            print(f"  Slide {i + 1} exception: {e}")

    if photo_ids:
        payload = {"message": caption, "access_token": token}
        for i, pid in enumerate(photo_ids):
            payload[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})

        try:
            r = requests.post(
                f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed",
                data=payload,
                timeout=30,
            )
            data = r.json()
            print(f"  FB carousel response: {data}")
            if "id" in data:
                return {"success": True, "id": data["id"]}
            print(f"  Carousel feed failed: {data.get('error', {}).get('message', str(data))}")
        except Exception as e:
            print(f"  Carousel feed exception: {e}")

    merged = merge_slides(slides)
    if merged:
        print("  Falling back to merged image")
        return engine_post_image_to_facebook(page_id, token, merged, caption)

    return {"success": False, "error": "Carousel upload failed"}


def commit_log_to_github(entry: dict, gh_token: str, repo: str):
    if not gh_token or not repo:
        print("  No GH_PAT — skipping log commit")
        return

    import base64

    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{repo}/contents/data/post_log.json"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            existing = json.loads(base64.b64decode(r.json()["content"]).decode())
            sha = r.json()["sha"]
        else:
            existing = []
            sha = None

        existing.append(entry)
        existing = existing[-100:]

        content = base64.b64encode(
            json.dumps(existing, indent=2, ensure_ascii=False).encode()
        ).decode()
        data = {
            "message": f"log: {entry.get('slot', 'post')} {entry.get('time', '')}",
            "content": content,
            "branch": "main",
        }
        if sha:
            data["sha"] = sha

        r2 = requests.put(url, json=data, headers=headers, timeout=15)
        if r2.status_code in (200, 201):
            print("  Log committed to GitHub")
        else:
            print(f"  Log commit failed: {r2.status_code}")
    except Exception as e:
        print(f"  Log commit error: {e}")


def fetch_trending_topic() -> dict:
    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl="en-US", tz=300)
        trending = pt.trending_searches(pn="pakistan")
        if trending is not None and len(trending) > 0:
            topic = str(trending.iloc[random.randint(0, min(4, len(trending) - 1))][0])
            print(f"  Google Trend PK: {topic}")
            return {"title": topic, "summary": f"Trending in Pakistan: {topic}", "source": "Google Trends"}
    except Exception as e:
        print(f"  pytrends failed: {e}")

    try:
        import xml.etree.ElementTree as ET

        feed_url = random.choice(PAKISTAN_NEWS_FEEDS)
        r = requests.get(feed_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            items = root.findall(".//item")
            if items:
                item = items[random.randint(0, min(4, len(items) - 1))]
                title = item.findtext("title", "").strip()
                summary = re.sub(r"<[^>]+>", "", item.findtext("description", "").strip())[:300]
                if title:
                    print(f"  RSS topic: {title[:60]}")
                    return {"title": title, "summary": summary, "source": feed_url}
    except Exception as e:
        print(f"  RSS failed: {e}")

    topic = random.choice(TRENDING_TOPICS_FALLBACK)
    return {"title": topic, "summary": topic, "source": "fallback"}


def generate_trending_post(trend: dict, api_key: str) -> str | None:
    prompt = f"""You are Pakistan's #1 viral Facebook creator.

Trending topic in Pakistan: {trend['title']}
Context: {trend.get('summary', '')[:250]}

Write one viral Facebook post about this trend.
Rules:
- Hinglish / Roman Urdu natural style
- Hook -> Value -> Punch -> CTA
- Specific to this trend
- No generic motivational lines
- 2-5 emojis naturally
- End with relevant hashtags including #Pakistan
- Max 12 words per line
Return ONLY post text."""

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
            if r.status_code != 200:
                print(f"  Groq trend error {r.status_code}: {r.text[:120]}")
                continue
            text = r.json()["choices"][0]["message"]["content"].strip()
            if not is_too_short(text) and not is_generic(text):
                return text
            print(f"  Trending attempt {attempt + 1}: quality retry")
        except Exception as e:
            print(f"  Trending attempt {attempt + 1} error: {e}")
    return None


def run_trending_post(groq_key: str, fb_token: str, fb_page: str):
    print("\n==================================================")
    print("  TRENDING AUTO POST")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("==================================================")

    trend = fetch_trending_topic()
    text = generate_trending_post(trend, groq_key)
    if not text:
        print("Failed to generate trending post")
        sys.exit(1)

    slides = []
    try:
        slides = generate_carousel(text, "News & Trends")
        print(f"  {len(slides)} slides ready")
    except Exception as e:
        print(f"  Carousel failed: {e}")

    if slides:
        result = post_carousel_to_facebook(fb_page, fb_token, slides, text)
        if not result.get("success"):
            result = post_text_to_facebook(fb_page, fb_token, text)
    else:
        result = post_text_to_facebook(fb_page, fb_token, text)

    log_entry = {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "slot": "trending",
        "niche": "News & Trends",
        "topic": trend["title"],
        "status": "success" if result.get("success") else "failed",
        "post_id": result.get("id", ""),
        "error": result.get("error", ""),
        "preview": text[:100],
    }
    commit_log_to_github(
        log_entry,
        os.environ.get("GH_PAT", ""),
        os.environ.get("GITHUB_REPO", ""),
    )

    if not result.get("success"):
        print(f"FAILED: {result.get('error')}")
        sys.exit(1)

    print(f"POSTED SUCCESSFULLY: {result['id']}")


def run_regular_post(slot_name: str, groq_key: str, fb_token: str, fb_page: str):
    base_slot = SLOTS[slot_name]

    # ── Step 1: Agent se adapted strategy lo ──
    if AGENT_ENABLED:
        slot = _agent.get_strategy(base_slot, slot_name)
    else:
        slot = base_slot

    print("\n==================================================")
    print(f"  Auto Post — {slot['label']}")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Niche: {slot['niche']} | Lang: {slot['language']}")
    print("==================================================")

    # ── Step 2: First draft generate karo ──
    text = generate_post(slot, groq_key)
    if not text:
        print("Failed to generate post")
        sys.exit(1)

    # ── Step 3: Agent quality gate (max 2 attempts) ──
    if AGENT_ENABLED:
        for attempt in range(1, 3):
            verdict = _agent.approve(text, slot, attempt=attempt)

            if verdict["action"] in ("post", "post_anyway"):
                # Approved — aage badho
                break

            elif verdict["action"] == "regenerate":
                print(f"  Regenerating (attempt {attempt + 1}/2)...")
                new_text = generate_post(slot, groq_key)
                if new_text:
                    text = new_text
                else:
                    # Regeneration fail — original text use karo
                    print("  Regeneration failed — using original draft")
                    break
    else:
        print("  [Agent] Gate skipped — posting original draft")

    # ── Step 4: Post karo (carousel → image → text fallbacks) ──
    result = {"success": False, "error": "No post attempt made"}

    try:
        slides = generate_carousel(text, slot["niche"])
        print(f"  {len(slides)} slides generated")
    except Exception as e:
        print(f"  Carousel failed: {e}")
        slides = []

    if slides:
        result = post_carousel_to_facebook(fb_page, fb_token, slides, text)

    if not result.get("success"):
        img_bytes = generate_and_download_image(slot["niche"], text, groq_key)
        if img_bytes:
            result = engine_post_image_to_facebook(fb_page, fb_token, img_bytes, text)

    if not result.get("success"):
        result = post_text_to_facebook(fb_page, fb_token, text)

    # ── Step 5: Log commit ──
    hook = get_hook_by_id(slot["hook_id"])
    log_entry = {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "slot": slot_name,
        "niche": slot["niche"],
        "language": slot["language"],
        "hook_id": slot["hook_id"],
        "hook_style": hook.get("name", ""),        # learning engine ke liye
        "variation": slot["variation"],
        "tone": slot["tone"],
        "status": "success" if result.get("success") else "failed",
        "post_id": result.get("id", ""),
        "method": result.get("method", ""),
        "error": result.get("error", ""),
        "preview": text[:100],
        "adapted_from_strategy": slot != base_slot,
    }
    commit_log_to_github(
        log_entry,
        os.environ.get("GH_PAT", ""),
        os.environ.get("GITHUB_REPO", ""),
    )

    if not result.get("success"):
        print(f"FAILED: {result.get('error')}")
        sys.exit(1)

    print(f"POSTED SUCCESSFULLY: {result['id']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--slot",
        required=True,
        choices=["morning", "afternoon", "evening", "trending"],
    )
    args = parser.parse_args()

    groq_key = os.environ.get("GROQ_API_KEY", "")
    fb_token = os.environ.get("FB_PAGE_TOKEN", "")
    fb_page = os.environ.get("FB_PAGE_ID", "")

    if not groq_key:
        print("GROQ_API_KEY not set in GitHub Secrets")
        sys.exit(1)
    if not fb_token or not fb_page:
        print("FB_PAGE_TOKEN or FB_PAGE_ID not set in GitHub Secrets")
        sys.exit(1)

    if args.slot == "trending":
        run_trending_post(groq_key, fb_token, fb_page)
    else:
        run_regular_post(args.slot, groq_key, fb_token, fb_page)


if __name__ == "__main__":
    main()
