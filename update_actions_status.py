import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

status = {
    'status': 'success',
    'last_run': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
}

(DATA_DIR / 'actions_status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
print('actions_status.json updated')
