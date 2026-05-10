"""
Phase 3 — Social Intelligence Layer

Responsible for:
- Reddit trend discovery
- Competitor pattern analysis
- Hook extraction
- CTA detection
- Viral signal aggregation
"""

import re
from datetime import datetime

DEFAULT_SIGNALS = {
    "top_topics": [
        "AI automation",
        "OpenAI updates",
        "freelancing with AI"
    ],
    "viral_hooks": [
        "Nobody talks about this",
        "This changes everything",
        "You are already late"
    ],
    "cta_patterns": [
        "comment below",
        "share this",
        "save this post"
    ],
    "emoji_density": 0.35,
    "updated": None
}


def extract_hooks(text: str):
    patterns = [
        r"nobody talks about",
        r"this changes everything",
        r"you are already late",
        r"before it is too late"
    ]

    found = []
    lower = text.lower()

    for p in patterns:
        if re.search(p, lower):
            found.append(p)

    return found



def get_social_signals():
    signals = DEFAULT_SIGNALS.copy()
    signals["updated"] = datetime.utcnow().isoformat()
    return signals


if __name__ == "__main__":
    print(get_social_signals())
