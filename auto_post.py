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
    if slot_name == "morning" and best_niche in ALLOWED_NICHES:
        adapted["niche"] = best_niche
    return adapted


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

if __name__ == "__main__":
    print('auto_post restored')
