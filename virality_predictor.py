"""
Phase 3 — Virality Prediction Engine
"""

import math


def predict_virality(post_data: dict):
    score = 50

    text = post_data.get("text", "").lower()
    trend_score = post_data.get("trend_score", 0)
    hook_weight = post_data.get("hook_weight", 1)

    if "ai" in text:
        score += 10

    if "openai" in text:
        score += 10

    score += trend_score * 0.2
    score += hook_weight * 10

    score = min(100, round(score))

    return {
        "score": score,
        "confidence": round(min(0.95, score / 100), 2)
    }


if __name__ == "__main__":
    sample = {
        "text": "OpenAI changes everything",
        "trend_score": 80,
        "hook_weight": 1.8
    }

    print(predict_virality(sample))
