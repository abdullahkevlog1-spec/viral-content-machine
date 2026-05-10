"""
Phase 3 — Autonomous Schedule Planner
"""

import json
from datetime import datetime, timedelta

OUTPUT = "data/schedule.json"



def build_schedule():
    now = datetime.utcnow()

    schedule = []

    for i in range(4):
        slot = now + timedelta(hours=(i * 6))

        schedule.append({
            "time": slot.isoformat(),
            "status": "planned",
            "priority": "high" if i == 0 else "normal"
        })

    return schedule



def save_schedule(schedule):
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2)


if __name__ == "__main__":
    s = build_schedule()
    save_schedule(s)
    print("Schedule generated")
