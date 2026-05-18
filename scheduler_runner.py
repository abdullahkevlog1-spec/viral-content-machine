"""Schedule loading and slot helpers for auto posting."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
SCHEDULE_FILE = DATA_DIR / "schedule.json"

DEFAULT_SLOTS: dict[str, dict[str, Any]] = {
    "morning": {
        "label": "Subah 9:00 AM",
        "niche": "AI & Tech",
        "hook_id": "curiosity",
        "tone": 7,
        "variation": "Bold/Controversial",
        "language": "English",
        "utc_hour": 4,
    },
    "trending": {
        "label": "Trending 11:00 AM",
        "niche": "News & Trends",
        "hook_id": "curiosity",
        "tone": 7,
        "variation": "Bold/Controversial",
        "language": "Hinglish",
        "utc_hour": 6,
    },
    "afternoon": {
        "label": "Dopahar 2:00 PM",
        "niche": "Motivation",
        "hook_id": "bold_claim",
        "tone": 8,
        "variation": "Bold/Controversial",
        "language": "Roman Urdu",
        "utc_hour": 9,
    },
    "evening": {
        "label": "Raat 9:00 PM",
        "niche": "ASMR / Satisfying",
        "hook_id": "relatable_pain",
        "tone": 5,
        "variation": "Emotional",
        "language": "Hinglish",
        "utc_hour": 16,
    },
}


def load_schedule(path: Path | None = None) -> dict[str, dict[str, Any]]:
    schedule_path = path or SCHEDULE_FILE
    if not schedule_path.exists():
        return {name: dict(slot) for name, slot in DEFAULT_SLOTS.items()}

    try:
        payload = json.loads(schedule_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {name: dict(slot) for name, slot in DEFAULT_SLOTS.items()}

    configured_slots = payload.get("slots", payload) if isinstance(payload, dict) else {}
    slots = {name: dict(slot) for name, slot in DEFAULT_SLOTS.items()}
    if isinstance(configured_slots, dict):
        for name, config in configured_slots.items():
            if isinstance(config, dict):
                slots[name] = {**slots.get(name, {}), **config}
    return slots


def get_next_slot(slot_name: str | None = None, now: datetime | None = None) -> tuple[str, dict[str, Any]]:
    slots = load_schedule()
    if slot_name:
        if slot_name not in slots:
            raise KeyError(f"Unknown slot: {slot_name}")
        return slot_name, slots[slot_name]

    current = now or datetime.now(timezone.utc)
    for name, slot in slots.items():
        if slot.get("utc_hour") == current.hour:
            return name, slot
    return "morning", slots["morning"]


def should_run(slot_name: str, now: datetime | None = None, tolerance_hours: int = 0) -> bool:
    slots = load_schedule()
    slot = slots.get(slot_name)
    if not slot or "utc_hour" not in slot:
        return False

    current = now or datetime.now(timezone.utc)
    slot_hour = int(slot["utc_hour"])
    if tolerance_hours <= 0:
        return current.hour == slot_hour
    return abs(current.hour - slot_hour) <= tolerance_hours
