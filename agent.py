"""
agent.py — Autonomous Decision Agent
=====================================
Role: Pre-posting quality gate + adaptive strategy selector.

HOW IT FITS IN THE PIPELINE:
    auto_post.py calls AgentDecision.approve(text, slot_config)
    ↓
    Agent checks virality score
    ↓
    If score >= threshold → approve, post karo
    If score < threshold → regenerate request bhejo (max 2x)
    If still low → post anyway (never skip entirely)

NOT a daemon. Single-run per post. GitHub Actions compatible.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR             = Path("data")
STRATEGY_PATH        = DATA_DIR / "strategy_state.json"
POST_LOG_PATH        = DATA_DIR / "post_log.json"
AGENT_LOG_PATH       = DATA_DIR / "agent_decisions.json"

VIRALITY_THRESHOLD   = 55    # Minimum score to approve post as-is
REGEN_THRESHOLD      = 40    # Below this → definitely regenerate
MAX_AGENT_LOG        = 100   # Keep last N decisions


# ─────────────────────────────────────────────────────────────────────────────
#  VIRALITY PREDICTOR — upgraded from the original fake version
# ─────────────────────────────────────────────────────────────────────────────
class ViralityPredictor:
    """
    Score a post draft before it goes live.
    Returns 0-100. Based on structural signals, not ML.
    Honest about what it is — a heuristic filter, not a crystal ball.
    """

    POWER_WORDS = [
        "secret", "mistake", "truth", "stop", "before", "never",
        "warning", "exposed", "finally", "nobody", "ignored", "banned",
        "koi nahi", "sach", "galti", "band karo", "pehle",  # Roman Urdu
    ]

    WEAK_WORDS = [
        "in today's world", "game changer", "believe in yourself",
        "never give up", "dream big", "stay motivated", "unlock your potential",
        "elevate", "synergy", "leverage",
    ]

    CTA_SIGNALS = [
        "comment", "follow", "share", "save", "tag", "dm",
        "neeche", "batao", "karo", "likho",  # Roman Urdu CTAs
    ]

    HOOK_PATTERNS = [
        r"^\d+\s",            # Starts with number (list hook)
        r"\?$",               # Ends with question
        r"^(stop|wait|yaar)", # Imperative opener
        r"\b(bhai|yaar|sun)\b",  # Direct address Hinglish
    ]

    def score(self, text: str, slot_config: dict = None) -> dict:
        if not text or len(text.strip()) < 50:
            return {"score": 0, "signals": ["too_short"], "confidence": 0.1}

        text_lower = text.lower()
        score = 50
        signals = []

        # ── Length scoring ──
        word_count = len(text.split())
        if 60 <= word_count <= 150:
            score += 8
            signals.append("good_length")
        elif word_count < 30:
            score -= 15
            signals.append("too_short")
        elif word_count > 300:
            score -= 5
            signals.append("too_long")

        # ── Hook strength ──
        first_line = text.strip().split("\n")[0]
        first_line_lower = first_line.lower()

        if any(w in first_line_lower for w in self.POWER_WORDS):
            score += 15
            signals.append("power_word_hook")

        for pattern in self.HOOK_PATTERNS:
            if re.search(pattern, first_line_lower):
                score += 8
                signals.append("hook_pattern_match")
                break

        if len(first_line.split()) <= 12:
            score += 5
            signals.append("punchy_hook")
        elif len(first_line.split()) > 20:
            score -= 5
            signals.append("hook_too_long")

        # ── CTA presence ──
        if any(cta in text_lower for cta in self.CTA_SIGNALS):
            score += 10
            signals.append("cta_present")
        else:
            score -= 8
            signals.append("no_cta")

        # ── Emoji density ──
        emoji_count = len(re.findall(
            r"[\U0001F300-\U0001FFFF\U00002700-\U000027BF]", text
        ))
        if 2 <= emoji_count <= 6:
            score += 5
            signals.append("good_emoji_density")
        elif emoji_count == 0:
            score -= 3
            signals.append("no_emojis")
        elif emoji_count > 10:
            score -= 5
            signals.append("emoji_spam")

        # ── Penalty: generic phrases ──
        generic_hits = sum(1 for w in self.WEAK_WORDS if w in text_lower)
        if generic_hits > 0:
            score -= generic_hits * 12
            signals.append(f"generic_phrases_{generic_hits}x")

        # ── Paragraph structure ──
        paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            score += 8
            signals.append("good_structure")
        elif len(paragraphs) < 2:
            score -= 5
            signals.append("no_paragraphs")

        # ── Hashtag check ──
        hashtag_count = len(re.findall(r"#\w+", text))
        if 3 <= hashtag_count <= 8:
            score += 3
            signals.append("good_hashtags")
        elif hashtag_count == 0:
            score -= 5
            signals.append("no_hashtags")
        elif hashtag_count > 15:
            score -= 5
            signals.append("hashtag_spam")

        # ── Language consistency bonus (slot-aware) ──
        if slot_config:
            lang = slot_config.get("language", "English")
            if lang == "Roman Urdu":
                # Check for some Roman Urdu markers
                urdu_markers = ["hai", "ka", "ke", "ko", "nahi", "karo", "ho", "yaar", "bhai"]
                urdu_hits = sum(1 for m in urdu_markers if m in text_lower)
                if urdu_hits >= 3:
                    score += 5
                    signals.append("roman_urdu_consistent")
            elif lang == "Hinglish":
                has_english = bool(re.search(r"\b(the|is|are|was|have)\b", text_lower))
                has_urdu = bool(re.search(r"\b(hai|ka|aur|ke)\b", text_lower))
                if has_english and has_urdu:
                    score += 5
                    signals.append("hinglish_consistent")

        final_score = max(0, min(100, score))
        confidence = 0.6 if len(signals) >= 4 else 0.4

        return {
            "score": final_score,
            "signals": signals,
            "confidence": confidence,
            "word_count": word_count,
            "paragraphs": len(paragraphs),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  STRATEGY SELECTOR — reads real performance data
# ─────────────────────────────────────────────────────────────────────────────
class StrategySelector:
    """
    Reads strategy_state.json to decide what to post.
    Falls back to safe defaults if file missing or corrupt.
    """

    SAFE_DEFAULTS = {
        "hook_id":   "curiosity",
        "niche":     "AI & Tech",
        "variation": "Bold/Controversial",
        "language":  "English",
        "tone":      7,
    }

    def load_strategy(self) -> dict:
        try:
            if STRATEGY_PATH.exists():
                with open(STRATEGY_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"  [Agent] Strategy load failed: {e}")
        return {}

    def best_hook_for_slot(self, slot_name: str, strategy: dict) -> str:
        """
        Pick the best hook — strategy-aware, with slot diversity.
        Morning gets best hook. Other slots rotate to avoid repetition.
        """
        hook_weights = strategy.get("hook_weights", {})

        if not hook_weights:
            # Fall back to simple best_hook field
            return strategy.get("best_hook", self.SAFE_DEFAULTS["hook_id"])

        sorted_hooks = sorted(hook_weights.items(), key=lambda x: x[1], reverse=True)

        if slot_name == "morning":
            return sorted_hooks[0][0] if sorted_hooks else "curiosity"
        elif slot_name == "afternoon" and len(sorted_hooks) >= 2:
            return sorted_hooks[1][0]
        elif slot_name == "evening" and len(sorted_hooks) >= 3:
            return sorted_hooks[2][0]
        else:
            return sorted_hooks[0][0] if sorted_hooks else "curiosity"

    def recommend(self, base_slot: dict, slot_name: str) -> dict:
        """
        Returns an adapted slot config based on performance history.
        Always returns a valid config — never crashes.
        """
        strategy = self.load_strategy()

        if not strategy or strategy.get("learning_status") not in ("active", "warmup"):
            print("  [Agent] No active strategy — using base slot config")
            return base_slot

        adapted = dict(base_slot)  # shallow copy

        # Hook: performance-based selection
        best_hook = self.best_hook_for_slot(slot_name, strategy)
        if best_hook:
            adapted["hook_id"] = best_hook

        # Language: use what's working
        best_lang = strategy.get("best_language")
        if best_lang in ("English", "Roman Urdu", "Hinglish"):
            adapted["language"] = best_lang

        # Variation: use what's working
        best_style = strategy.get("best_style")
        if best_style in ("Emotional", "Educational", "Bold/Controversial"):
            adapted["variation"] = best_style

        # Niche: only override morning (discovery slot)
        if slot_name == "morning":
            best_niche = strategy.get("best_niche")
            if best_niche in ("AI & Tech", "Motivation", "ASMR / Satisfying", "Business"):
                adapted["niche"] = best_niche

        print(f"  [Agent] Strategy applied: hook={adapted['hook_id']} "
              f"lang={adapted['language']} niche={adapted['niche']}")

        return adapted


# ─────────────────────────────────────────────────────────────────────────────
#  DECISION GATE — the main interface auto_post.py calls
# ─────────────────────────────────────────────────────────────────────────────
class AgentDecision:
    """
    Single entry point for pre-post decisions.

    Usage in auto_post.py:
        from agent import AgentDecision
        agent = AgentDecision()
        verdict = agent.approve(text, slot_config)
        if verdict["action"] == "post":
            # proceed
        elif verdict["action"] == "regenerate":
            # regenerate text, try again (max once)
    """

    def __init__(self):
        self.predictor = ViralityPredictor()
        self.selector  = StrategySelector()

    def approve(self, text: str, slot_config: dict,
                attempt: int = 1) -> dict:
        """
        Evaluate a post draft and return a verdict.

        Returns:
            {
                "action":     "post" | "regenerate" | "post_anyway",
                "score":      int,
                "signals":    list,
                "reason":     str,
                "attempt":    int,
            }
        """
        prediction = self.predictor.score(text, slot_config)
        score      = prediction["score"]
        signals    = prediction["signals"]

        if score >= VIRALITY_THRESHOLD:
            action = "post"
            reason = f"Score {score} >= threshold {VIRALITY_THRESHOLD}"

        elif score >= REGEN_THRESHOLD and attempt < 2:
            action = "regenerate"
            reason = (f"Score {score} borderline — regenerating "
                      f"(attempt {attempt}/2)")

        elif score < REGEN_THRESHOLD and attempt < 2:
            action = "regenerate"
            reason = (f"Score {score} below regen threshold {REGEN_THRESHOLD} "
                      f"— stronger rewrite needed")

        else:
            # Never block posting entirely — algo se zyada trust nahi
            action = "post_anyway"
            reason = (f"Score {score} still low after {attempt} attempts — "
                      f"posting anyway to maintain schedule")

        verdict = {
            "action":  action,
            "score":   score,
            "signals": signals,
            "reason":  reason,
            "attempt": attempt,
        }

        self._log_decision(text, slot_config, verdict)

        print(f"  [Agent] Score={score} | Action={action} | {reason}")
        return verdict

    def get_strategy(self, base_slot: dict, slot_name: str) -> dict:
        """Wrapper for StrategySelector.recommend()"""
        return self.selector.recommend(base_slot, slot_name)

    def _log_decision(self, text: str, slot_config: dict, verdict: dict):
        """Append decision to agent_decisions.json for dashboard visibility."""
        DATA_DIR.mkdir(exist_ok=True)
        try:
            if AGENT_LOG_PATH.exists():
                with open(AGENT_LOG_PATH, "r", encoding="utf-8") as f:
                    log = json.load(f)
            else:
                log = []
        except Exception:
            log = []

        log.append({
            "time":      datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "slot":      slot_config.get("label", ""),
            "niche":     slot_config.get("niche", ""),
            "score":     verdict["score"],
            "action":    verdict["action"],
            "reason":    verdict["reason"],
            "preview":   text[:80],
            "signals":   verdict["signals"],
        })

        # Keep last N entries only
        log = log[-MAX_AGENT_LOG:]

        with open(AGENT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
#  HOW TO WIRE INTO auto_post.py
# ─────────────────────────────────────────────────────────────────────────────
"""
Replace the current run_regular_post() body with this pattern:

    from agent import AgentDecision
    agent = AgentDecision()

    # Step 1: Get agent-recommended strategy
    slot = agent.get_strategy(base_slot, slot_name)

    # Step 2: Generate first draft
    text = generate_post(slot, groq_key)

    # Step 3: Agent quality gate (max 2 attempts)
    for attempt in range(1, 3):
        verdict = agent.approve(text, slot, attempt=attempt)

        if verdict["action"] in ("post", "post_anyway"):
            break
        elif verdict["action"] == "regenerate":
            print(f"  Regenerating (attempt {attempt + 1})...")
            text = generate_post(slot, groq_key)
            if not text:
                break

    # Step 4: Post normally
    result = post_carousel_to_facebook(...)
"""


# ─────────────────────────────────────────────────────────────────────────────
#  STANDALONE TEST — python agent.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = AgentDecision()

    test_cases = [
        {
            "label": "Strong post (should PASS)",
            "text": (
                "Stop using ChatGPT wrong. 🚫\n\n"
                "Most people treat it like Google.\n"
                "They type a question. Get an answer. Move on.\n\n"
                "But that's the amateur way.\n"
                "The pros use it as a thinking partner.\n\n"
                "They challenge it. Push back. Ask for alternatives.\n"
                "The difference? 10x better output.\n\n"
                "Comment 'PROMPT' and I'll send my full system 👇\n"
                "#ChatGPT #AI #AITools #Pakistan #Productivity"
            ),
            "slot": {"language": "English", "niche": "AI & Tech", "label": "morning"},
        },
        {
            "label": "Weak post (should REGENERATE)",
            "text": (
                "In today's world, AI is a game changer.\n"
                "Believe in yourself and never give up.\n"
                "Dream big and stay motivated.\n"
                "Follow for more."
            ),
            "slot": {"language": "English", "niche": "Motivation", "label": "afternoon"},
        },
        {
            "label": "Roman Urdu post",
            "text": (
                "Yaar, kya tum ChatGPT sahi use kar rahe ho? 🤔\n\n"
                "Zyada tar log sirf sawal poochte hain.\n"
                "Lekin asli trick hai is se argue karna.\n\n"
                "Jab tum iske jawab ko challenge karte ho,\n"
                "tab woh aur gehri soch deta hai.\n\n"
                "Comment mein 'PROMPT' likho, main apna system share karunga 👇\n"
                "#AI #Pakistan #ChatGPT #Tech"
            ),
            "slot": {"language": "Roman Urdu", "niche": "AI & Tech", "label": "evening"},
        },
    ]

    print("\n" + "=" * 55)
    print("  AGENT DECISION TEST")
    print("=" * 55)

    for case in test_cases:
        print(f"\n📝 {case['label']}")
        print("-" * 40)
        verdict = agent.approve(case["text"], case["slot"])
        print(f"   Score:   {verdict['score']}/100")
        print(f"   Action:  {verdict['action'].upper()}")
        print(f"   Signals: {', '.join(verdict['signals'][:4])}")

    print("\n" + "=" * 55)
    print("  STRATEGY TEST")
    print("=" * 55)
    base = {"niche": "AI & Tech", "hook_id": "curiosity",
            "tone": 7, "variation": "Bold/Controversial", "language": "English"}
    adapted = agent.get_strategy(base, "morning")
    print(f"\n  Base:    hook={base['hook_id']} lang={base['language']}")
    print(f"  Adapted: hook={adapted['hook_id']} lang={adapted['language']}")
