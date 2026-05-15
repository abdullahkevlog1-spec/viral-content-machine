"""
auto_post.py — Standalone scheduler for GitHub Actions.

Uses engine.py as the content source of truth, reads data/strategy_state.json
when available, and posts with safe carousel -> feed image -> direct image -> text fallbacks.
"""

import argparse
import json
import os
import random
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import requests

from carousel import generate_carousel
from engine import (
    generate_single,
    generate_and_download_image,
    get_hook_by_id,
    is_generic,
    is_too_short,
)

DATA_DIR = Path("data")
STRATEGY_PATH = DATA_DIR / "strategy_state.json"

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

ALLOWED_NICHES = {"AI & Tech", "Motivation", "ASMR / Satisfying", "Business"}
ALLOWED_VARIATIONS = {"Emotional", "Educational", "Bold/Controversial"}
ALLOWED_LANGUAGES = {"English", "Roman Urdu", "Hinglish"}

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


def load_json_file(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"  Could not load {path}: {e}")
    return default


def load_strategy() -> dict:
    strategy = load_json_file(STRATEGY_PATH, {})
    if not isinstance(strategy, dict):
        return {}
    return strategy


def apply_strategy(slot: dict, slot_name: str) -> dict:
    strategy = load_strategy()
    if not strategy or strategy.get("learning_status") not in {"active", "warmup"}:
        return slot

    adapted = deepcopy(slot)

    best_hook = strategy.get("best_hook")
    best_niche = strategy.get("best_niche")
    best_style = strategy.get("best_style")
    best_language = strategy.get("best_language")

    if best_hook:
        adapted["hook_id"] = best_hook
    if best_style in ALLOWED_VARIATIONS:
        adapted["variation"] = best_style
    if best_language in ALLOWED_LANGUAGES:
        adapted["language"] = best_language

    # Keep niche diversity by default. Only override morning because it is the most suitable discovery slot.
    if slot_name == "morning" and best_niche in ALLOWED_NICHES:
        adapted["niche"] = best_niche

    print(
        "  Strategy applied: "
        f"hook={adapted['hook_id']} niche={adapted['niche']} "
        f"style={adapted['variation']} lang={adapted['language']}"
    )
    return adapted


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
            return {"success": True, "id": data["id"], "method": "text_feed"}
        return {"success": False, "error": data.get("error", {}).get("message", str(data))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def post_feed_image_to_facebook(page_id: str, token: str, image_bytes: bytes, caption: str) -> dict:
    """Preferred image flow: upload unpublished image, then attach it to a normal feed post."""
    try:
        upload = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/photos",
            data={"access_token": token, "published": "false"},
            files={"source": ("post.jpg", image_bytes, "image/jpeg")},
            timeout=60,
        )
        upload_data = upload.json()
        media_id = upload_data.get("id")
        print(f"  FB unpublished image response: {upload_data}")
        if not media_id:
            return {"success": False, "error": upload_data.get("error", {}).get("message", str(upload_data))}

        feed = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed",
            data={
                "message": caption,
                "access_token": token,
                "attached_media[0]": json.dumps({"media_fbid": media_id}),
            },
            timeout=30,
        )
        feed_data = feed.json()
        print(f"  FB feed image response: {feed_data}")
        if "id" in feed_data:
            return {"success": True, "id": feed_data["id"], "method": "feed_image"}
        return {"success": False, "error": feed_data.get("error", {}).get("message", str(feed_data))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def post_direct_photo_to_facebook(page_id: str, token: str, image_bytes: bytes, caption: str) -> dict:
    """Last image fallback. May create a photo post depending on Page/API behavior."""
    try:
        r = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/photos",
            data={"caption": caption, "access_token": token, "published": "true"},
            files={"source": ("post.jpg", image_bytes, "image/jpeg")},
            timeout=60,
        )
        data = r.json()
        print(f"  FB direct photo response: {data}")
        if "id" in data or "post_id" in data:
            return {"success": True, "id": data.get("post_id", data.get("id")), "method": "direct_photo"}
        return {"success": False, "error": data.get("error", {}).get("message", str(data))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def post_image_with_fallbacks(page_id: str, token: str, image_bytes: bytes, caption: str) -> dict:
    result = post_feed_image_to_facebook(page_id, token, image_bytes, caption)
    if result.get("success"):
        return result

    print(f"  Feed image failed: {result.get('error')} — trying direct photo fallback")
    return post_direct_photo_to_facebook(page_id, token, image_bytes, caption)


def merge_slides(slides: list) -> bytes:
    from PIL import Image
    import io

    images = []
    for slide in slides:
        try:
            img = Image.open(io.BytesIO(slide)).convert("RGB")
            if img.width != 1080:
                img = img.resize((1080, 1080), Image.LANCZOS)
            images.append(img)
        except Exception as e:
            print(f"  Slide merge warning: {e}")

    if not images:
        return b""

    total_h = sum(img.height for img in images)
    merged = Image.new("RGB", (1080, total_h), (13, 13, 13))
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
            r = requests.post(f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed", data=payload, timeout=30)
            data = r.json()
            print(f"  FB carousel response: {data}")
            if "id" in data:
                return {"success": True, "id": data["id"], "method": "carousel_feed"}
            print(f"  Carousel feed failed: {data.get('error', {}).get('message', str(data))}")
        except Exception as e:
            print(f"  Carousel feed exception: {e}")

    merged = merge_slides(slides)
    if merged:
        print("  Falling back to merged image")
        return post_image_with_fallbacks(page_id, token, merged, caption)

    return {"success": False, "error": "Carousel upload failed"}


def commit_log_to_github(entry: dict, gh_token: str, repo: str):
    if not gh_token or not repo:
        print("  No GH_PAT — skipping log commit")
        return

    import base64

    headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
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

        content = base64.b64encode(json.dumps(existing, indent=2, ensure_ascii=False).encode()).decode()
        data = {"message": f"log: {entry.get('slot', 'post')} {entry.get('time', '')}", "content": content, "branch": "main"}
        if sha:
            data["sha"] = sha

        r2 = requests.put(url, json=data, headers=headers, timeout=15)
        if r2.status_code in (200, 201):
            print("  Log committed to GitHub")
        else:
            print(f"  Log commit failed: {r2.status_code}: {r2.text[:120]}")
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
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": round(0.85 + attempt * 0.05, 2), "max_tokens": 600},
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


def build_log_entry(slot_name: str, slot: dict, result: dict, text: str, extra: dict | None = None) -> dict:
    entry = {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "slot": slot_name,
        "niche": slot.get("niche", ""),
        "language": slot.get("language", ""),
        "hook_id": slot.get("hook_id", ""),
        "variation": slot.get("variation", ""),
        "tone": slot.get("tone", ""),
        "status": "success" if result.get("success") else "failed",
        "post_id": result.get("id", ""),
        "method": result.get("method", ""),
        "error": result.get("error", ""),
        "preview": text[:100],
    }
    if extra:
        entry.update(extra)
    return entry


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

    try:
        slides = generate_carousel(text, "News & Trends")
        print(f"  {len(slides)} slides ready")
    except Exception as e:
        print(f"  Carousel failed: {e}")
        slides = []

    result = post_carousel_to_facebook(fb_page, fb_token, slides, text) if slides else {"success": False, "error": "No slides"}
    if not result.get("success"):
        result = post_text_to_facebook(fb_page, fb_token, text)

    log_entry = build_log_entry(
        "trending",
        {"niche": "News & Trends", "language": "Hinglish", "hook_id": "trend", "variation": "Trending", "tone": 8},
        result,
        text,
        {"topic": trend["title"]},
    )
    commit_log_to_github(log_entry, os.environ.get("GH_PAT", ""), os.environ.get("GITHUB_REPO", ""))

    if not result.get("success"):
        print(f"FAILED: {result.get('error')}")
        sys.exit(1)
    print(f"POSTED SUCCESSFULLY: {result['id']}")


def run_regular_post(slot_name: str, groq_key: str, fb_token: str, fb_page: str):
    base_slot = SLOTS[slot_name]
    slot = apply_strategy(deepcopy(base_slot), slot_name)

    print("\n==================================================")
    print(f"  Auto Post — {slot['label']}")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Niche: {slot['niche']} | Lang: {slot['language']}")
    print("==================================================")

    text = generate_post(slot, groq_key)
    if not text:
        print("Failed to generate post")
        sys.exit(1)

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
            result = post_image_with_fallbacks(fb_page, fb_token, img_bytes, text)

    if not result.get("success"):
        result = post_text_to_facebook(fb_page, fb_token, text)

    log_entry = build_log_entry(slot_name, slot, result, text, {"adapted_from_strategy": slot != base_slot})
    commit_log_to_github(log_entry, os.environ.get("GH_PAT", ""), os.environ.get("GITHUB_REPO", ""))

    if not result.get("success"):
        print(f"FAILED: {result.get('error')}")
        sys.exit(1)
    print(f"POSTED SUCCESSFULLY: {result['id']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=["morning", "afternoon", "evening", "trending"])
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
