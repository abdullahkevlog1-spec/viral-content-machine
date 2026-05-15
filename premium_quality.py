"""
premium_quality.py — autonomous content upgrade layer.

This layer is intentionally safe:
- It never blocks posting if polishing fails.
- It preserves the selected niche, language, and CTA intent.
- It rejects generic or overly short rewrites and falls back to original text.
"""

import requests

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

BANNED_LOW_QUALITY = [
    "in today's world",
    "game changer",
    "believe in yourself",
    "never give up",
    "dream big",
    "work hard",
    "stay motivated",
    "most people don't realize",
    "unlock your potential",
    "take it to the next level",
]


def is_low_quality(text: str) -> bool:
    t = (text or "").lower().strip()
    if len(t) < 150:
        return True
    return any(p in t for p in BANNED_LOW_QUALITY)


def premium_polish_post(text: str, niche: str, language: str, api_key: str) -> str:
    """
    Upgrade raw generated copy into a more premium, less generic post.
    Returns original text if anything goes wrong.
    """
    if not text or not api_key:
        return text

    prompt = f"""You are an elite social media editor for a premium creator brand called AI with Abdullah.

Rewrite the post below so it feels premium, human, specific, and high-retention.

NICHE: {niche}
LANGUAGE: {language}

Original post:
{text}

Rewrite rules:
1. Keep the same language style exactly: {language}.
2. First 2 lines must be a strong scroll-stopping hook.
3. Remove all generic motivational filler.
4. Add concrete details, sensory language, or specific examples.
5. Keep it native to Pakistani / creator audience when relevant.
6. Make line breaks clean for Facebook reading.
7. End with a natural CTA and 3-5 relevant hashtags.
8. No labels, no explanation, no markdown headings.
9. Do NOT use these phrases: in today's world, game changer, believe in yourself, never give up, dream big, stay motivated.

Return ONLY the final post text."""

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.78,
                "max_tokens": 700,
                "top_p": 0.9,
            },
            headers={"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"},
            timeout=35,
        )
        if r.status_code != 200:
            print(f"  Premium polish skipped: Groq {r.status_code}")
            return text

        polished = r.json()["choices"][0]["message"]["content"].strip()
        if is_low_quality(polished):
            print("  Premium polish rejected by quality gate")
            return text
        return polished
    except Exception as e:
        print(f"  Premium polish failed: {e}")
        return text
