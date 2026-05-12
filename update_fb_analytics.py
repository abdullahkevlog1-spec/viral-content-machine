import os
import json
import requests
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

TOKEN = os.getenv("FB_PAGE_TOKEN")
PAGE_ID = os.getenv("FB_PAGE_ID")
OUTPUT_FILE = DATA_DIR / "fb_analytics.json"

def safe_write(data):
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
json.dump(data, f, indent=2)

def get_latest_post():
url = f"https://graph.facebook.com/v23.0/{PAGE_ID}/posts"
params = {
"access_token": TOKEN,
"limit": 1,
"fields": "id,message,created_time"
}

```
response = requests.get(url, params=params, timeout=30)
result = response.json()

posts = result.get("data", [])
if not posts:
    return None

return posts[0]
```

def get_post_metrics(post_id):
url = f"https://graph.facebook.com/v23.0/{post_id}"
params = {
"access_token": TOKEN,
"fields": "likes.summary(true),comments.summary(true),shares"
}

```
response = requests.get(url, params=params, timeout=30)
result = response.json()

likes = result.get("likes", {}).get("summary", {}).get("total_count", 0)
comments = result.get("comments", {}).get("summary", {}).get("total_count", 0)
shares = result.get("shares", {}).get("count", 0)

score = likes + (comments * 3) + (shares * 2)

return {
    "likes": likes,
    "comments": comments,
    "shares": shares,
    "score": score
}
```

def main():
if not TOKEN or not PAGE_ID:
safe_write({"error": "Missing credentials"})
return

```
try:
    latest_post = get_latest_post()

    if not latest_post:
        safe_write({
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "score": 0
        })
        return

    metrics = get_post_metrics(latest_post["id"])
    safe_write(metrics)

except Exception as e:
    safe_write({"error": str(e)})
```

if **name** == "**main**":
main()
