import json
import random
from pathlib import Path

FALLBACK_TRENDS = [
    {"topic": "AI automation Pakistan", "score": 80, "source": "fallback"},
    {"topic": "ChatGPT tips 2026", "score": 75, "source": "fallback"},
    {"topic": "Freelancing with AI", "score": 70, "source": "fallback"},
]


def get_best_trend() -> dict:
    try:
        cache = Path("data/trends_cache.json")
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
            trends = data.get("trends", [])
            if trends:
                return max(trends, key=lambda x: x.get("score", 0))
    except Exception:
        pass

    return random.choice(FALLBACK_TRENDS)
