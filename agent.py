"""
agent.py — Semantic Reasoning & Quality Gate
Uses Gemini 3.5 Flash to score content based on psychological hooks.
"""

import json
import os
import google.generativeai as genai

class AgentDecision:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    def get_strategy(self, base_slot: dict, slot_name: str) -> dict:
        """Reads system_memory.json to adapt strategy."""
        try:
            with open("data/system_memory.json", "r") as f:
                memory = json.load(f)
            # Strategy adaptation logic could go here
            return base_slot
        except:
            return base_slot

    def approve(self, text: str, slot_config: dict) -> dict:
        """Semantic Reasoning Quality Gate."""
        if not self.model:
            return {"action": "post", "score": 100, "reason": "No API key, bypassing gate"}
            
        prompt = f"""
        Analyze the following social media post for virality and quality.
        Score it from 0-100 based on:
        - Psychological Hooks (Fear, Greed, Curiosity)
        - Readability & Structure
        - Niche Relevance: {slot_config['niche']}
        
        POST:
        {text}
        
        Return ONLY a JSON object:
        {{
            "score": int,
            "action": "post" | "regenerate",
            "reason": "short explanation"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            verdict = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
            return verdict
        except Exception as e:
            print(f"Agent Error: {e}")
            return {"action": "post", "score": 50, "reason": "Error in reasoning, posting anyway"}
