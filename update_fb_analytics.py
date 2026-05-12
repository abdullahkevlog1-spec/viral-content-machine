import json
from pathlib import Path

DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

analytics = {
    'likes': 0,
    'comments': 0,
    'shares': 0,
    'score': 0
}

(DATA_DIR / 'fb_analytics.json').write_text(json.dumps(analytics, indent=2), encoding='utf-8')
print('fb_analytics.json updated')
