"""
analytics.py — Unified Analytics + History + Engagement Tracking
Phase 2: Added quality scoring + prompt version tracking.
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

HISTORY_FILE = "data/performance_history.json"
MEMORY_FILE = "data/content_memory.json"
MAX_HISTORY = 200
CURRENT_PROMPT_VERSION = "v1"

os.makedirs("data", exist_ok=True)


def _safe_load_json(path, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        backup_path = f"{path}.corrupted"
        try:
            os.replace(path, backup_path)
        except Exception:
            pass
        return default


def _safe_save_json(path, data):
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def score_content_quality(text: str) -> int:
    score = 50
    if not text:
        return 0

    text_lower = text.lower()

    if any(x in text_lower for x in ["how", "why", "secret", "mistake", "truth", "stop", "before"]):
        score += 15

    if any(x in text_lower for x in ["comment", "follow", "share", "save", "dm"]):
        score += 10

    wc = len(text.split())
    if 30 <= wc <= 120:
        score += 10

    if any(x in text_lower for x in ["in today's world", "unlock your potential", "game changer", "elevate"]):
        score -= 20

    return max(0, min(100, score))


def load_history() -> list:
    history = _safe_load_json(HISTORY_FILE, [])
    if history:
        return history
    return _safe_load_json("fb_history.json", [])


def save_history(history: list):
    _safe_save_json(HISTORY_FILE, history[-MAX_HISTORY:])


def add_to_history(entry: dict):
    history = load_history()
    text = entry.get("text", "")

    record = {
        "post_id": entry.get("post_id", entry.get("id", "")),
        "created_at": entry.get("created_at", entry.get("time", datetime.now().strftime("%Y-%m-%d %H:%M"))),
        "time": entry.get("created_at", entry.get("time", datetime.now().strftime("%Y-%m-%d %H:%M"))),
        "prompt_version": entry.get("prompt_version", CURRENT_PROMPT_VERSION),
        "quality_score": entry.get("quality_score", score_content_quality(text)),
        "niche": entry.get("niche", entry.get("type", "Unknown")),
        "hook_style": entry.get("hook_style", entry.get("hook", "")),
        "variation": entry.get("variation", ""),
        "tone_level": entry.get("tone_level", entry.get("tone", 5)),
        "language": entry.get("language", "English"),
        "slot": entry.get("slot", ""),
        "text": text[:200],
        "auto_scheduled": entry.get("auto_scheduled", False),
        "likes": entry.get("likes", 0),
        "comments": entry.get("comments", 0),
        "shares": entry.get("shares", 0),
        "reach": entry.get("reach", 0),
        "engagement_rate": entry.get("engagement_rate", 0.0),
        "score": entry.get("score", 0)
    }

    history.append(record)
    save_history(history)
    return record


def record_post(text: str, niche: str, hook_style_name: str, variation: str, tone_level: int, post_id: str) -> dict:
    record = {
        "post_id": post_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "prompt_version": CURRENT_PROMPT_VERSION,
        "quality_score": score_content_quality(text),
        "niche": niche,
        "hook_style": hook_style_name,
        "variation": variation,
        "tone_level": tone_level,
        "text": text[:200],
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "reach": 0,
        "engagement_rate": 0.0,
        "score": 0
    }

    history = load_history()
    history.append(record)
    save_history(history)
    return record
