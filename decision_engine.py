"""Autonomous Decision Engine"""

import random
from trend_engine import get_best_trend
from social_listener import get_social_signals

HOOKS = [
    "curiosity",
    "fear_of_missing_out",
    "authority",
    "controversy"
]

NICHES = [
    "AI",
    "business",
    "motivation",
    "freelancing"
]


def decide_next_strategy():
    trend = get_best_trend()
    social = get_social_signals()

    hook = random.choice(HOOKS)
    niche = random.choice(NICHES)

    return {
        "hook": hook,
        "niche": niche,
        "trend": trend.get("topic"),
        "trend_score": trend.get("score", 50),
        "cta": social.get("cta_patterns", ["comment below"])[0],
        "viral_hook": social.get("viral_hooks", ["This changes everything"])[0]
    }


if __name__ == "__main__":
    print(decide_next_strategy())
