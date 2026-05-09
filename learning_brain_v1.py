import json
from collections import defaultdict

class LearningBrainV1:
    def __init__(self, log_path="data/post_log.json"):
        self.log_path = log_path
        self.data = self.load_data()

    def load_data(self):
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def score_post(self, post):
        score = 0
        text = post.get("content", "").lower()

        if 300 <= len(text) <= 1200:
            score += 2
        elif len(text) < 200:
            score -= 1

        if "?" in text:
            score += 1

        if any(w in text for w in ["you", "tum", "aap"]):
            score += 1

        bad_phrases = ["stay motivated", "never give up", "work hard"]
        if any(bp in text for bp in bad_phrases):
            score -= 3

        return score

    def analyze(self):
        if not self.data:
            return {"error": "No data found"}

        results = []

        for post in self.data:
            results.append({
                "slot": post.get("slot"),
                "time": post.get("time"),
                "score": self.score_post(post),
                "content_preview": post.get("content", "")[:80]
            })

        return results

    def insights(self):
        results = self.analyze()

        if isinstance(results, dict) and "error" in results:
            return results

        slot_scores = defaultdict(list)

        for r in results:
            slot_scores[r["slot"]].append(r["score"])

        avg_slot_scores = {
            k: sum(v)/len(v) for k, v in slot_scores.items() if v
        }

        best_slot = max(avg_slot_scores, key=avg_slot_scores.get, default=None)

        return {
            "total_posts": len(results),
            "best_slot": best_slot,
            "slot_performance": avg_slot_scores,
            "avg_score": sum(r["score"] for r in results) / len(results)
        }


if __name__ == "__main__":
    brain = LearningBrainV1()
    print(brain.insights())
