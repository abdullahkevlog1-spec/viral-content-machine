import json
from collections import defaultdict
import statistics

class LearningBrainV3:
    def __init__(self, log_path="data/post_log.json"):
        self.log_path = log_path
        self.data = self.load_data()

    def load_data(self):
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    # ─────────────────────────────
    # REAL VIRAL SCORE
    # ─────────────────────────────
    def score(self, post):
        return (
            post.get("likes", 0) +
            post.get("comments", 0) * 2 +
            post.get("shares", 0) * 3
        )

    # ─────────────────────────────
    # SPLIT WINNERS / LOSERS
    # ─────────────────────────────
    def split_data(self):
        scored = [(p, self.score(p)) for p in self.data]

        if not scored:
            return [], []

        scored.sort(key=lambda x: x[1], reverse=True)

        top_cut = int(len(scored) * 0.2)

        winners = [p for p, s in scored[:top_cut]]
        losers  = [p for p, s in scored[-top_cut:]]

        return winners, losers

    # ─────────────────────────────
    # PATTERN EXTRACTION
    # ─────────────────────────────
    def extract_patterns(self, posts):
        hooks = defaultdict(int)
        niches = defaultdict(int)
        tones = defaultdict(int)

        for p in posts:
            hooks[p.get("hook")] += 1
            niches[p.get("niche")] += 1
            tones[p.get("tone")] += 1

        return {
            "hooks": hooks,
            "niches": niches,
            "tones": tones
        }

    # ─────────────────────────────
    # NEXT POST STRATEGY ENGINE
    # ─────────────────────────────
    def next_post_strategy(self):

        winners, losers = self.split_data()

        if not winners:
            return {"error": "Not enough data"}

        win_patterns = self.extract_patterns(winners)

        best_hook = max(win_patterns["hooks"], key=win_patterns["hooks"].get, default=None)
        best_niche = max(win_patterns["niches"], key=win_patterns["niches"].get, default=None)
        best_tone = max(win_patterns["tones"], key=win_patterns["tones"].get, default=None)

        return {
            "next_best_hook": best_hook,
            "next_best_niche": best_niche,
            "next_best_tone": best_tone,
            "instruction": "Generate next post using these parameters for maximum viral probability"
        }

    # ─────────────────────────────
    # FULL INSIGHT
    # ─────────────────────────────
    def insights(self):

        winners, losers = self.split_data()

        return {
            "total_posts": len(self.data),
            "winner_count": len(winners),
            "loser_count": len(losers),
            "next_strategy": self.next_post_strategy()
        }


if __name__ == "__main__":
    brain = LearningBrainV3()
    print(brain.insights())
