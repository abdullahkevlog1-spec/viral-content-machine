import json
from collections import defaultdict

# ─────────────────────────────────────────────
# LEARNING BRAIN v2 — REAL PERFORMANCE AI
# ─────────────────────────────────────────────

class LearningBrainV2:
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
    # REAL SCORING (v2 UPGRADE)
    # ─────────────────────────────
    def score_post(self, post):
        """
        Now uses REAL engagement signals (if available)
        """

        likes = post.get("likes", 0)
        comments = post.get("comments", 0)
        shares = post.get("shares", 0)

        # Weighted viral score formula
        score = (
            likes * 1 +
            comments * 2 +
            shares * 3
        )

        # normalize for fairness
        text_len = len(post.get("content", ""))

        if 300 <= text_len <= 1200:
            score += 5
        elif text_len < 200:
            score -= 3

        return score

    # ─────────────────────────────
    # HOOK LEARNING SYSTEM
    # ─────────────────────────────
    def analyze_hooks(self):
        hook_stats = defaultdict(list)

        for post in self.data:
            hook = post.get("hook", "unknown")
            score = self.score_post(post)
            hook_stats[hook].append(score)

        return {
            hook: sum(scores)/len(scores)
            for hook, scores in hook_stats.items()
        }

    # ─────────────────────────────
    # NICHE LEARNING SYSTEM
    # ─────────────────────────────
    def analyze_niches(self):
        niche_stats = defaultdict(list)

        for post in self.data:
            niche = post.get("niche", "unknown")
            score = self.score_post(post)
            niche_stats[niche].append(score)

        return {
            niche: sum(scores)/len(scores)
            for niche, scores in niche_stats.items()
        }

    # ─────────────────────────────
    # TONE OPTIMIZATION
    # ─────────────────────────────
    def analyze_tones(self):
        tone_stats = defaultdict(list)

        for post in self.data:
            tone = post.get("tone", "unknown")
            score = self.score_post(post)
            tone_stats[tone].append(score)

        return {
            tone: sum(scores)/len(scores)
            for tone, scores in tone_stats.items()
        }

    # ─────────────────────────────
    # FINAL INSIGHTS ENGINE
    # ─────────────────────────────
    def insights(self):

        if not self.data:
            return {"error": "No data found"}

        hooks = self.analyze_hooks()
        niches = self.analyze_niches()
        tones = self.analyze_tones()

        best_hook = max(hooks, key=hooks.get) if hooks else None
        best_niche = max(niches, key=niches.get) if niches else None
        best_tone = max(tones, key=tones.get) if tones else None

        return {
            "total_posts": len(self.data),

            "best_hook": best_hook,
            "best_niche": best_niche,
            "best_tone": best_tone,

            "hook_scores": hooks,
            "niche_scores": niches,
            "tone_scores": tones
        }


# ─────────────────────────────
# TEST RUN
# ─────────────────────────────
if __name__ == "__main__":
    brain = LearningBrainV2()
    print("\n🧠 V2 SELF-LEARNING OUTPUT:")
    print(brain.insights())
