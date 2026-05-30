# ═══════════════════════════════════════════════════════════════════════════
#  engine.py — Viral Content Generation Engine (Unified Gemini Edition)
# ═══════════════════════════════════════════════════════════════════════════

import time
import google.generativeai as genai
import random
import requests
import os

# ─────────────────────────────────────────────────────────────────────────────
#  HOOK STYLES LIBRARY (Psychology-backed)
# ─────────────────────────────────────────────────────────────────────────────
HOOK_STYLES = [
    {"id": "curiosity", "name": "🔍 Curiosity Gap", "psychology": "Creates an information gap"},
    {"id": "controversy", "name": "🔥 Controversy", "psychology": "Challenges existing beliefs"},
    {"id": "fear", "name": "😨 Fear / Loss Aversion", "psychology": "Loss aversion focus"},
    {"id": "authority", "name": "🎓 Authority + Data", "psychology": "Social proof & credibility"},
    {"id": "relatable_pain", "name": "💔 Relatable Pain", "psychology": "Deep understanding"},
    {"id": "bold_claim", "name": "⚡ Bold Claim", "psychology": "Pattern interrupt"},
    {"id": "story", "name": "📖 Story Hook", "psychology": "Narrative arc compulsion"},
    {"id": "list_promise", "name": "📋 List / Number", "psychology": "Cognitive ease"},
    {"id": "question", "name": "❓ Provocative Question", "psychology": "Open loops"},
    {"id": "shocking_stat", "name": "📊 Shocking Statistic", "psychology": "Social comparison"},
    {"id": "direct_callout", "name": "👉 Direct Call-Out", "psychology": "Eliminates the scroll"},
    {"id": "transformation", "name": "🔄 Transformation", "psychology": "Aspiration & hope"},
]

# ─────────────────────────────────────────────────────────────────────────────
#  NICHE PROFILES
# ─────────────────────────────────────────────────────────────────────────────
NICHE_PROFILES = {
    "AI & Tech": {
        "tone": "futuristic, insightful",
        "ctas": ["Follow for daily AI tools ⚡", "Comment 'TOOLS' for my toolkit 🤖"],
        "emojis": "⚡🤖🧠💡",
    },
    "Motivation": {
        "tone": "raw, emotional, punchy",
        "ctas": ["Follow if you're building something great 🔥", "Drop a '🔥' if this hit."],
        "emojis": "🔥💪🧠✨",
    },
    "ASMR / Satisfying": {
        "tone": "calming, sensory",
        "ctas": ["Follow for daily calm 😌", "Save this for tonight."],
        "emojis": "😌✨💙🎧",
    },
    "Business": {
        "tone": "practical, strategic",
        "ctas": ["Follow for business strategies 📈", "Comment 'SCALE' to grow."],
        "emojis": "📈💰🎯🤝",
    }
}

# ─────────────────────────────────────────────────────────────────────────────
#  AI GENERATION (Gemini 3.5 Flash Unified)
# ─────────────────────────────────────────────────────────────────────────────
def call_gemini(prompt: str, api_key: str, model_name: str = "gemini-1.5-flash") -> str:
    """Unified call to Gemini API."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        return ""

def generate_single(niche: str, hook_style: dict, variation: str, tone_level: int, api_key: str, language: str = "Roman Urdu", max_retries: int = 3) -> dict:
    """Generates a single viral post using Gemini."""
    profile = NICHE_PROFILES.get(niche, NICHE_PROFILES["AI & Tech"])
    
    prompt = f"""
    You are a world-class viral content creator specializing in the Pakistani market.
    Your mission is to write a high-engagement Facebook post.
    
    NICHE: {niche}
    HOOK STYLE: {hook_style['name']}
    VARIATION: {variation}
    TONE: {tone_level}/10 ({profile['tone']})
    LANGUAGE: {language} (Use natural, conversational Roman Urdu/Hinglish)
    
    STRUCTURE:
    1. Hook: A punchy opening line that stops the scroll.
    2. Value: 2-3 short paragraphs of deep insight or value.
    3. Punch: A strong emotional or logical closing statement.
    4. CTA: A clear call to action from this list: {profile['ctas']}
    
    RULES:
    - Use Roman Urdu/Hinglish (e.g., 'Yaar', 'Suno', 'Kya tumne dekha?').
    - NO generic motivational fluff.
    - Max 12 words per line.
    - Use 3-5 emojis naturally.
    - Add 3-5 relevant hashtags including #Pakistan.
    
    Return ONLY the post text.
    """
    
    for attempt in range(max_retries):
        text = call_gemini(prompt, api_key)
        if text and len(text) > 100:
            return {"text": text, "success": True}
        time.sleep(1)
        
    return {"text": "", "success": False, "error": "Generation failed after retries"}

# ─────────────────────────────────────────────────────────────────────────────
#  IMAGE & TTS (Gemini/Pollinations)
# ─────────────────────────────────────────────────────────────────────────────
def generate_and_download_image(niche: str, post_text: str, api_key: str) -> bytes | None:
    """Generates an image using a 'Dark Aesthetic' prompt engineered by Gemini."""
    system_prompt = "You are a professional AI image prompt engineer. Write a 'Dark Aesthetic' Stable Diffusion prompt for this post. No text in image. Cinematic, 8k, dramatic lighting."
    user_input = f"Niche: {niche}\nPost: {post_text[:200]}"
    
    image_prompt = call_gemini(f"{system_prompt}\n\n{user_input}", api_key)
    if not image_prompt:
        image_prompt = f"Dark aesthetic cinematic photo for {niche}, dramatic lighting, 8k, no text"
        
    import urllib.parse
    encoded = urllib.parse.quote(image_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&nologo=true&model=flux"
    
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.content
    except Exception as e:
        print(f"Image Error: {e}")
    return None

def generate_tts_voice(text: str, output_path: str):
    """Placeholder for Gemini-based TTS integration (or edge-tts fallback)."""
    # Using edge-tts as it's the most reliable for Roman Urdu/Hinglish currently in sandbox
    import asyncio
    import edge_tts
    
    async def _gen():
        communicate = edge_tts.Communicate(text, "ur-PK-AsadNeural")
        await communicate.save(output_path)
        
    asyncio.run(_gen())

def post_image_to_facebook(page_id: str, page_token: str, image_bytes: bytes, caption: str) -> dict:
    """Posts image to Facebook."""
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/photos",
            data={"caption": caption, "access_token": page_token, "published": "true"},
            files={"source": ("post.jpg", image_bytes, "image/jpeg")},
            timeout=60,
        )
        data = r.json()
        if "id" in data:
            return {"success": True, "id": data["id"]}
        return {"success": False, "error": data.get("error", {}).get("message", str(data))}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_hook_by_id(hook_id: str) -> dict:
    for h in HOOK_STYLES:
        if h["id"] == hook_id:
            return h
    return HOOK_STYLES[0]
