"""
auto_post.py — Unified Gemini Execution Engine
Sole execution engine for scheduled posting via GitHub Actions.
"""

import os
import sys
import json
import requests
from datetime import datetime
from engine import (
    generate_single,
    generate_and_download_image,
    get_hook_by_id,
    post_image_to_facebook
)

# ── Agent Integration ──
try:
    from agent import AgentDecision
    _agent = AgentDecision()
    AGENT_ENABLED = True
except Exception as e:
    print(f"Agent Load Error: {e}")
    AGENT_ENABLED = False

SLOTS = {
    "morning": {"label": "🌅 Morning 9 AM", "niche": "AI & Tech", "hook_id": "curiosity", "tone": 7, "variation": "Bold", "language": "Roman Urdu"},
    "afternoon": {"label": "☀️ Afternoon 2 PM", "niche": "Motivation", "hook_id": "bold_claim", "tone": 8, "variation": "Controversial", "language": "Roman Urdu"},
    "evening": {"label": "🌙 Evening 9 PM", "niche": "Business", "hook_id": "relatable_pain", "tone": 6, "variation": "Educational", "language": "Roman Urdu"},
}

def run_post(slot_key: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    page_id = os.environ.get("FB_PAGE_ID")
    page_token = os.environ.get("FB_PAGE_TOKEN")
    
    missing = []
    if not api_key:
        missing.append("GEMINI_API_KEY")
    if not page_id:
        missing.append("FB_PAGE_ID")
    if not page_token:
        missing.append("FB_PAGE_TOKEN")
    
    if missing:
        print(f"Error: Missing required secrets: {', '.join(missing)}")
        print("Please configure these secrets in GitHub repository settings:")
        print("  Settings → Secrets and variables → Actions")
        sys.exit(1)
        
    slot = SLOTS.get(slot_key, SLOTS["morning"])
    
    # 1. Agent Strategy
    if AGENT_ENABLED:
        slot = _agent.get_strategy(slot, slot_key)
        
    # 2. Generation
    result = generate_single(
        niche=slot["niche"],
        hook_style=get_hook_by_id(slot["hook_id"]),
        variation=slot["variation"],
        tone_level=slot["tone"],
        api_key=api_key,
        language=slot["language"]
    )
    
    if not result["success"]:
        print("Generation Failed")
        sys.exit(1)
        
    text = result["text"]
    
    # 3. Agent Quality Gate
    if AGENT_ENABLED:
        verdict = _agent.approve(text, slot)
        if verdict["action"] == "regenerate":
            result = generate_single(niche=slot["niche"], hook_style=get_hook_by_id(slot["hook_id"]), variation=slot["variation"], tone_level=slot["tone"], api_key=api_key)
            text = result["text"]
            
    # 4. Image Generation
    img_bytes = generate_and_download_image(slot["niche"], text, api_key)
    
    # 5. Posting
    if img_bytes:
        post_res = post_image_to_facebook(page_id, page_token, img_bytes, text)
    else:
        # Fallback to text post
        post_res = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/feed",
            data={"message": text, "access_token": page_token}
        ).json()
        
    # 6. Logging
    log_entry = {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "slot": slot_key,
        "status": "success" if "id" in post_res else "failed",
        "post_id": post_res.get("id", ""),
        "text": text[:100]
    }
    
    # Commit log logic (simplified for overhaul)
    with open("data/post_log.json", "r+") as f:
        logs = json.load(f)
        logs.append(log_entry)
        f.seek(0)
        json.dump(logs[-100:], f, indent=2)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True)
    args = parser.parse_args()
    run_post(args.slot)
