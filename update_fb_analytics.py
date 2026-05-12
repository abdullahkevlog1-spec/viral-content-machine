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
OUTPUT_FILE.write_text(
json.dumps(data, indent=2),
encoding="utf-8"
)

def get_latest_post():
url = f"https://graph.facebook.com/v23.0/{PAGE_ID}/posts"
params = {
"access_token": TOKEN,
"limit": 1,
"fields": "id,message,created_time"
}

```
res = requests.get(url, params=params, timeout=30)
data = res.json()

posts = data.get("data", [])
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
res = requests.get(url, params=params, timeout=30)
data = res.json()

likes = data.get("likes", {}).get("summary", {}).get("total_count", 0)
comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
shares = data.get("shares", {}).get("count", 0)

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
safe_write({"error": "Missing FB credentials"})
return

```
try:
    latest = get_latest_post()

    if not latest:
        safe_write({
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "score": 0
        })
        return

    metrics = get_post_metrics(latest["id"])
    safe_write(metrics)

except Exception as e:
    safe_write({"error": str(e)})
```

if **name** == "**main**":
main()
