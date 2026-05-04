"""
self_improve_action.py — Autonomous Self-Improvement Engine
Runs daily via GitHub Actions at 11 PM PKT.
Reads post logs, fetches FB insights, generates AI report,
commits report.json back to GitHub.
NO Streamlit needed. Fully autonomous.
"""

import os
import sys
import json
import base64
import requests
from datetime import datetime, timedelta

GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# From GitHub Secrets
GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
FB_TOKEN   = os.environ.get("FB_PAGE_TOKEN", "")
FB_PAGE    = os.environ.get("FB_PAGE_ID", "")
GH_TOKEN   = os.environ.get("GH_PAT", "")
GH_REPO    = os.environ.get("GITHUB_REPO", "abdullahkevlog1-spec/viral-content-machine")

GH_HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


# ─────────────────────────────────────────────────────────────────────────────
#  GITHUB FILE READER / WRITER
# ─────────────────────────────────────────────────────────────────────────────
def read_github_file(path: str) -> dict | list | None:
    """Read a JSON file from GitHub repo."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    r = requests.get(url, headers=GH_HEADERS, timeout=10)
    if r.status_code == 200:
        try:
            content = base64.b64decode(r.json()["content"]).decode()
            return json.loads(content)
        except Exception as e:
            print(f"  Parse error for {path}: {e}")
    return None


def write_github_file(path: str, data, message: str):
    """Write/update a JSON file in GitHub repo."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"

    # Get existing sha if file exists
    r = requests.get(url, headers=GH_HEADERS, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None

    content = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode()
    ).decode()

    payload = {"message": message, "content": content, "branch": "main"}
    if sha:
        payload["sha"] = sha

    r2 = requests.put(url, json=payload, headers=GH_HEADERS, timeout=15)
    if r2.status_code in (200, 201):
        print(f"  ✅ {path} committed")
        return True
    else:
        print(f"  ❌ Failed to commit {path}: {r2.status_code} {r2.text[:100]}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  DATA COLLECTORS
# ─────────────────────────────────────────────────────────────────────────────
def analyze_post_logs(logs: list) -> dict:
    """Analyze post_log.json for patterns."""
    if not logs:
        return {"total": 0, "success": 0, "failed": 0,
                "success_rate": 0, "errors": [], "slots": {}}

    success = [l for l in logs if l.get("status") == "success"]
    failed  = [l for l in logs if l.get("status") == "failed"]
    errors  = list({l.get("error", "") for l in failed if l.get("error")})[:5]

    # Slot breakdown
    slots = {}
    for l in logs:
        s = l.get("slot", "unknown")
        slots[s] = slots.get(s, {"success": 0, "failed": 0})
        if l.get("status") == "success":
            slots[s]["success"] += 1
        else:
            slots[s]["failed"] += 1

    # Niche breakdown
    niches = {}
    for l in success:
        n = l.get("niche", "unknown")
        niches[n] = niches.get(n, 0) + 1

    # Recent 7 days
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [l for l in logs if l.get("time", "") >= week_ago]

    return {
        "total":        len(logs),
        "success":      len(success),
        "failed":       len(failed),
        "success_rate": round(len(success) / max(len(logs), 1) * 100, 1),
        "errors":       errors,
        "slots":        slots,
        "niches":       niches,
        "recent_7d":    len(recent),
        "last_post":    logs[-1].get("time") if logs else None,
    }


def fetch_fb_insights() -> dict:
    """Fetch Facebook page post insights."""
    if not FB_TOKEN or not FB_PAGE:
        return {"error": "No FB credentials", "posts": []}

    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{FB_PAGE}/posts",
            params={
                "fields": "id,message,created_time,"
                          "likes.summary(true),"
                          "comments.summary(true),"
                          "shares",
                "limit": 15,
                "access_token": FB_TOKEN,
            },
            timeout=15,
        )
        data = r.json()
        if "error" in data:
            return {"error": data["error"].get("message"), "posts": []}

        posts = []
        for p in data.get("data", []):
            likes    = p.get("likes",    {}).get("summary", {}).get("total_count", 0)
            comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares   = p.get("shares",   {}).get("count", 0)
            posts.append({
                "id":         p.get("id"),
                "time":       p.get("created_time", "")[:10],
                "preview":    (p.get("message") or "")[:80],
                "likes":      likes,
                "comments":   comments,
                "shares":     shares,
                "engagement": likes + comments + shares,
            })

        posts.sort(key=lambda x: x["engagement"], reverse=True)

        return {
            "posts":           posts,
            "total_posts":     len(posts),
            "avg_engagement":  round(
                sum(p["engagement"] for p in posts) / max(len(posts), 1), 1
            ),
            "best_post":       posts[0] if posts else None,
            "worst_post":      posts[-1] if posts else None,
            "zero_engagement": sum(1 for p in posts if p["engagement"] == 0),
        }
    except Exception as e:
        return {"error": str(e), "posts": []}


# ─────────────────────────────────────────────────────────────────────────────
#  AI ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def generate_report(log_analysis: dict, fb_data: dict) -> list:
    """Call Groq to generate 5 specific improvement suggestions."""
    if not GROQ_KEY:
        return []

    best_preview  = fb_data.get("best_post",  {}).get("preview", "N/A") if fb_data.get("best_post")  else "N/A"
    worst_preview = fb_data.get("worst_post", {}).get("preview", "N/A") if fb_data.get("worst_post") else "N/A"

    context = f"""
SYSTEM: AI with Abdullah — Facebook Auto-Posting System

POST LOG ANALYSIS (last {log_analysis['total']} posts):
- Success rate: {log_analysis['success_rate']}%
- Successful: {log_analysis['success']}, Failed: {log_analysis['failed']}
- Posts last 7 days: {log_analysis['recent_7d']}
- Last post: {log_analysis['last_post']}
- Errors detected: {', '.join(log_analysis['errors']) if log_analysis['errors'] else 'None'}
- Slot breakdown: {json.dumps(log_analysis['slots'])}
- Niche breakdown: {json.dumps(log_analysis['niches'])}

FACEBOOK ENGAGEMENT (last {fb_data.get('total_posts', 0)} posts):
- Average engagement: {fb_data.get('avg_engagement', 0)} (likes+comments+shares)
- Posts with ZERO engagement: {fb_data.get('zero_engagement', 0)}
- Best post ({fb_data.get('best_post', {}).get('engagement', 0)} engagement): "{best_preview}"
- Worst post ({fb_data.get('worst_post', {}).get('engagement', 0)} engagement): "{worst_preview}"
- FB API error: {fb_data.get('error', 'None')}
"""

    prompt = f"""You are analyzing an automated Facebook content system.

{context}

Generate exactly 5 improvement suggestions as a JSON array.
Each object must have:
- "priority": "HIGH" | "MEDIUM" | "LOW"
- "category": "content" | "technical" | "schedule" | "engagement" | "design"
- "problem": what issue was detected (1 sentence, reference actual data)
- "suggestion": what to change (1 sentence, specific)
- "action": exact step to implement (specific, actionable)
- "impact": expected result (1 sentence)
- "auto_implementable": true if code change needed, false if strategy change

Be specific. Reference actual numbers. No generic advice.
Return ONLY the JSON array. No markdown. No explanation."""

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model":    GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.35,
                "max_tokens":  1400,
            },
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type":  "application/json"
            },
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  Groq error: {r.status_code}")
            return []

        raw = r.json()["choices"][0]["message"]["content"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except Exception as e:
        print(f"  AI analysis error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*55}")
    print(f"  🧠 Self-Improvement Engine")
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*55}")

    if not GH_TOKEN:
        print("❌ GH_PAT not set")
        sys.exit(1)

    # Step 1 — Read post logs from GitHub
    print("\n📊 Reading post logs from GitHub...")
    raw_logs = read_github_file("data/post_log.json") or []
    print(f"  {len(raw_logs)} log entries found")
    log_analysis = analyze_post_logs(raw_logs)
    print(f"  Success rate: {log_analysis['success_rate']}%")

    # Step 2 — Fetch Facebook insights
    print("\n📱 Fetching Facebook insights...")
    fb_data = fetch_fb_insights()
    if fb_data.get("error"):
        print(f"  FB error: {fb_data['error']}")
    else:
        print(f"  {fb_data['total_posts']} posts found, avg engagement: {fb_data['avg_engagement']}")

    # Step 3 — Generate AI report
    print("\n🤖 Running AI analysis...")
    suggestions = generate_report(log_analysis, fb_data)
    print(f"  {len(suggestions)} suggestions generated")

    # Step 4 — Build and commit report
    report = {
        "generated_at":   datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "log_analysis":   log_analysis,
        "facebook":       {
            "avg_engagement":  fb_data.get("avg_engagement", 0),
            "total_posts":     fb_data.get("total_posts", 0),
            "zero_engagement": fb_data.get("zero_engagement", 0),
            "best_post":       fb_data.get("best_post"),
            "worst_post":      fb_data.get("worst_post"),
            "error":           fb_data.get("error"),
        },
        "suggestions":    suggestions,
        "implemented":    [],
    }

    print("\n💾 Committing report to GitHub...")
    success = write_github_file(
        "data/report.json",
        report,
        f"report: auto-generated {datetime.utcnow().strftime('%Y-%m-%d')}"
    )

    if success:
        print(f"\n✅ SELF-IMPROVE COMPLETE")
        print(f"   Report: {len(suggestions)} suggestions")
        print(f"   Viewable at: https://raw.githubusercontent.com/{GH_REPO}/main/data/report.json")
    else:
        print("❌ Report commit failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
