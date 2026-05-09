"""
analytics.py — Unified Analytics + History + Engagement Tracking
Phase 1: Fixed add_to_history(), proper engagement scoring, comparison functions.
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

HISTORY_FILE    = "data/performance_history.json"
MEMORY_FILE     = "data/content_memory.json"
MAX_HISTORY     = 200

os.makedirs("data", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD / SAVE
# ─────────────────────────────────────────────────────────────────────────────
def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback: old path
    if os.path.exists("fb_history.json"):
        try:
            with open("fb_history.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(history: list):
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
#  ADD TO HISTORY — the missing function that app.py calls
# ─────────────────────────────────────────────────────────────────────────────
def add_to_history(entry: dict):
    """
    Add a post entry to performance history.
    Called from app.py and auto_post.py after every post.
    """
    history = load_history()

    # Normalize entry schema
    record = {
        "post_id":    entry.get("post_id", entry.get("id", "")),
        "time":       entry.get("time", entry.get("timestamp",
                      datetime.now().strftime("%Y-%m-%d %H:%M"))),
        "niche":      entry.get("niche", entry.get("type", "Unknown")),
        "hook_style": entry.get("hook_style", entry.get("hook", "")),
        "variation":  entry.get("variation", ""),
        "tone_level": entry.get("tone_level", entry.get("tone", 5)),
        "language":   entry.get("language", "English"),
        "slot":       entry.get("slot", ""),
        "text":       entry.get("text", "")[:200],
        "auto_scheduled": entry.get("auto_scheduled", False),
        # Engagement — filled later by insights_fetcher
        "likes":      entry.get("likes", 0),
        "comments":   entry.get("comments", 0),
        "shares":     entry.get("shares", 0),
        "reach":      entry.get("reach", 0),
        "engagement_rate": entry.get("engagement_rate", 0.0),
        "score":      entry.get("score", 0),
    }

    history.append(record)
    save_history(history)
    return record


# ─────────────────────────────────────────────────────────────────────────────
#  RECORD POST — extended schema (called from app.py Approve button)
# ─────────────────────────────────────────────────────────────────────────────
def record_post(text: str, niche: str, hook_style_name: str,
                variation: str, tone_level: int, post_id: str) -> dict:
    record = {
        "post_id":    post_id,
        "time":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "niche":      niche,
        "hook_style": hook_style_name,
        "variation":  variation,
        "tone_level": tone_level,
        "text":       text[:200],
        "likes": 0, "comments": 0, "shares": 0,
        "reach": 0, "engagement_rate": 0.0, "score": 0,
    }
    history = load_history()
    history.append(record)
    save_history(history)
    return record


# ─────────────────────────────────────────────────────────────────────────────
#  UPDATE ENGAGEMENT — called by self_improve_action after fetching FB metrics
# ─────────────────────────────────────────────────────────────────────────────
def update_post_engagement(post_id: str, likes: int, comments: int,
                           shares: int, reach: int = 0):
    """Update engagement metrics for a specific post by ID."""
    history = load_history()
    for p in history:
        if p.get("post_id") == post_id:
            p["likes"]    = likes
            p["comments"] = comments
            p["shares"]   = shares
            p["reach"]    = reach
            total_eng = likes + comments + shares
            p["engagement_rate"] = round(total_eng / max(reach, 1), 4) if reach else 0
            p["score"] = score_post(p)
            break
    save_history(history)


# ─────────────────────────────────────────────────────────────────────────────
#  SCORING
# ─────────────────────────────────────────────────────────────────────────────
def score_post(post: dict) -> int:
    """
    Score 0-100 based on engagement.
    Comments worth 3x, shares 2x, likes 1x.
    """
    likes    = post.get("likes", 0)
    comments = post.get("comments", 0)
    shares   = post.get("shares", 0)
    weighted = (likes * 1) + (comments * 3) + (shares * 2)
    # Normalize: assume 100 weighted = score 100
    return min(100, int(weighted))


# ─────────────────────────────────────────────────────────────────────────────
#  HOOK PERFORMANCE — compare which hooks work best
# ─────────────────────────────────────────────────────────────────────────────
def compare_hooks(history: list) -> dict:
    """
    Returns hook performance sorted by avg score.
    {'Curiosity Gap': {'posts': 5, 'avg_score': 23, 'avg_comments': 2.1}}
    """
    hooks = defaultdict(lambda: {"posts": 0, "total_score": 0,
                                  "total_comments": 0, "total_shares": 0})
    for p in history:
        h = p.get("hook_style", "Unknown")
        hooks[h]["posts"] += 1
        hooks[h]["total_score"]    += p.get("score", 0)
        hooks[h]["total_comments"] += p.get("comments", 0)
        hooks[h]["total_shares"]   += p.get("shares", 0)

    result = {}
    for h, d in hooks.items():
        n = max(d["posts"], 1)
        result[h] = {
            "posts":        d["posts"],
            "avg_score":    round(d["total_score"] / n, 1),
            "avg_comments": round(d["total_comments"] / n, 1),
            "avg_shares":   round(d["total_shares"] / n, 1),
        }
    return dict(sorted(result.items(),
                key=lambda x: x[1]["avg_score"], reverse=True))


# ─────────────────────────────────────────────────────────────────────────────
#  TIME SLOT PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────
def compare_time_slots(history: list) -> dict:
    slots = defaultdict(lambda: {"posts": 0, "total_score": 0})
    for p in history:
        slot = p.get("slot", "unknown")
        slots[slot]["posts"] += 1
        slots[slot]["total_score"] += p.get("score", 0)

    return {
        s: {
            "posts":     d["posts"],
            "avg_score": round(d["total_score"] / max(d["posts"], 1), 1)
        }
        for s, d in slots.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
#  NICHE PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────
def compare_niches(history: list) -> dict:
    niches = defaultdict(lambda: {"posts": 0, "total_score": 0})
    for p in history:
        n = p.get("niche", "Unknown")
        niches[n]["posts"] += 1
        niches[n]["total_score"] += p.get("score", 0)

    return {
        n: {
            "posts":     d["posts"],
            "avg_score": round(d["total_score"] / max(d["posts"], 1), 1)
        }
        for n, d in niches.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
#  WINNER / LOSER DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def detect_winners(history: list, min_posts: int = 3) -> dict:
    """
    Detect winning patterns (hooks, niches, slots, languages).
    Only considers items with min_posts posts.
    """
    hook_perf  = compare_hooks(history)
    niche_perf = compare_niches(history)
    slot_perf  = compare_time_slots(history)

    winning_hooks  = [h for h, d in hook_perf.items()
                      if d["posts"] >= min_posts and d["avg_score"] >= 10][:3]
    weak_hooks     = [h for h, d in hook_perf.items()
                      if d["posts"] >= min_posts and d["avg_score"] < 5][:3]
    winning_niches = [n for n, d in niche_perf.items()
                      if d["posts"] >= min_posts and d["avg_score"] >= 10][:2]
    best_slot      = max(slot_perf, key=lambda x: slot_perf[x]["avg_score"],
                         default="morning")

    return {
        "winning_hooks":  winning_hooks,
        "weak_hooks":     weak_hooks,
        "winning_niches": winning_niches,
        "best_slot":      best_slot,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  CONVENIENCE STATS (used by app.py sidebar + dashboard)
# ─────────────────────────────────────────────────────────────────────────────
def posts_today(history: list) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for p in history if p.get("time", "").startswith(today))


def posts_this_week(history: list) -> int:
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    return sum(1 for p in history
               if p.get("time", "")[:10] >= week_ago)


def hook_performance_summary(history: list) -> dict:
    return {h: {"count": d["posts"]} for h, d in compare_hooks(history).items()}


def niche_usage_summary(history: list) -> dict:
    return {n: d["posts"] for n, d in compare_niches(history).items()}


def variation_usage_summary(history: list) -> dict:
    variations = defaultdict(int)
    for p in history:
        variations[p.get("variation", "Unknown")] += 1
    return dict(variations)


def tone_distribution(history: list) -> dict:
    buckets = {"Safe (1-3)": 0, "Balanced (4-6)": 0, "Aggressive (7-10)": 0}
    for p in history:
        tone = p.get("tone_level")
        if tone is None:
            continue
        if tone <= 3:
            buckets["Safe (1-3)"] += 1
        elif tone <= 6:
            buckets["Balanced (4-6)"] += 1
        else:
            buckets["Aggressive (7-10)"] += 1
    return buckets
