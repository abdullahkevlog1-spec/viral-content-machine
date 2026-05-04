"""
self_improve.py — Daily Self-Improvement Engine
Detects pain points, analyzes performance, generates AI report with 1-click fixes.
"""

import os
import json
import requests
from datetime import datetime, timedelta

GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
REPORT_FILE  = "self_improve_report.json"
LOG_FILE     = "schedule_log.json"
HISTORY_FILE = "fb_history.json"


# ─────────────────────────────────────────────────────────────────────────────
#  DATA COLLECTORS
# ─────────────────────────────────────────────────────────────────────────────
def collect_schedule_errors() -> dict:
    """Parse schedule log for failures and patterns."""
    if not os.path.exists(LOG_FILE):
        return {"total": 0, "failed": 0, "errors": [], "success_rate": 100}

    with open(LOG_FILE, "r") as f:
        try:
            logs = json.load(f)
        except Exception:
            return {"total": 0, "failed": 0, "errors": [], "success_rate": 100}

    total   = len(logs)
    failed  = [l for l in logs if "FAILED" in l.get("status", "") or "ERROR" in l.get("status", "")]
    errors  = list({l.get("status", "") for l in failed})[:5]
    success_rate = round((1 - len(failed) / max(total, 1)) * 100, 1)

    return {
        "total":        total,
        "failed":       len(failed),
        "errors":       errors,
        "success_rate": success_rate,
        "recent_logs":  logs[:5],
    }


def collect_post_history() -> dict:
    """Analyze post history for patterns."""
    if not os.path.exists(HISTORY_FILE):
        return {"total_posts": 0, "niches": {}, "hooks": {}, "variations": {}}

    with open(HISTORY_FILE, "r") as f:
        try:
            history = json.load(f)
        except Exception:
            return {"total_posts": 0, "niches": {}, "hooks": {}, "variations": {}}

    niches     = {}
    hooks      = {}
    variations = {}
    today      = datetime.now().strftime("%Y-%m-%d")
    week_ago   = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    this_week  = 0

    for p in history:
        n = p.get("niche") or p.get("type", "Unknown")
        niches[n] = niches.get(n, 0) + 1

        h = p.get("hook_style", "Unknown")
        hooks[h] = hooks.get(h, 0) + 1

        v = p.get("variation", "Unknown")
        variations[v] = variations.get(v, 0) + 1

        t = p.get("time", "")
        if t[:10] >= week_ago:
            this_week += 1

    return {
        "total_posts": len(history),
        "this_week":   this_week,
        "niches":      niches,
        "hooks":       hooks,
        "variations":  variations,
    }


def fetch_facebook_insights(page_id: str, page_token: str) -> dict:
    """Fetch recent post insights from Facebook Graph API."""
    if not page_id or not page_token:
        return {"error": "No credentials", "posts": []}

    try:
        # Get recent posts
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{page_id}/posts",
            params={
                "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
                "limit": 10,
                "access_token": page_token,
            },
            timeout=15,
        )
        data = r.json()
        if "error" in data:
            return {"error": data["error"].get("message", "FB error"), "posts": []}

        posts = []
        for p in data.get("data", []):
            posts.append({
                "id":       p.get("id"),
                "preview":  (p.get("message") or "")[:80],
                "time":     p.get("created_time", "")[:10],
                "likes":    p.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": p.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares":   p.get("shares", {}).get("count", 0),
            })

        total_likes    = sum(p["likes"]    for p in posts)
        total_comments = sum(p["comments"] for p in posts)
        total_shares   = sum(p["shares"]   for p in posts)
        avg_engagement = round((total_likes + total_comments + total_shares) / max(len(posts), 1), 1)

        return {
            "posts":           posts,
            "avg_engagement":  avg_engagement,
            "total_likes":     total_likes,
            "total_comments":  total_comments,
            "total_shares":    total_shares,
            "best_post":       max(posts, key=lambda x: x["likes"] + x["comments"], default=None),
            "worst_post":      min(posts, key=lambda x: x["likes"] + x["comments"], default=None),
        }
    except Exception as e:
        return {"error": str(e), "posts": []}


# ─────────────────────────────────────────────────────────────────────────────
#  AI ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def generate_ai_report(schedule_data: dict, history_data: dict,
                       fb_data: dict, groq_key: str) -> dict:
    """
    Use Groq to analyze all data and generate improvement suggestions.
    Returns structured report with actionable fixes.
    """
    if not groq_key:
        return {"error": "No Groq API key", "suggestions": []}

    # Build analysis context
    context = f"""
SYSTEM PERFORMANCE DATA — AI with Abdullah Facebook Page:

SCHEDULE LOG:
- Total auto-posts attempted: {schedule_data['total']}
- Failed: {schedule_data['failed']}
- Success rate: {schedule_data['success_rate']}%
- Recent errors: {', '.join(schedule_data['errors'][:3]) if schedule_data['errors'] else 'None'}

POST HISTORY:
- Total posts ever: {history_data['total_posts']}
- Posts this week: {history_data['this_week']}
- Niche breakdown: {json.dumps(history_data['niches'])}
- Hook usage: {json.dumps(history_data['hooks'])}
- Variation usage: {json.dumps(history_data['variations'])}

FACEBOOK ENGAGEMENT:
- Avg engagement per post: {fb_data.get('avg_engagement', 'N/A')}
- Total likes (last 10 posts): {fb_data.get('total_likes', 'N/A')}
- Total comments: {fb_data.get('total_comments', 'N/A')}
- Total shares: {fb_data.get('total_shares', 'N/A')}
- Best post preview: {fb_data.get('best_post', {}).get('preview', 'N/A') if fb_data.get('best_post') else 'N/A'}
- Worst post preview: {fb_data.get('worst_post', {}).get('preview', 'N/A') if fb_data.get('worst_post') else 'N/A'}
- FB errors: {fb_data.get('error', 'None')}
"""

    prompt = f"""You are an AI system analyst for a Facebook auto-posting system called "Viral Content Machine".

Analyze this performance data and generate exactly 5 improvement suggestions.

{context}

Return ONLY a valid JSON array with exactly 5 objects. Each object must have:
- "priority": "HIGH" | "MEDIUM" | "LOW"
- "category": "content" | "technical" | "schedule" | "engagement" | "design"  
- "problem": (1 sentence — what issue was detected)
- "suggestion": (1 sentence — what to change)
- "action": (exactly what to do — specific and actionable)
- "impact": (expected result if implemented)

Be specific about what data you detected. Reference actual numbers from the data.
Return ONLY the JSON array. No explanation. No markdown."""

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 1200,
            },
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            timeout=30,
        )
        if r.status_code != 200:
            return {"error": f"Groq error {r.status_code}", "suggestions": []}

        raw = r.json()["choices"][0]["message"]["content"].strip()
        # Clean JSON
        raw = raw.replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(raw)
        return {"suggestions": suggestions, "error": None}

    except Exception as e:
        return {"error": str(e), "suggestions": []}


# ─────────────────────────────────────────────────────────────────────────────
#  FULL REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_full_report(page_id: str, page_token: str, groq_key: str) -> dict:
    """
    Master function — collect all data, run AI analysis, save report.
    """
    print("📊 Collecting schedule logs...")
    schedule_data = collect_schedule_errors()

    print("📜 Analyzing post history...")
    history_data = collect_post_history()

    print("📱 Fetching Facebook insights...")
    fb_data = fetch_facebook_insights(page_id, page_token)

    print("🧠 Running AI analysis...")
    ai_report = generate_ai_report(schedule_data, history_data, fb_data, groq_key)

    report = {
        "generated_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "schedule":      schedule_data,
        "history":       history_data,
        "facebook":      fb_data,
        "suggestions":   ai_report.get("suggestions", []),
        "ai_error":      ai_report.get("error"),
        "implemented":   [],  # Track which suggestions were approved+implemented
    }

    # Save report
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    print(f"✅ Report saved: {len(report['suggestions'])} suggestions generated")
    return report


def load_report() -> dict | None:
    """Load existing report from disk."""
    if not os.path.exists(REPORT_FILE):
        return None
    try:
        with open(REPORT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def mark_implemented(suggestion_index: int):
    """Mark a suggestion as implemented."""
    report = load_report()
    if not report:
        return
    implemented = report.get("implemented", [])
    if suggestion_index not in implemented:
        implemented.append(suggestion_index)
    report["implemented"] = implemented
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
