import json
from collections import defaultdict

class LearningBrain:
    def __init__(self, log_path="data/post_log.json", memory_path="data/brain_memory.json"):
        self.log_path = log_path
        self.memory_path = memory_path
        self.data = self.load_data()
        self.memory = self.load_memory()

    def load_data(self):
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def load_memory(self):
        try:
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"hook": {}, "niche": {}, "tone": {}}

    def save_memory(self):
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2)

    def score_post(self, post):
        return post.get("likes", 0) + post.get("comments", 0) * 2 + post.get("shares", 0) * 3

    def learn(self):
        for post in self.data:
            score = self.score_post(post)

            hook = post.get("hook_id") or post.get("hook_style") or post.get("hook")
            niche = post.get("niche")
            tone = post.get("tone")

            if hook:
                self.memory["hook"][hook] = self.memory["hook"].get(hook, 0) + score
            if niche:
                self.memory["niche"][niche] = self.memory["niche"].get(niche, 0) + score
            if tone:
                self.memory["tone"][tone] = self.memory["tone"].get(tone, 0) + score

        self.save_memory()

    def get_best(self, category):
        if not self.memory[category]:
            return None
        return max(self.memory[category], key=self.memory[category].get)

    def get_weak(self, threshold=10):
        return [hook for hook, score in self.memory["hook"].items() if score < threshold]

    def next_strategy(self):
        self.learn()
        return {
            "hook": self.get_best("hook"),
            "niche": self.get_best("niche"),
            "tone": self.get_best("tone"),
            "avoid": self.get_weak(),
            "mode": "adaptive-learning"
        }

    def report(self):
        return {"total_posts": len(self.data), "strategy": self.next_strategy()}


if __name__ == "__main__":
    brain = LearningBrain()
    print(json.dumps(brain.report(), indent=2))
