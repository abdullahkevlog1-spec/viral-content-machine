import json
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
LOG_PATH = DATA_DIR / "post_log.json"
OUTPUT_PATH = DATA_DIR / "self_improve_report.json"


def analyze_post_logs(logs):
    if not logs:
        return {
            "total_posts": 0,
            "niches": [],
            "last_post": None,
            "status": "no_data"
        }

    niches = set()
    last_post = logs[-1] if logs else None

    for log in logs:
        niche = log.get("niche")
        if isinstance(niche, list):
            niches.update(niche)
        elif niche:
            niches.add(niche)

    return {
        "total_posts": len(logs),
        "niches": list(niches),
        "last_post": last_post,
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    }


def main():
    try:
        if LOG_PATH.exists():
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []

        report = analyze_post_logs(logs)

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print("self_improve_report.json updated")

    except Exception as e:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"error": str(e)}, f, indent=2)
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
