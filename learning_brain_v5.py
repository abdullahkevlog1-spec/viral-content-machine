import json
import math
from collections import defaultdict
from datetime import datetime

class LearningBrainV5:
    def __init__(self, log_path="data/post_log.json"):
        self.log_path = log_path
        self.data = self.load_data()
        self.memory = self.load_memory()

    # ─────────────────────────────
    # LOAD DATA
    # ─────────────────────────────
    def load_data(self):
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    # ─────────────────────────────
    # LONG-TERM MEMORY
    # ─────────────────────────────
    def load_memory(self):
        try:
            with open("data/brain_memory.json", "r") as f:
                return json.load(f)
        except:
            return {
                "hook_weights": {},
                "niche_weights": {},
                "tone_weights": {}
            }

    def save_memory(self):
        with open("data/brain_memory.json", "w") as f:
            json.dump(self.memory, f, indent=2)

    # ─────────────────────────────
    # VIRAL SCORE
    # ─────────────────────────────
    def score(self, post):
        return (
            post.get("likes", 0) +
            post.get("comments", 0) * 2 +
            post.get("shares", 0) * 3
        )

    # ─────────────────────────────
    # UPDATE MEMORY BASED ON RESULTS
    # ─────────────────────────────
    def update_memory(self):

        for post in self.data:
            score = self.score(post)

            hook = post.get("hook")
            niche = post.get("niche")
            tone = post.get("tone")

            if hook:
                self.memory["hook_weights"][hook] = \
                    self.memory["hook_weights"].get(hook, 0) + score

            if niche:
                self.memory["niche_weights"][niche] = \
                    self.memory["niche_weights"].get(niche, 0) + score

            if tone:
                self.memory["tone_weights"][tone] = \
                    self.memory["tone_weights"].get(tone, 0) + score

        self.save_memory()

    # ─────────────────────────────
    # DECISION ENGINE
    # ─────────────────────────────
    def decide(self):

        self.update_memory()

        def best(d):
            return max(d, key=d.get) if d else None

        return {
            "best_hook": best(self.memory["hook_weights"]),
            "best_niche": best(self.memory["niche_weights"]),
            "best_tone": best(self.memory["tone_weights"])
        }

    # ─────────────────────────────
    # FAILURE DETECTION
    # ─────────────────────────────
    def detect_weak_patterns(self, threshold=10):

        weak = []

        for k, v in self.memory["hook_weights"].items():
            if v < threshold:
                weak.append(k)

        return weak

    # ─────────────────────────────
    # NEXT ACTION (FULL AUTONOMY)
    # ─────────────────────────────
    def next_action(self):

        decision = self.decide()
        weak = self.detect_weak_patterns()

        return {
            "action": "generate_post",
            "strategy": decision,
            "avoid": weak,
            "mode": "autonomous"
        }

    # ─────────────────────────────
    # REPORT
    # ─────────────────────────────
    def report(self):

        return {
            "total_posts": len(self.data),
            "memory_size": {
                "hooks": len(self.memory["hook_weights"]),
                "niches": len(self.memory["niche_weights"]),
                "tones": len(self.memory["tone_weights"])
            },
            "next_action": self.next_action()
        }


if __name__ == "__main__":
    brain = LearningBrainV5()
    print(json.dumps(brain.report(), indent=2))
