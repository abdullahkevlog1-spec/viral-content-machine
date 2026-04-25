# ═══════════════════════════════════════════════════════════════════════════
#  analytics.py — Post History + Engagement Metrics Storage
#  NEW FILE — extends original history system with hook tracking & stats
# ═══════════════════════════════════════════════════════════════════════════

import json
import os
from datetime import datetime
from collections import defaultdict

HISTORY_FILE = "fb_history.json"
MAX_HISTORY = 100  # Increased from 30


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD / SAVE
# ─────────────────────────────────────────────────────────────────────────────
def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history: list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
#  ADD POST RECORD — extended schema vs original
# ─────────────────────────────────────────────────────────────────────────────
def record_post(
    text: str,
    niche: str,
    hook_style_name: str,
    variation: str,
    tone_level: int,
    post_id: str
) -> dict:
    """
    Creates a post record with the extended schema.
    Schema is backwards-compatible with original history entries.
    """
    record = {
        # ── Original fields (kept for backwards compat) ──
        "text": text,
        "type": niche,          # maps to original "type" field
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "post_id": post_id,
        # ── NEW fields ──
        "niche": niche,
        "hook_style": hook_style_name,
        "variation": variation,
        "tone_level": tone_level,
        "char_count": len(text),
        "word_count": len(text.split()),
        # Engagement fields — to be manually updated in future, or via FB API
        "likes": None,
        "comments": None,
        "shares": None,
        "reach": None
    }
    return record


# ─────────────────────────────────────────────────────────────────────────────
#  ANALYTICS COMPUTATIONS — prepares data for future hook performance tracking
# ─────────────────────────────────────────────────────────────────────────────
def hook_performance_summary(history: list) -> dict:
    """
    Groups posts by hook style and counts usage.
    Future: when engagement data is filled in, will show best-performing hooks.
    """
    summary = defaultdict(lambda: {"count": 0, "posts": []})
    for post in history:
        hook = post.get("hook_style", "Unknown")
        summary[hook]["count"] += 1
        summary[hook]["posts"].append(post.get("time", ""))
    return dict(summary)


def niche_usage_summary(history: list) -> dict:
    """Counts posts per niche."""
    summary = defaultdict(int)
    for post in history:
        niche = post.get("niche") or post.get("type", "Unknown")
        summary[niche] += 1
    return dict(summary)


def variation_usage_summary(history: list) -> dict:
    """Counts posts per variation type."""
    summary = defaultdict(int)
    for post in history:
        var = post.get("variation", "Unknown")
        summary[var] += 1
    return dict(summary)


def tone_distribution(history: list) -> dict:
    """Groups posts by tone level bucket."""
    buckets = {"Safe (1-3)": 0, "Balanced (4-6)": 0, "Aggressive (7-10)": 0}
    for post in history:
        tone = post.get("tone_level")
        if tone is None:
            continue
        if tone <= 3:
            buckets["Safe (1-3)"] += 1
        elif tone <= 6:
            buckets["Balanced (4-6)"] += 1
        else:
            buckets["Aggressive (7-10)"] += 1
    return buckets


def posts_this_week(history: list) -> int:
    """Count posts in last 7 days."""
    from datetime import timedelta
    now = datetime.now()
    count = 0
    for post in history:
        try:
            posted_at = datetime.strptime(post["time"], "%Y-%m-%d %H:%M")
            if (now - posted_at).days < 7:
                count += 1
        except (KeyError, ValueError):
            continue
    return count


def posts_today(history: list) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for p in history if p.get("time", "").startswith(today))
