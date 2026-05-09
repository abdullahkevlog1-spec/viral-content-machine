"""
memory_manager.py — System Memory + Strategy State
Tracks what works, what doesn't, updates strategy weights.
Phase 1: Core memory read/write. Phase 3+: auto-weight updates.
"""

import json
import os
from datetime import datetime

os.makedirs("data", exist_ok=True)

STRATEGY_FILE = "data/strategy_state.json"
MEMORY_FILE   = "data/content_memory.json"


# ─────────────────────────────────────────────────────────────────────────────
#  DEFAULT STATE
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_STRATEGY = {
    "version":  1,
    "updated":  datetime.now().strftime("%Y-%m-%d"),

    # Hook weights — higher = use more often
    "hook_weights": {
        "curiosity":       1.0,
        "bold_claim":      1.0,
        "relatable_pain":  1.0,
        "controversy":     1.0,
        "fear_loss":       1.0,
        "authority_data":  1.0,
        "story":           1.0,
        "shocking_stat":   1.0,
        "question":        1.0,
        "transformation":  1.0,
    },

    # Niche weights
    "niche_weights": {
        "AI & Tech":         1.0,
        "Motivation":        1.0,
        "ASMR / Satisfying": 1.0,
        "News & Trends":     1.0,
    },

    # Slot preferences
    "slot_weights": {
        "morning":   1.0,
        "trending":  1.0,
        "afternoon": 1.0,
        "evening":   1.0,
    },

    # Language preferences
    "language_weights": {
        "English":    1.0,
        "Roman Urdu": 1.0,
        "Hinglish":   1.0,
    },

    # Format preferences
    "format_weights": {
        "carousel":   1.0,
        "text_only":  0.5,
        "single_img": 0.8,
    },

    # Variation preferences
    "variation_weights": {
        "Emotional":          1.0,
        "Educational":        1.0,
        "Bold/Controversial": 1.0,
    },

    # Tone preference
    "preferred_tone_range": [5, 8],

    # Content rules learned from performance
    "content_rules": {
        "min_post_length":     150,
        "preferred_frameworks": [],
        "banned_patterns":     [],
        "boost_patterns":      [],
    },

    # Topics that perform well
    "winning_topics":  [],
    "failing_topics":  [],

    # Experiment tracking
    "total_experiments": 0,
    "last_update":       datetime.now().strftime("%Y-%m-%d %H:%M"),
}

DEFAULT_MEMORY = {
    "winning_hooks":    [],
    "weak_hooks":       [],
    "winning_niches":   [],
    "winning_formats":  ["carousel"],
    "best_languages":   ["Roman Urdu", "Hinglish"],
    "best_slots":       ["evening", "morning"],
    "best_ctas":        ["comment", "save"],
    "learned_patterns": [],
    "last_updated":     datetime.now().strftime("%Y-%m-%d %H:%M"),
}


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD / SAVE
# ─────────────────────────────────────────────────────────────────────────────
def load_strategy() -> dict:
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE, "r") as f:
                s = json.load(f)
                # Merge with defaults for any missing keys
                for k, v in DEFAULT_STRATEGY.items():
                    if k not in s:
                        s[k] = v
                return s
        except Exception:
            pass
    # First run — create default
    save_strategy(DEFAULT_STRATEGY.copy())
    return DEFAULT_STRATEGY.copy()


def save_strategy(strategy: dict):
    strategy["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(STRATEGY_FILE, "w") as f:
        json.dump(strategy, f, indent=2, ensure_ascii=False)


def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    save_memory(DEFAULT_MEMORY.copy())
    return DEFAULT_MEMORY.copy()


def save_memory(memory: dict):
    memory["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
#  WEIGHT UPDATER — called by learning engine
# ─────────────────────────────────────────────────────────────────────────────
def boost_hook(hook_id: str, amount: float = 0.1):
    """Increase weight of a winning hook."""
    s = load_strategy()
    current = s["hook_weights"].get(hook_id, 1.0)
    s["hook_weights"][hook_id] = min(2.0, round(current + amount, 2))
    save_strategy(s)


def penalize_hook(hook_id: str, amount: float = 0.1):
    """Decrease weight of a weak hook."""
    s = load_strategy()
    current = s["hook_weights"].get(hook_id, 1.0)
    s["hook_weights"][hook_id] = max(0.3, round(current - amount, 2))
    save_strategy(s)


def boost_niche(niche: str, amount: float = 0.1):
    s = load_strategy()
    current = s["niche_weights"].get(niche, 1.0)
    s["niche_weights"][niche] = min(2.0, round(current + amount, 2))
    save_strategy(s)


def update_memory_from_winners(winners: dict):
    """Update content memory from detected winners."""
    m = load_memory()
    if winners.get("winning_hooks"):
        m["winning_hooks"] = winners["winning_hooks"]
    if winners.get("weak_hooks"):
        m["weak_hooks"] = winners["weak_hooks"]
    if winners.get("winning_niches"):
        m["winning_niches"] = winners["winning_niches"]
    if winners.get("best_slot"):
        if winners["best_slot"] not in m["best_slots"]:
            m["best_slots"].insert(0, winners["best_slot"])
            m["best_slots"] = m["best_slots"][:3]
    save_memory(m)


# ─────────────────────────────────────────────────────────────────────────────
#  STRATEGY SUMMARY — for UI display + prompt injection
# ─────────────────────────────────────────────────────────────────────────────
def get_strategy_summary() -> dict:
    """Human-readable strategy summary for dashboard display."""
    s = load_strategy()
    m = load_memory()

    # Top hooks by weight
    sorted_hooks = sorted(
        s["hook_weights"].items(), key=lambda x: x[1], reverse=True
    )
    top_hooks    = [h for h, _ in sorted_hooks[:3]]
    weak_hooks   = [h for h, w in sorted_hooks if w < 0.7]

    # Top niches
    sorted_niches = sorted(
        s["niche_weights"].items(), key=lambda x: x[1], reverse=True
    )

    return {
        "top_hooks":         top_hooks,
        "weak_hooks":        weak_hooks,
        "top_niche":         sorted_niches[0][0] if sorted_niches else "AI & Tech",
        "preferred_formats": [f for f, w in sorted(
            s["format_weights"].items(), key=lambda x: x[1], reverse=True)[:2]],
        "memory":            m,
        "version":           s["version"],
        "last_updated":      s["last_update"],
    }


def get_prompt_context() -> str:
    """
    Returns strategy context string to inject into prompts.
    Makes generation strategy-aware.
    """
    m = load_memory()
    s = load_strategy()

    winning = m.get("winning_hooks", [])
    weak    = m.get("weak_hooks", [])

    lines = []
    if winning:
        lines.append(f"HIGH PERFORMING HOOKS (use more): {', '.join(winning)}")
    if weak:
        lines.append(f"LOW PERFORMING HOOKS (avoid): {', '.join(weak)}")
    if m.get("best_slots"):
        lines.append(f"BEST POSTING TIMES: {', '.join(m['best_slots'])}")

    return "\n".join(lines) if lines else ""
