import os
import json
import requests

TOKEN = os.getenv("FB_PAGE_TOKEN")
PAGE_ID = os.getenv("FB_PAGE_ID")

def main():
output_path = "data/fb_analytics.json"

```
if not TOKEN or not PAGE_ID:
    data = {"error": "Missing credentials"}
else:
    try:
        post_url = f"https://graph.facebook.com/v23.0/{PAGE_ID}/posts"
        post_params = {
            "access_token": TOKEN,
            "limit": 1,
            "fields": "id"
        }

        post_response = requests.get(post_url, params=post_params, timeout=30)
        post_json = post_response.json()

        posts = post_json.get("data", [])

        if not posts:
            data = {
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "score": 0
            }
        else:
            post_id = posts[0]["id"]

            metrics_url = f"https://graph.facebook.com/v23.0/{post_id}"
            metrics_params = {
                "access_token": TOKEN,
                "fields": "likes.summary(true),comments.summary(true),shares"
            }

            metrics_response = requests.get(
                metrics_url,
                params=metrics_params,
                timeout=30
            )
            metrics_json = metrics_response.json()

            likes = metrics_json.get(
                "likes", {}
            ).get(
                "summary", {}
            ).get(
                "total_count", 0
            )

            comments = metrics_json.get(
                "comments", {}
            ).get(
                "summary", {}
            ).get(
                "total_count", 0
            )

            shares = metrics_json.get(
                "shares", {}
            ).get(
                "count", 0
            )

            score = likes + (comments * 3) + (shares * 2)

            data = {
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "score": score
            }

    except Exception as e:
        data = {"error": str(e)}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
```

if **name** == "**main**":
main()
