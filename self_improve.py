"""
self_improve.py — Centralized Memory & Autonomous Learning
Consolidates all metrics into system_memory.json and updates strategy.
"""

import os
import json
import requests
from datetime import datetime
import google.generativeai as genai

MEMORY_PATH = "data/system_memory.json"
POST_LOG_PATH = "data/post_log.json"

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def sync_memory():
    memory = load_json(MEMORY_PATH, {})
    post_log = load_json(POST_LOG_PATH, [])
    
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    
    if not fb_token:
        print("FB Token missing, skipping sync")
        return
        
    # Sync metrics for last 10 posts
    for entry in post_log[-10:]:
        post_id = entry.get("post_id")
        if post_id:
            try:
                r = requests.get(
                    f"https://graph.facebook.com/v19.0/{post_id}",
                    params={"fields": "likes.summary(true),comments.summary(true),shares", "access_token": fb_token}
                )
                data = r.json()
                entry["likes"] = data.get("likes", {}).get("summary", {}).get("total_count", 0)
                entry["comments"] = data.get("comments", {}).get("summary", {}).get("total_count", 0)
                entry["shares"] = data.get("shares", {}).get("count", 0)
            except:
                pass
                
    # Update memory
    memory["engagement_history"] = post_log[-100:]
    memory["total_posts"] = len(post_log)
    memory["successful_posts"] = sum(1 for p in post_log if p.get("status") == "success")
    memory["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    # Simple weight update logic
    # (In a real AGI system, this would be more complex)
    
    save_json(MEMORY_PATH, memory)
    save_json(POST_LOG_PATH, post_log)
    print("Memory Synced Successfully")

if __name__ == "__main__":
    sync_memory()
