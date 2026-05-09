import json
import math
from collections import defaultdict
from datetime import datetime

class LearningBrainV4:
    def __init__(self, log_path="data/post_log.json"):
        self.log_path = log_path
        self.data = self.load_data()

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
    # SAFE SCORE (REALISTIC)
    # ─────────────────────────────
    def score(self, post):
        likes = post.get("likes", 0)
        comments = post.get("comments", 0)
        shares = post.get("shares", 0)

        base = likes + comments * 2 + shares * 3

        # time decay (recent posts matter more)
        try:
            ts = datetime.fromisoformat(post.get("timestamp"))
            days_old = max((datetime.now() - ts).days, 1)
            decay = 1 / math.log(days_old + 1.5)
        except:
            decay = 1

        return base * decay

    # ─────────────────────────────
    # STUDENT STYLE PATTERN LEARNING
    # ─────────────────────────────
    def learn_patterns(self):

        hooks = defaultdict(list)
        niches = defaultdict(list)
        tones = defaultdict(list)

        for p in self.data:
            s = self.score(p)

            hooks[p.get("hook", "unknown")].append(s)
            niches[p.get("niche", "unknown")].append(s)
            tones[p.get("tone", "unknown")].append(s)

        def avg(x):
            return sum(x) / len(x) if x else 0

        return {
            "hooks": {k: avg(v) for k, v in hooks.items()},
            "niches": {k: avg(v) for k, v in niches.items()},
            "tones": {k: avg(v) for k, v in tones.items()}
        }

    # ─────────────────────────────
    # NEXT POST RECOMMENDATION (CONTROLLED AUTONOMY)
    # ─────────────────────────────
    def recommend_next_post(self):

        patterns = self.learn_patterns()

        best_hook = max(patterns["hooks"], key=patterns["hooks"].get, default=None)
        best_niche = max(patterns["niches"], key=patterns["niches"].get, default=None)
        best_tone = max(patterns["tones"], key=patterns["tones"].get, default=None)

        # confidence calculation (simple stability check)
        confidence = min(len(self.data) * 5, 95)

        return {
            "recommendation": {
                "hook": best_hook,
                "niche": best_niche,
                "tone": best_tone
            },
            "confidence_percent": confidence,
            "explanation": (
                "Based on historical engagement patterns. "
                "This is a statistical recommendation, not a fixed rule."
            ),
            "alternative": {
                "note": "If engagement drops, fallback to second best performing pattern"
            }
        }

    # ─────────────────────────────
    # MAIN OUTPUT (STUDENT REPORT STYLE)
    # ─────────────────────────────
    def report(self):

        if not self.data:
            return {
                "status": "no data",
                "message": "System is learning from empty dataset"
            }

        return {
            "total_posts": len(self.data),
            "learning_mode": "student-safe-autonomous",
            "next_post_plan": self.recommend_next_post()
        }


if __name__ == "__main__":
    brain = LearningBrainV4()
    print(json.dumps(brain.report(), indent=2))
