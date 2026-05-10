"""
prompt_optimizer.py — Real Prompt Intelligence Layer

Purpose:
- Analyze historical post performance
- Detect winning hooks/patterns
- Evolve future prompts automatically
- Improve emotional structure over time

This is NOT a decorative module.
It directly transforms future prompt generation.
"""

import json
import os
from collections import Counter
from datetime import datetime

DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "optimized_prompt_profile.json")


DEFAULT_PROFILE = {
    "best_hooks": ["curiosity"],
    "best_ctas": ["comment below"],
    "best_styles": ["short punchy"],
    "best_openings": ["Nobody talks about this"],
    "avg_score": 50,
    "updated": None
}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []



def save_profile(profile):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

def calculate_post_score(post):
    likes = post.get("likes", 0)
    comments = post.get("comments", 0)
    shares = post.get("shares", 0)

    weighted = likes + (comments * 3) + (shares * 4)

    return weighted


# ─────────────────────────────────────────────
# CORE LEARNING ENGINE
# ─────────────────────────────────────────────

def analyze_history():
    history = load_history()

    if not history:
        profile = DEFAULT_PROFILE.copy()
        profile["updated"] = datetime.utcnow().isoformat()
        save_profile(profile)
        return profile

    scored = []

    for post in history:
        score = calculate_post_score(post)
        post["_score"] = score
        scored.append(post)

    scored.sort(key=lambda x: x.get("_score", 0), reverse=True)

    top = scored[: min(20, len(scored))]

    hooks = []
    ctas = []
    styles = []
    openings = []
    scores = []

    for post in top:
        if post.get("hook_style"):
            hooks.append(post["hook_style"])

        if post.get("cta"):
            ctas.append(post["cta"])

        if post.get("style"):
            styles.append(post["style"])

        text = post.get("text", "")

        if text:
            first_line = text.split("\n")[0][:80]
            openings.append(first_line)

        scores.append(post.get("_score", 0))

    profile = {
        "best_hooks": [x[0] for x in Counter(hooks).most_common(3)] or DEFAULT_PROFILE["best_hooks"],
        "best_ctas": [x[0] for x in Counter(ctas).most_common(3)] or DEFAULT_PROFILE["best_ctas"],
        "best_styles": [x[0] for x in Counter(styles).most_common(3)] or DEFAULT_PROFILE["best_styles"],
        "best_openings": openings[:5] or DEFAULT_PROFILE["best_openings"],
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 50,
        "updated": datetime.utcnow().isoformat()
    }

    save_profile(profile)

    return profile


# ─────────────────────────────────────────────
# PROMPT EVOLUTION
# ─────────────────────────────────────────────

def build_optimized_prompt(topic, niche="AI"):
    profile = analyze_history()

    hook = profile["best_hooks"][0]
    cta = profile["best_ctas"][0]
    style = profile["best_styles"][0]
    opening = profile["best_openings"][0]

    prompt = f"""
Create a highly engaging Facebook post.

Topic: {topic}
Niche: {niche}

Requirements:
- Use hook style: {hook}
- Writing style: {style}
- Strong emotional pacing
- Keep sentences concise
- Use a viral-style opening similar to: '{opening}'
- End with CTA: '{cta}'
- Avoid generic AI wording
- Sound natural and social-media native
- Optimize for comments and shares
"""

    return {
        "prompt": prompt.strip(),
        "profile_used": profile
    }


# ─────────────────────────────────────────────
# SELF EVOLUTION SIGNAL
# ─────────────────────────────────────────────

def evolve_prompt_strategy():
    profile = analyze_history()

    evolution = {
        "recommended_hook": profile["best_hooks"][0],
        "recommended_style": profile["best_styles"][0],
        "recommended_cta": profile["best_ctas"][0],
        "confidence": min(0.95, profile["avg_score"] / 100),
        "updated": datetime.utcnow().isoformat()
    }

    return evolution


# ─────────────────────────────────────────────
# DEBUG
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(analyze_history())

    sample = build_optimized_prompt(
        topic="OpenAI changes freelancing forever",
        niche="AI"
    )

    print("\nOPTIMIZED PROMPT:\n")
    print(sample["prompt"])
