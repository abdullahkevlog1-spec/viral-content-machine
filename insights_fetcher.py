"""
insights_fetcher.py
Phase 1 autonomous feedback layer.
Fetches Facebook post metrics and syncs them into analytics history.
"""

import requests
from analytics import load_history, update_post_engagement

GRAPH_API_VERSION = "v20.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def fetch_post_metrics(post_id: str, access_token: str) -> dict:
    """
    Fetch likes/comments/shares from Facebook Graph API.
    Returns normalized metrics dict.
    """
    url = f"{BASE_URL}/{post_id}"
    params = {
        "fields": "likes.summary(true),comments.summary(true),shares",
        "access_token": access_token,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        data = response.json()

        if response.status_code != 200:
            return {"error": data}

        return {
            "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
            "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares": data.get("shares", {}).get("count", 0),
            "reach": 0,
        }
    except Exception as e:
        return {"error": str(e)}


def sync_recent_posts(access_token: str, limit: int = 10) -> dict:
    """
    Sync latest stored posts with live Facebook metrics.
    Updates analytics history in-place.
    """
    history = load_history()
    recent_posts = history[-limit:]

    updated = 0
    failed = 0

    for post in recent_posts:
        post_id = post.get("post_id")
        if not post_id:
            continue

        metrics = fetch_post_metrics(post_id, access_token)

        if metrics.get("error"):
            failed += 1
            continue

        update_post_engagement(
            post_id=post_id,
            likes=metrics["likes"],
            comments=metrics["comments"],
            shares=metrics["shares"],
            reach=metrics.get("reach", 0),
        )
        updated += 1

    return {
        "updated": updated,
        "failed": failed,
        "checked": len(recent_posts),
    }


if __name__ == "__main__":
    print("Insights fetcher ready. Import and run sync_recent_posts().")
