"""Autonomous Agent Orchestrator"""

import time
from datetime import datetime

from decision_engine import decide_next_strategy
from virality_predictor import predict_virality
from trend_engine import get_best_trend



def run_cycle():
    strategy = decide_next_strategy()

    draft = {
        "text": f"{strategy['viral_hook']} — {strategy['trend']}",
        "trend_score": strategy.get("trend_score", 50),
        "hook_weight": 1.5
    }

    prediction = predict_virality(draft)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "strategy": strategy,
        "prediction": prediction,
        "status": "ready_to_publish"
    }

    return result


if __name__ == "__main__":
    while True:
        print(run_cycle())
        time.sleep(900)
