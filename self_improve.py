"""
self_improve_action.py — Autonomous Learning Loop
Runs daily via GitHub Actions.
Collects real FB metrics → updates performance history → 
runs learning engine → updates strategy weights → commits report.
"""

import os
import sys
import json
import base64
import requests
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_KEY  = os.environ.get("GROQ_API_KEY", "")
FB_TOKEN  = os.environ.get("FB_PAGE_TOKEN", "")
FB_PAGE   = os.environ.get("FB_PAGE_ID", "")
GH_TOKEN  = os.environ.get("GH_PAT", "")
GH_REPO   = os.environ.get("GITHUB_REPO",
            "abdullahkevlog1-spec/viral-content-machine")

GH_HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept":        "application/vnd.github.v3+json",
}


# ─────────────────────────────────────────────────────────────────────────────
#  GITHUB FILE OPS
# ─────────────────────────────────────────────────────────────────────────────
def gh_read(path: str):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    r   = requests.get(url, headers=GH_HEADERS, timeout=10)
    if r.status_code == 200:
        try:
            return json.loads(base64.b64decode(r.json()["content"]).decode())
        except Exception:
            pass
    return None


def gh_write(path: str, data, message: str) -> bool:
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    r   = requests.get(url, headers=GH_HEADERS, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None

    content = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode()
    ).decode()

    payload = {"message": message, "content": content, "branch": "main"}
    if sha:
        payload["sha"] = sha

    r2 = requests.put(url, json=payload, headers=GH_HEADERS, timeout=15)
    ok = r2.status_code in (200, 201)
    if ok:
        print(f"  ✅ {path}")
    else:
        print(f"  ❌ {path}: {r2.status_code}")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 — FETCH REAL FACEBOOK METRICS
# ─────────────────────────────────────────────────────────────────────────────
def fetch_fb_post_insights(post_id: str) -> dict:
    """Fetch real engagement for a specific post."""
    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{post_id}",
            params={
                "fields": "likes.summary(true),comments.summary(true),shares",
                "access_token": FB_TOKEN,
            },
            timeout=10,
        )
        d = r.json()
        return {
            "likes":    d.get("likes",    {}).get("summary", {}).get("total_count", 0),
            "comments": d.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares":   d.get("shares",   {}).get("count", 0),
        }
    except Exception:
        return {"likes": 0, "comments": 0, "shares": 0}


def fetch_all_fb_posts() -> list:
    """Fetch last 20 posts with engagement data."""
    if not FB_TOKEN or not FB_PAGE:
        return []
    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{FB_PAGE}/posts",
            params={
                "fields": "id,message,created_time,"
                          "likes.summary(true),comments.summary(true),shares",
                "limit":  20,
                "access_token": FB_TOKEN,
            },
            timeout=15,
        )
        posts = []
        for p in r.json().get("data", []):
            posts.append({
                "id":       p.get("id"),
                "time":     p.get("created_time", "")[:10],
                "preview":  (p.get("message") or "")[:80],
                "likes":    p.get("likes",    {}).get("summary", {}).get("total_count", 0),
                "comments": p.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares":   p.get("shares",   {}).get("count", 0),
            })
        return posts
    except Exception as e:
        print(f"  FB fetch error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — UPDATE PERFORMANCE HISTORY WITH REAL METRICS
# ─────────────────────────────────────────────────────────────────────────────
def update_history_with_metrics(history: list, fb_posts: list) -> list:
    """
    Cross-reference post log with FB metrics.
    Updates engagement scores in history.
    """
    fb_by_id = {p["id"]: p for p in fb_posts}

    for entry in history:
        pid = entry.get("post_id", "")
        if pid and pid in fb_by_id:
            fb = fb_by_id[pid]
            entry["likes"]    = fb["likes"]
            entry["comments"] = fb["comments"]
            entry["shares"]   = fb["shares"]
            total = fb["likes"] + fb["comments"] + fb["shares"]
            entry["score"]    = min(100, (fb["likes"] * 1) +
                                    (fb["comments"] * 3) +
                                    (fb["shares"] * 2))

    return history


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 — LEARNING ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def run_learning_engine(history: list, strategy: dict) -> dict:
    """
    Analyze performance history and update strategy weights.
    Returns updated strategy.
    """
    if not history:
        return strategy

    # Group by hook
    hook_scores  = {}
    niche_scores = {}
    slot_scores  = {}

    for p in history:
        score = p.get("score", 0)

        h = p.get("hook_style", "")
        if h:
            if h not in hook_scores:
                hook_scores[h] = []
            hook_scores[h].append(score)

        n = p.get("niche", "")
        if n:
            if n not in niche_scores:
                niche_scores[n] = []
            niche_scores[n].append(score)

        s = p.get("slot", "")
        if s:
            if s not in slot_scores:
                slot_scores[s] = []
            slot_scores[s].append(score)

    # Update hook weights
    for hook, scores in hook_scores.items():
        if len(scores) < 2:
            continue
        avg = sum(scores) / len(scores)
        # Normalize: avg score > 15 = boost, < 5 = penalize
        if avg > 15:
            current = strategy["hook_weights"].get(hook, 1.0)
            strategy["hook_weights"][hook] = min(2.0, round(current + 0.05, 2))
            print(f"  ↑ Boosted hook: {hook} (avg score {avg:.1f})")
        elif avg < 5 and len(scores) >= 5:
            current = strategy["hook_weights"].get(hook, 1.0)
            strategy["hook_weights"][hook] = max(0.3, round(current - 0.05, 2))
            print(f"  ↓ Penalized hook: {hook} (avg score {avg:.1f})")

    # Update niche weights
    for niche, scores in niche_scores.items():
        if len(scores) < 3:
            continue
        avg = sum(scores) / len(scores)
        if avg > 15:
            current = strategy["niche_weights"].get(niche, 1.0)
            strategy["niche_weights"][niche] = min(2.0, round(current + 0.05, 2))
        elif avg < 5 and len(scores) >= 5:
            current = strategy["niche_weights"].get(niche, 1.0)
            strategy["niche_weights"][niche] = max(0.3, round(current - 0.05, 2))

    strategy["version"] = strategy.get("version", 1) + 1
    return strategy


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 — AI ANALYSIS → 5 SUGGESTIONS
# ─────────────────────────────────────────────────────────────────────────────
def generate_ai_suggestions(history: list, strategy: dict,
                              fb_posts: list) -> list:
    if not GROQ_KEY:
        return []

    # Build stats
    total   = len(history)
    success = sum(1 for p in history if p.get("score", 0) > 0)
    avg_score = round(sum(p.get("score", 0) for p in history) / max(total, 1), 1)

    # Hook performance
    hook_avg = {}
    for p in history:
        h = p.get("hook_style", "")
        if h:
            if h not in hook_avg:
                hook_avg[h] = []
            hook_avg[h].append(p.get("score", 0))
    hook_summary = {h: round(sum(s)/len(s), 1)
                    for h, s in hook_avg.items() if s}
    top_hook = max(hook_summary, key=hook_summary.get) if hook_summary else "N/A"

    fb_avg_eng = round(
        sum(p["likes"] + p["comments"] + p["shares"] for p in fb_posts) /
        max(len(fb_posts), 1), 1
    ) if fb_posts else 0

    best_fb_post = max(
        fb_posts,
        key=lambda x: x["likes"] + x["comments"] + x["shares"],
        default={}
    )

    context = f"""
SYSTEM: AI with Abdullah — Facebook Auto-Posting (Pakistan)

PERFORMANCE SUMMARY:
- Total logged posts: {total}
- Posts with engagement data: {success}
- Average score: {avg_score}/100
- Top performing hook: {top_hook}
- Hook performance: {json.dumps(hook_summary)}
- Strategy version: {strategy.get('version', 1)}
- Hook weights: {json.dumps(strategy.get('hook_weights', {}))}

FACEBOOK REAL DATA (last {len(fb_posts)} posts):
- Avg engagement: {fb_avg_eng}
- Best post preview: {best_fb_post.get('preview', 'N/A')}
- Best post engagement: {best_fb_post.get('likes', 0) + best_fb_post.get('comments', 0) + best_fb_post.get('shares', 0)}
- Posts with zero engagement: {sum(1 for p in fb_posts if p['likes']+p['comments']+p['shares']==0)}
"""

    prompt = f"""Analyze this Pakistani Facebook page performance data and give 5 specific improvement suggestions.

{context}

Return ONLY a JSON array with 5 objects. Each must have:
- "priority": "HIGH"|"MEDIUM"|"LOW"
- "category": "content"|"technical"|"schedule"|"engagement"|"design"
- "problem": 1 sentence, reference actual numbers
- "suggestion": 1 sentence, specific
- "action": exact implementable step
- "impact": expected result

No markdown. Only the JSON array."""

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.35,
                "max_tokens":  1200,
            },
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
        if r.status_code == 200:
            raw = r.json()["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
    except Exception as e:
        print(f"  AI suggestions error: {e}")
    return []


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN — Full autonomous learning loop
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*55}")
    print(f"  🧠 Self-Improvement Learning Loop")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*55}")

    if not GH_TOKEN:
        print("❌ GH_PAT missing")
        sys.exit(1)

    # ── Step 1: Load post log from GitHub ──
    print("\n📊 Loading post log...")
    post_log = gh_read("data/post_log.json") or []
    print(f"  {len(post_log)} log entries")

    # ── Step 2: Load performance history from GitHub ──
    print("\n📜 Loading performance history...")
    history = gh_read("data/performance_history.json") or []

    # Merge post_log into history (add new entries)
    existing_ids = {p.get("post_id") for p in history}
    added = 0
    for log_entry in post_log:
        pid = log_entry.get("post_id")
        if pid and pid not in existing_ids and log_entry.get("status") == "success":
            history.append({
                "post_id":    pid,
                "time":       log_entry.get("time", ""),
                "niche":      log_entry.get("niche", ""),
                "slot":       log_entry.get("slot", ""),
                "language":   log_entry.get("language", ""),
                "preview":    log_entry.get("preview", ""),
                "likes":      0, "comments": 0, "shares": 0, "score": 0,
            })
            existing_ids.add(pid)
            added += 1
    print(f"  Added {added} new entries from post_log")

    # ── Step 3: Fetch real FB metrics ──
    print("\n📱 Fetching Facebook metrics...")
    fb_posts = fetch_all_fb_posts()
    print(f"  {len(fb_posts)} posts fetched")

    history = update_history_with_metrics(history, fb_posts)
    print(f"  Engagement data updated")

    # ── Step 4: Load + update strategy ──
    print("\n🧠 Running learning engine...")
    strategy = gh_read("data/strategy_state.json")
    if not strategy:
        # Import default
        try:
            from memory_manager import DEFAULT_STRATEGY
            strategy = DEFAULT_STRATEGY.copy()
        except ImportError:
            strategy = {"version": 1, "hook_weights": {}, "niche_weights": {},
                        "slot_weights": {}, "format_weights": {}}

    strategy = run_learning_engine(history, strategy)
    print(f"  Strategy updated to v{strategy.get('version', '?')}")

    # ── Step 5: Update content memory ──
    print("\n💾 Updating content memory...")
    scored = [p for p in history if p.get("score", 0) > 0]
    if scored:
        top    = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)
        w_hooks = list({p.get("hook_style") for p in top[:5] if p.get("hook_style")})
        w_niches = list({p.get("niche") for p in top[:5] if p.get("niche")})
        memory = {
            "winning_hooks":   w_hooks[:3],
            "winning_niches":  w_niches[:2],
            "winning_formats": ["carousel"],
            "total_scored":    len(scored),
            "avg_score":       round(sum(p.get("score",0) for p in scored)/len(scored),1),
            "last_updated":    datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        }
    else:
        memory = {"winning_hooks": [], "winning_niches": [],
                  "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M")}

    # ── Step 6: Generate AI suggestions ──
    print("\n🤖 Generating AI suggestions...")
    suggestions = generate_ai_suggestions(history, strategy, fb_posts)
    print(f"  {len(suggestions)} suggestions generated")

    # ── Step 7: Build report ──
    report = {
        "generated_at":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "total_posts":   len(history),
        "scored_posts":  len([p for p in history if p.get("score", 0) > 0]),
        "avg_score":     round(sum(p.get("score",0) for p in history)/max(len(history),1), 1),
        "log_analysis": {
            "total":        len(post_log),
            "success":      sum(1 for p in post_log if p.get("status") == "success"),
            "failed":       sum(1 for p in post_log if p.get("status") == "failed"),
            "success_rate": round(
                sum(1 for p in post_log if p.get("status") == "success") /
                max(len(post_log), 1) * 100, 1
            ),
            "errors": list({p.get("error","") for p in post_log
                           if p.get("error")})[:5],
        },
        "facebook": {
            "avg_engagement":  round(
                sum(p["likes"]+p["comments"]+p["shares"] for p in fb_posts) /
                max(len(fb_posts), 1), 1),
            "total_posts":     len(fb_posts),
            "zero_engagement": sum(1 for p in fb_posts
                                   if p["likes"]+p["comments"]+p["shares"]==0),
            "best_post":       max(fb_posts,
                key=lambda x: x["likes"]+x["comments"]+x["shares"],
                default=None) if fb_posts else None,
            "worst_post":      min(fb_posts,
                key=lambda x: x["likes"]+x["comments"]+x["shares"],
                default=None) if fb_posts else None,
        },
        "strategy_version": strategy.get("version", 1),
        "hook_weights":     strategy.get("hook_weights", {}),
        "suggestions":      suggestions,
        "implemented":      [],
    }

    # ── Step 8: Commit everything ──
    print("\n💾 Committing to GitHub...")
    ts = datetime.utcnow().strftime("%Y-%m-%d")
    gh_write("data/performance_history.json", history[-200:],
             f"metrics: update engagement {ts}")
    gh_write("data/strategy_state.json", strategy,
             f"strategy: v{strategy.get('version','?')} update {ts}")
    gh_write("data/content_memory.json", memory,
             f"memory: update {ts}")
    gh_write("data/report.json", report,
             f"report: {len(suggestions)} suggestions {ts}")

    print(f"\n{'='*55}")
    print(f"  ✅ LEARNING LOOP COMPLETE")
    print(f"  Strategy: v{strategy.get('version')}")
    print(f"  History: {len(history)} posts")
    print(f"  Suggestions: {len(suggestions)}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
