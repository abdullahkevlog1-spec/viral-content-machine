"""Content generation, trend fallback, agent gate, and run logging."""

from __future__ import annotations

import base64
import json
import os
import random
import re
from datetime import datetime
from typing import Any

import requests

from carousel import generate_carousel
from engine import generate_and_download_image, generate_single, get_hook_by_id, is_generic, is_too_short

try:
    from agent import AgentDecision
except Exception as agent_error:
    AgentDecision = None
    print(f"  [Agent] Disabled (import failed: {agent_error})")

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

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


def get_agent() -> Any | None:
    if AgentDecision is None:
        return None
    try:
        print("  [Agent] Quality gate: ENABLED")
        return AgentDecision()
    except Exception as exc:
        print(f"  [Agent] Disabled (init failed: {exc})")
        return None


def generate_post(slot: dict[str, Any], api_key: str) -> str | None:
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


def approve_or_regenerate(text: str, slot: dict[str, Any], groq_key: str, agent: Any | None) -> str:
    if agent is None:
        print("  [Agent] Gate skipped - posting original draft")
        return text

    for attempt in range(1, 3):
        verdict = agent.approve(text, slot, attempt=attempt)
        if verdict["action"] in ("post", "post_anyway"):
            return text
        if verdict["action"] == "regenerate":
            print(f"  Regenerating (attempt {attempt + 1}/2)...")
            new_text = generate_post(slot, groq_key)
            if new_text:
                text = new_text
            else:
                print("  Regeneration failed - using previous draft")
                return text
    return text


def generate_regular_bundle(slot_name: str, base_slot: dict[str, Any], groq_key: str) -> dict[str, Any] | None:
    agent = get_agent()
    slot = agent.get_strategy(base_slot, slot_name) if agent else dict(base_slot)

    print(f"  Niche: {slot['niche']} | Lang: {slot['language']}")
    text = generate_post(slot, groq_key)
    if not text:
        return None
    text = approve_or_regenerate(text, slot, groq_key, agent)

    slides = []
    try:
        slides = generate_carousel(text, slot["niche"])
        print(f"  {len(slides)} slides generated")
    except Exception as exc:
        print(f"  Carousel failed: {exc}")

    image = None
    if not slides:
        image = generate_and_download_image(slot["niche"], text, groq_key)

    return {
        "slot_name": slot_name,
        "slot": slot,
        "base_slot": base_slot,
        "text": text,
        "slides": slides,
        "image": image,
        "trend": None,
    }


def fetch_trending_topic() -> dict[str, str]:
    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl="en-US", tz=300)
        trending = pt.trending_searches(pn="pakistan")
        if trending is not None and len(trending) > 0:
            topic = str(trending.iloc[random.randint(0, min(4, len(trending) - 1))][0])
            print(f"  Google Trend PK: {topic}")
            return {"title": topic, "summary": f"Trending in Pakistan: {topic}", "source": "Google Trends"}
    except Exception as exc:
        print(f"  pytrends failed: {exc}")

    try:
        import xml.etree.ElementTree as ET

        feed_url = random.choice(PAKISTAN_NEWS_FEEDS)
        response = requests.get(feed_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            if items:
                item = items[random.randint(0, min(4, len(items) - 1))]
                title = item.findtext("title", "").strip()
                summary = re.sub(r"<[^>]+>", "", item.findtext("description", "").strip())[:300]
                if title:
                    print(f"  RSS topic: {title[:60]}")
                    return {"title": title, "summary": summary, "source": feed_url}
    except Exception as exc:
        print(f"  RSS failed: {exc}")

    topic = random.choice(TRENDING_TOPICS_FALLBACK)
    return {"title": topic, "summary": topic, "source": "fallback"}


def generate_trending_post(trend: dict[str, str], api_key: str) -> str | None:
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
            response = requests.post(
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
            if response.status_code != 200:
                print(f"  Groq trend error {response.status_code}: {response.text[:120]}")
                continue
            text = response.json()["choices"][0]["message"]["content"].strip()
            if not is_too_short(text) and not is_generic(text):
                return text
            print(f"  Trending attempt {attempt + 1}: quality retry")
        except Exception as exc:
            print(f"  Trending attempt {attempt + 1} error: {exc}")
    return None


def generate_trending_bundle(slot: dict[str, Any], groq_key: str) -> dict[str, Any] | None:
    trend = fetch_trending_topic()
    text = generate_trending_post(trend, groq_key)
    if not text:
        return None

    slides = []
    try:
        slides = generate_carousel(text, "News & Trends")
        print(f"  {len(slides)} slides ready")
    except Exception as exc:
        print(f"  Carousel failed: {exc}")

    return {
        "slot_name": "trending",
        "slot": slot,
        "base_slot": slot,
        "text": text,
        "slides": slides,
        "image": None,
        "trend": trend,
    }


def generate_content_bundle(slot_name: str, slot: dict[str, Any], groq_key: str) -> dict[str, Any] | None:
    print("\n==================================================")
    print(f"  Auto Post - {slot.get('label', slot_name)}")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("==================================================")

    if slot_name == "trending":
        return generate_trending_bundle(slot, groq_key)
    return generate_regular_bundle(slot_name, slot, groq_key)


def build_log_entry(bundle: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    slot = bundle["slot"]
    hook = get_hook_by_id(slot.get("hook_id", "curiosity"))
    trend = bundle.get("trend") or {}
    return {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "slot": bundle.get("slot_name", ""),
        "niche": slot.get("niche", ""),
        "language": slot.get("language", ""),
        "hook_id": slot.get("hook_id", ""),
        "hook_style": hook.get("name", ""),
        "variation": slot.get("variation", ""),
        "tone": slot.get("tone", ""),
        "topic": trend.get("title", ""),
        "status": "success" if result.get("success") else "failed",
        "post_id": result.get("id", ""),
        "method": result.get("method", ""),
        "error": result.get("error", ""),
        "preview": bundle.get("text", "")[:100],
        "adapted_from_strategy": bundle.get("slot") != bundle.get("base_slot"),
    }


def commit_log_to_github(entry: dict[str, Any], gh_token: str, repo: str) -> None:
    if not gh_token or not repo:
        print("  No GH_PAT - skipping log commit")
        return

    headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{repo}/contents/data/post_log.json"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            existing = json.loads(base64.b64decode(response.json()["content"]).decode())
            sha = response.json()["sha"]
        else:
            existing = []
            sha = None

        existing.append(entry)
        existing = existing[-100:]
        content = base64.b64encode(json.dumps(existing, indent=2, ensure_ascii=False).encode()).decode()
        payload = {"message": f"log: {entry.get('slot', 'post')} {entry.get('time', '')}", "content": content, "branch": "main"}
        if sha:
            payload["sha"] = sha

        update_response = requests.put(url, json=payload, headers=headers, timeout=15)
        if update_response.status_code in (200, 201):
            print("  Log committed to GitHub")
        else:
            print(f"  Log commit failed: {update_response.status_code}")
    except Exception as exc:
        print(f"  Log commit error: {exc}")


def record_run(bundle: dict[str, Any], result: dict[str, Any]) -> None:
    entry = build_log_entry(bundle, result)
    commit_log_to_github(entry, os.environ.get("GH_PAT", ""), os.environ.get("GITHUB_REPO", ""))
