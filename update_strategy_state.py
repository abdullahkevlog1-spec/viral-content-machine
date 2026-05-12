import json
from pathlib import Path

DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

state = {
    'best_hook': 'curiosity',
    'best_niche': 'AI',
    'best_style': 'short punchy'
}

(DATA_DIR / 'strategy_state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
print('strategy_state.json updated')
