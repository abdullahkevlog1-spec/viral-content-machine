import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

POST_LOG_PATH = DATA_DIR / "post_log.json"
ANALYTICS_PATH = DATA_DIR / "fb_analytics.json"
OUTPUT_PATH = DATA_DIR / "strategy_state.json"


def load_json(path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def get_best(counter, fallback):
    if not counter:
        return fallback
    return counter.most_common(1)[0][0]


def main():
    logs = load_json(POST_LOG_PATH, [])
    analytics = load_json(ANALYTICS_PATH, {})
    existing = load_json(OUTPUT_PATH, {})

    successful_logs = [log for log in logs if log.get("status") == "success"]

    hook_counter = Counter()
    niche_counter = Counter()
    style_counter = Counter()
    slot_counter = Counter()
    language_counter = Counter()

    for log in successful_logs:
        if log.get("hook_id"):
            hook_counter[log["hook_id"]] += 1
        if log.get("niche"):
            niche_counter[log["niche"]] += 1
        if log.get("variation"):
            style_counter[log["variation"]] += 1
        if log.get("slot"):
            slot_counter[log["slot"]] += 1
        if log.get("language"):
            language_counter[log["language"]] += 1

    score = analytics.get("score", 0)

    hook_weights = existing.get("hook_weights", {
        "curiosity": 1.0,
        "bold_claim": 1.0,
        "relatable_pain": 1.0,
        "controversy": 1.0,
        "authority": 1.0,
    })

    niche_weights = existing.get("niche_weights", {
        "AI & Tech": 1.0,
        "Motivation": 1.0,
        "ASMR / Satisfying": 1.0,
        "Business": 1.0,
    })

    state = {
        "best_hook": get_best(hook_counter, "curiosity"),
        "best_niche": get_best(niche_counter, "AI & Tech"),
        "best_style": get_best(style_counter, "Bold/Controversial"),
        "best_slot": get_best(slot_counter, "morning"),
        "best_language": get_best(language_counter, "English"),
        "hook_weights": hook_weights,
        "niche_weights": niche_weights,
        "successful_posts": len(successful_logs),
        "total_posts": len(logs),
        "latest_score": score,
        "learning_status": "active",
        "version": existing.get("version", 1),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print("strategy_state.json updated")


if __name__ == "__main__":
    main()
