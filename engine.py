# ═══════════════════════════════════════════════════════════════════════════
#  engine.py — Viral Content Generation Engine
#  PATCHED v3 — Groq primary + Gemini REST fallback + emergency templates
#
#  WHAT CHANGED (everything else is identical to original):
#  ─────────────────────────────────────────────────────
#  1. Removed: import google.generativeai as genai  (deprecated SDK)
#  2. Removed: GEMINI_MODEL constant
#  3. Added:   _call_groq(), _call_gemini_rest(), _emergency_template()
#  4. Rewrote: call_ai() — proper 2-provider fallback chain
#  5. Patched: generate_single() — emergency template at final fallback
#  6. Cleaned: generate_image_prompt_via_groq() stale comments removed
#
#  PROVIDER CHAIN:
#  ───────────────
#  Groq (GROQ_API_KEY) → Gemini REST (GEMINI_API_KEY env) → Emergency Template
#
#  KEY MAPPING (matches auto_post.py + workflow secrets):
#  ──────────────────────────────────────────────────────
#  api_key parameter everywhere = GROQ_API_KEY
#  GEMINI_API_KEY read directly from os.environ (fallback, optional)
# ═══════════════════════════════════════════════════════════════════════════

import os
import re
import random
import time

import requests


# ─────────────────────────────────────────────────────────────────────────────
#  HOOK STYLES LIBRARY  (12 psychology-backed hooks)
# ─────────────────────────────────────────────────────────────────────────────
HOOK_STYLES = [
    {
        "id": "curiosity",
        "name": "🔍 Curiosity Gap",
        "examples": [
            "No one is talking about this...",
            "Most people don't know this exists...",
            "I found something that changes everything..."
        ],
        "psychology": "Creates an information gap the brain is compelled to close"
    },
    {
        "id": "controversy",
        "name": "🔥 Controversy",
        "examples": [
            "This is why most people fail...",
            "Hot take: everything you know about this is wrong.",
            "Everyone is doing this — and it's a mistake."
        ],
        "psychology": "Challenges existing beliefs, triggers emotional response and debate"
    },
    {
        "id": "fear",
        "name": "😨 Fear / Loss Aversion",
        "examples": [
            "You're making this mistake daily...",
            "This habit is quietly killing your growth.",
            "Stop doing this before it costs you everything."
        ],
        "psychology": "Loss aversion — fear of losing is 2x stronger than desire to gain"
    },
    {
        "id": "authority",
        "name": "🎓 Authority + Data",
        "examples": [
            "After analyzing 1,000 posts, I found one pattern:",
            "I studied the top 1% creators for 90 days. Here's what separates them:",
            "Data from 500 viral posts reveals one thing in common:"
        ],
        "psychology": "Authority bias + social proof creates instant credibility"
    },
    {
        "id": "relatable_pain",
        "name": "💔 Relatable Pain",
        "examples": [
            "If you feel stuck, read this carefully.",
            "Feeling burned out and invisible online? So was I.",
            "I used to wake up dreading my day. Then one thing changed."
        ],
        "psychology": "Mirror neurons fire when people feel deeply understood"
    },
    {
        "id": "bold_claim",
        "name": "⚡ Pattern Interrupt / Bold Claim",
        "examples": [
            "AI will replace 80% of jobs. Most aren't ready.",
            "The traditional 9-5 is already dead. Millions just don't know it yet.",
            "Everything you've been taught about success is backwards."
        ],
        "psychology": "Unexpected statement forces the brain to stop and evaluate"
    },
    {
        "id": "story",
        "name": "📖 Story Hook",
        "examples": [
            "3 months ago I had zero online presence. Here's exactly what changed:",
            "I failed 47 times before I cracked this.",
            "Last week I discovered something that made me rethink my entire strategy..."
        ],
        "psychology": "Humans are wired to follow narrative arcs — story beginnings compel completion"
    },
    {
        "id": "list_promise",
        "name": "📋 List / Number Promise",
        "examples": [
            "5 AI tools that saved me 20 hours this week:",
            "3 things top creators do that beginners ignore:",
            "7 ASMR triggers that melt stress in under 60 seconds:"
        ],
        "psychology": "Cognitive ease — numbered lists feel scannable and achievable"
    },
    {
        "id": "question",
        "name": "❓ Provocative Question",
        "examples": [
            "What if everything you believe about productivity is wrong?",
            "Why do some people build audiences while others stay invisible?",
            "Are you actually working toward your dream — or just surviving?"
        ],
        "psychology": "Open loops — the brain seeks to close unanswered questions"
    },
    {
        "id": "shocking_stat",
        "name": "📊 Shocking Statistic",
        "examples": [
            "95% of content creators quit within 6 months. Here's why the 5% don't:",
            "The average person spends 7 hours/day on their phone. Most waste it.",
            "Only 3% of people write down their goals. They earn 10x more."
        ],
        "psychology": "Statistics create social comparison, urgency, and self-evaluation"
    },
    {
        "id": "direct_callout",
        "name": "👉 Direct Call-Out",
        "examples": [
            "If you're a creator who feels invisible — this is for you:",
            "This is for anyone building something online from scratch:",
            "Attention: if you feel behind in life, read every word of this."
        ],
        "psychology": "Direct address eliminates the scroll — the reader feels personally spoken to"
    },
    {
        "id": "transformation",
        "name": "🔄 Transformation Promise",
        "examples": [
            "One daily habit that transformed my output in 30 days:",
            "How I went from 0 to 10K followers using only free tools:",
            "The exact mindset shift that changed how I work forever:"
        ],
        "psychology": "Before/after contrast activates aspiration, hope, and belief in change"
    },
]


# ─────────────────────────────────────────────────────────────────────────────
#  NICHE PROFILES — tone, audience, CTA library per niche
# ─────────────────────────────────────────────────────────────────────────────
NICHE_PROFILES = {
    "AI & Tech": {
        "tone_descriptor": "futuristic, insightful, data-driven, slightly provocative",
        "audience": "tech-savvy professionals, AI enthusiasts, developers, early adopters",
        "content_angles": [
            "hidden AI tool reveals", "automation tips", "future predictions",
            "productivity hacks using AI", "AI replacing traditional jobs"
        ],
        "ctas": [
            "Follow for daily AI tools that save you hours ⚡",
            "Comment 'TOOLS' and I'll send my full AI toolkit 🤖",
            "Save this — you'll need it when AI reshapes your industry.",
            "Tag someone who's still doing this manually 👇",
            "Follow before this page blows up 🚀",
            "Drop a '🤖' below if you're already using AI daily."
        ],
        "emojis": "⚡🤖🧠💡🔬📊",
        "hashtag_pool": [
            "#AI", "#ArtificialIntelligence", "#ChatGPT", "#AITools",
            "#TechTrends", "#Automation", "#FutureOfWork", "#MachineLearning",
            "#Productivity", "#AIRevolution", "#TechTwitter", "#OpenAI"
        ]
    },
    "Motivation": {
        "tone_descriptor": "raw, emotional, punchy, deeply human — never preachy",
        "audience": "hustlers, entrepreneurs, self-improvement seekers, anyone who feels stuck",
        "content_angles": [
            "mindset shifts nobody talks about", "the dark side of success",
            "daily habits of high achievers", "failure lessons", "mental toughness"
        ],
        "ctas": [
            "Follow if you're building something great 🔥",
            "Drop a '🔥' if this hit different.",
            "Share this with someone who needs to hear it today.",
            "Save this for your 3 AM motivation.",
            "Comment your biggest goal below 👇",
            "Follow for daily mindset shifts that actually move you."
        ],
        "emojis": "🔥💪🧠✨🎯",
        "hashtag_pool": [
            "#Mindset", "#Motivation", "#GrowthMindset", "#Entrepreneur",
            "#Success", "#HustleSmarter", "#SelfImprovement", "#Discipline",
            "#MentalHealth", "#PersonalDevelopment", "#Grind", "#Winning"
        ]
    },
    "ASMR / Satisfying": {
        "tone_descriptor": "calming, sensory, immersive, gentle — invite the reader into the feeling",
        "audience": "stress relief seekers, ASMR lovers, satisfying content fans, insomniacs",
        "content_angles": [
            "ASMR triggers that melt anxiety", "most satisfying sounds explained",
            "why ASMR works (science)", "best ASMR for sleep", "pop tubes & slime therapy"
        ],
        "ctas": [
            "Follow Abdullah ASMR for daily calm in your feed 😌",
            "Tag someone who desperately needs to relax 💙",
            "Save this for tonight when stress hits.",
            "Comment your favourite ASMR trigger below 🎧",
            "Follow for more satisfying content that quiets your mind ✨",
            "Drop a '😌' if you felt calmer just reading this."
        ],
        "emojis": "😌✨💙🎧🌙",
        "hashtag_pool": [
            "#ASMR", "#ASMRCommunity", "#SatisfyingVideos", "#PopTube",
            "#RelaxingContent", "#StressRelief", "#ASMRSounds", "#Tapping",
            "#SleepAid", "#Calming", "#Tingling", "#ASMRArtist"
        ]
    },
    "Business": {
        "tone_descriptor": "practical, strategic, direct, no-fluff — respect the reader's time",
        "audience": "entrepreneurs, freelancers, small business owners, side hustlers",
        "content_angles": [
            "revenue tactics nobody shares", "client acquisition secrets",
            "the real reason businesses fail", "scaling with zero budget", "pricing psychology"
        ],
        "ctas": [
            "Follow for daily business strategies that actually work 📈",
            "Comment 'SCALE' if you want to grow your business this year.",
            "Save this — implement it this week, not next month.",
            "Tag a business owner who needs to see this 👇",
            "Follow before your competitors do 🎯",
            "Share this with your entrepreneur circle 🤝"
        ],
        "emojis": "📈💰🎯🤝🔑",
        "hashtag_pool": [
            "#Business", "#Entrepreneur", "#SmallBusiness", "#Marketing",
            "#BusinessGrowth", "#StartUp", "#FreelanceTips", "#SideHustle",
            "#Revenue", "#BusinessStrategy", "#Scaling", "#BusinessMindset"
        ]
    }
}


# ─────────────────────────────────────────────────────────────────────────────
#  ANTI-GENERIC FILTER — rejects clichéd, low-engagement output
# ─────────────────────────────────────────────────────────────────────────────
GENERIC_PHRASES = [
    "stay motivated", "work hard every day", "never give up", "success is important",
    "believe in yourself", "just keep going", "you can do it", "dream big",
    "hustle every day", "grind never stops", "be positive", "think positive",
    "success takes time", "be consistent", "stay focused", "keep pushing forward",
    "great things take time", "success is a journey", "be the best version of yourself",
    "unlock your potential", "embrace the journey", "one step at a time",
    "the sky is the limit", "reach for the stars", "hard work pays off",
    "every day is a new opportunity", "make every day count",
    "in today's world", "in today's fast", "in the digital age",
    "it's no secret", "the truth is", "at the end of the day",
    "game changer", "game-changer", "think outside the box",
    "hit the ground running", "move the needle", "low hanging fruit",
    "paradigm shift", "synergy", "disruptive", "leverage",
    "in conclusion", "to sum up", "as we all know",
    "the future is", "exciting times", "we live in a world",
    "it is what it is", "take it to the next level",
    "do what you love", "follow your passion", "make a difference",
    "change the world", "create impact", "add value",
    "most people don't realize", "what nobody tells you",
    "secret that nobody", "hack your way", "10x your",
]

WEAK_OPENERS = [
    "in today", "the truth", "it's no", "as we", "we live",
    "most people", "let me tell", "here's the thing",
    "i want to", "i am going to", "this post is about",
]


def is_generic(text: str) -> bool:
    """Returns True if text contains ANY generic phrase — strict mode."""
    text_lower = text.lower()
    for phrase in GENERIC_PHRASES:
        if phrase in text_lower:
            return True
    first_line = text_lower.split("\n")[0].strip()
    for opener in WEAK_OPENERS:
        if first_line.startswith(opener):
            return True
    return False


def is_too_short(text: str) -> bool:
    """Reject posts under 150 characters or fewer than 2 paragraphs."""
    if len(text.strip()) < 150:
        return True
    paragraphs = [p for p in text.strip().split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  TONE LEVEL DESCRIPTIONS
# ─────────────────────────────────────────────────────────────────────────────
def tone_descriptor(level: int) -> str:
    if level <= 3:
        return "safe and informative — share insights without controversy, warm and inviting"
    elif level <= 6:
        return "balanced and direct — engaging, slightly bold, confident voice"
    else:
        return "aggressive and provocative — bold claims, challenge common beliefs, create debate. Be fearless."


# ─────────────────────────────────────────────────────────────────────────────
#  PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────
VARIATION_INSTRUCTIONS = {
    "Emotional": (
        "Focus on emotional storytelling and relatable human experience. "
        "Make the reader FEEL something — understood, inspired, or slightly uncomfortable. "
        "Personal, vulnerable, and real."
    ),
    "Educational": (
        "Teach one specific, actionable insight. Give real value that makes people "
        "save the post and come back to it. Concrete, specific, useful. No vague advice."
    ),
    "Bold/Controversial": (
        "Make a strong, slightly controversial statement. Challenge mainstream thinking. "
        "Be bold, provocative, and confident. Not offensive — but definitely uncomfortable for some."
    )
}

LANGUAGE_INSTRUCTIONS = {
    "English": {
        "instruction": "Write the ENTIRE post in clear, punchy English.",
        "cta_note": "CTA in English.",
        "hashtag_note": "Use English hashtags.",
    },
    "Roman Urdu": {
        "instruction": """Write the ENTIRE post in Roman Urdu (Urdu words written in English letters).
Example style: "Yaar, kya tumne kabhi socha hai ke AI tera kaam chheen sakti hai? Nahi? To sun..."
Every word must be Roman Urdu. Do NOT mix in English sentences. Only Roman Urdu throughout.""",
        "cta_note": "CTA bhi Roman Urdu mein likho. Jaise: 'Neeche comment karo agar tum bhi yahi sochte ho!'",
        "hashtag_note": "Use Urdu/Pakistan-relevant hashtags like #Pakistan #Urdu #PakistaniYouth",
    },
    "Hinglish": {
        "instruction": """Write the ENTIRE post in Hinglish (natural mix of Hindi/Urdu words and English).
Example style: "Bhai, AI ne seriously sab kuch change kar diya hai. Abhi tak jo log soch rahe the..."
Mix naturally — don't force either language. Sound like a smart Pakistani/Indian friend texting.""",
        "cta_note": "CTA Hinglish mein. Jaise: 'Comment mein batao tum kya sochte ho!'",
        "hashtag_note": "Mix English and Urdu hashtags.",
    },
}

CONTENT_FRAMEWORKS_ENGINE = [
    {"name": "Confession",        "structure": "Personal confession → why it matters → question to reader"},
    {"name": "Myth vs Reality",   "structure": "Common myth → destroy with specific fact → real truth"},
    {"name": "Before/After",      "structure": "Stark transformation → specific turning point → how reader can do it"},
    {"name": "Unpopular Opinion", "structure": "Bold opinion → 2-3 specific reasons → invite debate"},
    {"name": "Behind The Scenes", "structure": "Hidden truth revealed → insider knowledge → reader feels special"},
    {"name": "The Mistake",       "structure": "Specific mistake → what went wrong → clear lesson"},
    {"name": "Numbered Reveal",   "structure": "3 surprising insights → build to best last"},
    {"name": "Sensory Story",     "structure": "Vivid sensory scene → sounds textures smells → transport reader"},
    {"name": "What Nobody Says",  "structure": "What everyone thinks → what nobody says → the real truth"},
    {"name": "Time Machine",      "structure": "You from past → what changed → message to past self"},
]


def build_prompt(niche: str, hook_style: dict, variation: str, tone_level: int,
                 language: str = "English") -> str:
    profile = NICHE_PROFILES[niche]
    hook_examples = "\n".join([f'  • "{ex}"' for ex in hook_style["examples"]])
    hashtags_sample = " ".join(random.sample(profile["hashtag_pool"], min(5, len(profile["hashtag_pool"]))))
    lang = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["English"])
    framework = random.choice(CONTENT_FRAMEWORKS_ENGINE)

    length_guide = {
        "Emotional":          "180-250 words. Deep personal emotional story.",
        "Educational":        "220-300 words. Specific actionable with real examples.",
        "Bold/Controversial": "100-160 words. Short punchy lines. Every word hits.",
    }.get(variation, "180-250 words.")

    niche_context = {
        "AI & Tech":         "Name SPECIFIC 2026 tools: Claude Sonnet 4.6, GPT-5.5, Gemini 2.5 Pro, Cursor, Windsurf, Codex. Real numbers, real impact.",
        "Motivation":        "REAL Pakistan scenarios: raat 2 baje akele kaam, parents ki umeedein, rejection letter, failed attempt.",
        "ASMR / Satisfying": "SPECIFIC sensory: kinetic sand texture, soap crunch sound, slime stretch pop, rain on window glass.",
        "Business":          "Specific numbers: '3 clients in 2 weeks', 'Rs.50k with one skill'. Real Pakistani market.",
    }.get(niche, "Be hyper-specific. Name real things. No vague statements.")

    prompt = f"""You are Pakistan's #1 viral Facebook creator. Posts feel human, raw, real — never AI-generated.

LANGUAGE (non-negotiable): {lang['instruction']}
NICHE: {niche}
SPECIFICS: {niche_context}
HOOK: {hook_style['name']} — {hook_style['psychology']}
VARIATION: {variation}
TONE: {tone_level}/10 {"= aggressive, polarizing" if tone_level >= 7 else "= warm, personal, intimate" if tone_level <= 4 else "= confident, direct, bold"}
LENGTH: {length_guide}

FRAMEWORK: {framework['name']}
Structure: {framework['structure']}

POST FORMAT:
[HOOK — 1-2 lines: {hook_style['name']} psychology]

[BODY — specific details, real feelings, framework structure visible]

[PUNCH — the screenshot-worthy line]

[CTA]: {lang['cta_note']}
End with: {hashtags_sample}

RULES:
1. Return ONLY post text. No labels. No preamble.
2. BANNED: "stay motivated" "work hard" "believe in yourself" "never give up" "dream big"
   "in today's world" "game changer" "think outside the box" "most people don't realize"
3. Max 12 words per line. 3-5 emojis natural.
4. Framework MUST be clearly visible in structure
5. Each post must feel DIFFERENT from typical AI content

Write now:"""

    return prompt


# ─────────────────────────────────────────────────────────────────────────────
#  AI PROVIDER LAYER
#  Chain: Groq (api_key param) → Gemini REST (GEMINI_API_KEY env) → empty
#  Emergency templates handled at generate_single() level, not here.
# ─────────────────────────────────────────────────────────────────────────────

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"          # Primary model (kept for backward compat)
GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",   # Best quality — try first
    "llama-3.1-8b-instant",      # Faster, still solid — rate-limit fallback
    "gemma2-9b-it",              # Google model on Groq — last Groq resort
]

GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)
GEMINI_FREE_MODELS = [
    "gemini-1.5-flash",   # Most reliable free tier as of 2026
    "gemini-1.0-pro",     # Fallback if 1.5-flash also hits quota
]

# ── Emergency templates — used only when ALL AI providers fail ──
EMERGENCY_TEMPLATES = {
    "AI & Tech": """Stop using ChatGPT like Google. 🚫

Everyone types a question and copies the answer.
That's the amateur move.

The pros challenge it.
Push back on the first answer.
Ask: "Give me 3 alternatives."

Output quality goes up 10x instantly.

Comment 'PROMPT' and I'll share my full system 👇

#AI #ChatGPT #AITools #Pakistan #Productivity""",

    "Motivation": """Yaar, sach bolunga.

Success ki koi shortcut nahi.
Lekin smart work zaroor hoti hai.

Roz sirf ek cheez improve karo.
Bas ek.

30 din mein khud fark mahsoos karogay.

Drop a 🔥 if you're building something real.

#Pakistan #Motivation #GrowthMindset #SelfImprovement""",

    "ASMR / Satisfying": """Stress hai? Yeh try karo. 😌

Aankhein band karo.
5 gehri sansein lo.
Apni favorite ASMR sound suno.

Dimagh automatically slow ho jaata hai.
Science bhi yahi kehti hai.

Tag someone who needs to relax right now 💙

#ASMR #StressRelief #Pakistan #Calm #Relaxing""",

    "Business": """Rs. 50,000 per month.
Zero investment.
One skill.

Content writing + AI tools.
Pakistani market mein demand hai.
Fiverr, Upwork, local clients — sab hain.

Shuru karo aaj. Kal mat rakho.

Comment 'HOW' and I'll send the full roadmap 👇

#Pakistan #Business #Freelancing #AI #SideHustle""",
}

EMERGENCY_TEMPLATE_DEFAULT = """AI tools Pakistan mein available hain. 🤖

ChatGPT, Claude, Gemini — sab free mein use karo.
Freelancing, content, coding — sab mein kaam aate hain.

Comment mein batao: kaunsa tool tumhare liye best raha?

Follow karo aur save karo is post ko 👇

#AI #Pakistan #Tech #AITools #Productivity"""


def _call_groq(prompt: str, api_key: str, temperature: float = 0.9) -> str:
    """
    Primary AI provider: Groq with model cascade.
    Tries GROQ_FALLBACK_MODELS in order on rate-limit or errors.

    Args:
        prompt     : Generation prompt
        api_key    : GROQ_API_KEY value
        temperature: 0.0–1.0

    Returns:
        Generated text string, or empty string on all failures.
    """
    if not api_key or not api_key.strip():
        print("  [Groq] No API key — skipping")
        return ""

    for model in GROQ_FALLBACK_MODELS:
        for attempt in range(2):   # 2 attempts per model for transient errors
            try:
                r = requests.post(
                    GROQ_API_URL,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": 600,
                    },
                    headers={
                        "Authorization": f"Bearer {api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )

                if r.status_code == 200:
                    text = r.json()["choices"][0]["message"]["content"].strip()
                    if text and len(text) > 50:
                        print(f"  [Groq] {model} ✓")
                        return text
                    print(f"  [Groq] {model} returned empty/short text")

                elif r.status_code == 429:
                    # Rate limited — exponential wait then try next model
                    wait = 10 * (attempt + 1)
                    print(f"  [Groq] {model} rate-limited — waiting {wait}s")
                    time.sleep(wait)
                    if attempt == 1:
                        print(f"  [Groq] {model} still limited — trying next model")

                elif r.status_code in (401, 403):
                    # Bad key — no point trying other models with same key
                    try:
                        err_msg = r.json().get("error", {}).get("message", "auth error")
                    except Exception:
                        err_msg = r.text[:100]
                    print(f"  [Groq] Auth error {r.status_code}: {err_msg}")
                    return ""

                elif r.status_code == 503:
                    print(f"  [Groq] {model} service unavailable — trying next model")
                    break  # Don't retry same model

                else:
                    try:
                        err_msg = r.json().get("error", {}).get("message", r.text[:120])
                    except Exception:
                        err_msg = r.text[:120]
                    print(f"  [Groq] {model} error {r.status_code}: {err_msg}")
                    break  # Try next model

            except requests.exceptions.Timeout:
                print(f"  [Groq] {model} timeout (attempt {attempt + 1}/2)")
                time.sleep(3)

            except requests.exceptions.ConnectionError:
                print(f"  [Groq] Network error — check connectivity")
                break

            except Exception as e:
                print(f"  [Groq] {model} unexpected error: {e}")
                break

    print("  [Groq] All models exhausted")
    return ""


def _call_gemini_rest(prompt: str, temperature: float = 0.9) -> str:
    """
    Fallback AI provider: Gemini via REST API — no SDK required.
    Reads GEMINI_API_KEY from environment. Silently skips if key not set.

    Uses REST directly to avoid deprecated google.generativeai SDK and its
    quota/version issues.

    Returns:
        Generated text string, or empty string on all failures/missing key.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        # Not configured — silently skip (Gemini is optional fallback)
        return ""

    for model in GEMINI_FREE_MODELS:
        url = GEMINI_REST_URL.format(model=model, key=api_key)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 600,
            },
        }
        for attempt in range(2):
            try:
                r = requests.post(url, json=payload, timeout=30)

                if r.status_code == 200:
                    data = r.json()
                    text = (
                        data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                            .strip()
                    )
                    if text and len(text) > 50:
                        print(f"  [Gemini] {model} ✓")
                        return text
                    print(f"  [Gemini] {model} returned empty text")

                elif r.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"  [Gemini] {model} quota exceeded — waiting {wait}s")
                    time.sleep(wait)

                elif r.status_code in (400, 401, 403):
                    print(f"  [Gemini] {model} auth/config error {r.status_code}: {r.text[:100]}")
                    return ""  # Bad key — skip all Gemini models

                else:
                    print(f"  [Gemini] {model} error {r.status_code}: {r.text[:100]}")
                    break  # Try next model

            except requests.exceptions.Timeout:
                print(f"  [Gemini] {model} timeout (attempt {attempt + 1}/2)")
                time.sleep(5)

            except Exception as e:
                print(f"  [Gemini] {model} exception: {e}")
                break

    print("  [Gemini] All models exhausted")
    return ""


def _emergency_template(niche: str) -> str:
    """
    Absolute last resort when all AI providers fail.
    Returns a curated pre-written post. Never returns empty string.
    This ensures posting schedule is never broken due to API issues.
    """
    template = EMERGENCY_TEMPLATES.get(niche, EMERGENCY_TEMPLATE_DEFAULT)
    print(f"  [Emergency] ⚠️ Using pre-written template for niche: {niche}")
    print(f"  [Emergency] All AI providers failed — check GROQ_API_KEY and GEMINI_API_KEY secrets")
    return template


def call_ai(prompt: str, api_key: str, temperature: float = 0.9) -> str:
    """
    Unified AI caller with 2-provider fallback chain.

    Provider chain (in order):
      1. Groq  — llama-3.3-70b-versatile → llama-3.1-8b-instant → gemma2-9b-it
                 Uses `api_key` param (= GROQ_API_KEY from secrets)
      2. Gemini REST — gemini-1.5-flash → gemini-1.0-pro
                       Uses GEMINI_API_KEY from os.environ (optional, no SDK)

    Args:
        prompt     : The generation prompt
        api_key    : Groq API key (GROQ_API_KEY)
        temperature: Creativity level 0.0–1.0 (default 0.9)

    Returns:
        Generated text string. Returns empty string only if ALL providers
        fail — generate_single() will then apply emergency template.

    NOTE: api_key is the Groq key. Gemini key is read from env automatically.
    This matches how auto_post.py passes secrets (groq_key → api_key param).
    """
    # ── Provider 1: Groq (primary) ──
    text = _call_groq(prompt, api_key, temperature)
    if text:
        return text

    print("  [AI] Groq failed — escalating to Gemini REST fallback")

    # ── Provider 2: Gemini REST (no SDK) ──
    text = _call_gemini_rest(prompt, temperature)
    if text:
        return text

    print("  [AI] ❌ All providers failed")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLE POST GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_single(niche: str, hook_style: dict, variation: str, tone_level: int,
                    api_key: str, max_retries: int = 3,
                    language: str = "English") -> dict:
    """
    Generate one post with anti-generic retry loop.

    Returns:
        {
            "text":            str,
            "error":           None | str,
            "retries":         int,
            "flagged_generic": bool,
        }

    Guarantees: "text" is never empty — emergency template used as last resort.
    """
    if not api_key or not api_key.strip():
        # No Groq key — try Gemini directly then fall back to template
        print("  [Engine] GROQ_API_KEY not set — attempting Gemini fallback")

    last_text = ""
    flagged   = False

    for attempt in range(max_retries):
        prompt      = build_prompt(niche, hook_style, variation, tone_level, language)
        temperature = round(0.82 + (attempt * 0.06), 2)

        try:
            text = call_ai(prompt, api_key, temperature)

            if not text:
                print(f"  [Engine] Attempt {attempt + 1}/{max_retries}: empty response")
                continue

            last_text = text

            if is_too_short(text):
                print(f"  [Engine] Attempt {attempt + 1}/{max_retries}: too short ({len(text)} chars)")
                continue

            if is_generic(text):
                flagged = True
                print(f"  [Engine] Attempt {attempt + 1}/{max_retries}: generic phrase detected — retrying")
                continue

            # Quality passed
            return {
                "text":            text,
                "error":           None,
                "retries":         attempt,
                "flagged_generic": False,
            }

        except requests.exceptions.ConnectionError:
            return {
                "text":            "",
                "error":           "NETWORK_ERROR",
                "retries":         attempt,
                "flagged_generic": False,
            }
        except Exception as e:
            return {
                "text":            "",
                "error":           str(e),
                "retries":         attempt,
                "flagged_generic": False,
            }

    # ── All retries done ──
    # If we have any text (even flagged-generic), use it rather than emergency
    if last_text:
        return {
            "text":            last_text,
            "error":           None,
            "retries":         max_retries,
            "flagged_generic": flagged,
        }

    # Absolute last resort — pre-written template so posting never breaks
    emergency_text = _emergency_template(niche)
    return {
        "text":            emergency_text,
        "error":           "emergency_template",
        "retries":         max_retries,
        "flagged_generic": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  THREE VARIATIONS GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_three_variations(niche: str, hook_style: dict, tone_level: int,
                               api_key: str, language: str = "English") -> dict:
    """
    Generates Emotional, Educational, and Bold/Controversial versions.
    Returns dict keyed by variation name.
    """
    results = {}
    for variation in ["Emotional", "Educational", "Bold/Controversial"]:
        results[variation] = generate_single(
            niche, hook_style, variation, tone_level, api_key, language=language
        )
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  POST STRUCTURE PARSER
# ─────────────────────────────────────────────────────────────────────────────
def parse_post_sections(text: str) -> dict:
    """
    Splits post into paragraphs. Returns hook, body, and cta sections.
    """
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        return {
            "hook": paragraphs[0],
            "body": "\n\n".join(paragraphs[1:-1]),
            "cta":  paragraphs[-1],
        }
    elif len(paragraphs) == 2:
        return {"hook": paragraphs[0], "body": "", "cta": paragraphs[1]}
    else:
        lines = text.strip().split("\n")
        return {
            "hook": lines[0] if lines else text,
            "body": "\n".join(lines[1:-1]),
            "cta":  lines[-1] if len(lines) > 1 else "",
        }


# ─────────────────────────────────────────────────────────────────────────────
#  HOOK STYLE LOOKUPS
# ─────────────────────────────────────────────────────────────────────────────
def get_hook_by_id(hook_id: str) -> dict:
    for h in HOOK_STYLES:
        if h["id"] == hook_id:
            return h
    return HOOK_STYLES[0]


def get_hook_names() -> list:
    return [h["name"] for h in HOOK_STYLES]


def get_hook_by_name(name: str) -> dict:
    for h in HOOK_STYLES:
        if h["name"] == name:
            return h
    return HOOK_STYLES[0]


# ─────────────────────────────────────────────────────────────────────────────
#  IMAGE GENERATION — Groq prompt → Pollinations.ai render → Facebook upload
# ─────────────────────────────────────────────────────────────────────────────

NICHE_BASE_STYLES = {
    "AI & Tech":          "cinematic close-up glowing holographic AI brain, deep space neon blue purple light rays, ultra detailed 8k, dramatic shadows, no text",
    "Motivation":         "cinematic portrait determined person cliff edge sunset, golden hour god rays, silhouette burning sky, ultra realistic 8k, no text",
    "Business & Finance": "luxury dark office dramatic side lighting, gold coins scattered on glass table, editorial photo, ultra sharp 8k, no text",
    "ASMR / Satisfying":  "extreme macro iridescent liquid mercury droplets black surface, rainbow caustics, studio lighting, ultra sharp 8k, perfectly symmetrical, no text",
    "Health & Wellness":  "serene misty forest sunrise, lone figure meditating on rock, volumetric light rays, National Geographic style, no text",
    "Relationships":      "candid emotional moment two people laughing, golden hour bokeh, shallow depth of field, film grain, cinematic, no text",
    "Comedy & Memes":     "vibrant pop art explosion bold colors, dynamic composition, high energy, comic style, no text",
    "News & Trends":      "dramatic cinematic photojournalism, bold lighting, high contrast, award winning press photo, no text",
}


def generate_image_prompt_via_groq(niche: str, post_text: str,
                                    api_key: str) -> str:
    """
    Use Groq (via call_ai) to generate a vivid, specific image prompt.
    Falls back to niche base style if generation fails.
    """
    # Clean post text — remove hashtags, strip non-ASCII (emojis)
    clean_text = re.sub(r"#\w+", "", post_text)
    clean_text = re.sub(r"[^\x00-\x7F]+", "", clean_text).strip()[:300]

    base_style = NICHE_BASE_STYLES.get(
        niche, "cinematic dramatic professional photography, 8k"
    )

    system = """You are a professional AI image prompt engineer.
Given a social media post and niche, write ONE ultra-specific Stable Diffusion image prompt.
Rules:
- No text, no words, no letters in the image
- Hyper-specific visual scene — NOT generic
- Include: subject, lighting, mood, style, camera angle
- Max 80 words
- End with: no text, no words, photorealistic, 8k
- Return ONLY the prompt. Nothing else."""

    user = (
        f"Niche: {niche}\n"
        f"Post: {clean_text}\n"
        f"Base style: {base_style}\n\n"
        "Write the image prompt:"
    )

    try:
        result = call_ai(system + "\n\n" + user, api_key, temperature=0.7)
        if result:
            if "no text" not in result.lower():
                result += ", no text, no words, photorealistic"
            return result
    except Exception as e:
        print(f"  Image prompt generation error: {e}")

    # Fallback to niche base style
    return f"{base_style}, no text, no words, photorealistic, 8k"


def add_text_overlay(img_bytes: bytes, post_text: str,
                      page_name: str = "AI with Abdullah") -> bytes:
    """
    Adds hook text + page watermark overlay on image using Pillow.
    Returns processed image bytes, or original bytes if Pillow fails.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        import textwrap

        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        w, h = img.size

        title_size     = max(36, w // 22)
        watermark_size = max(18, w // 55)

        try:
            font_hook = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_size
            )
            font_wm = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", watermark_size
            )
        except Exception:
            font_hook = ImageFont.load_default()
            font_wm   = ImageFont.load_default()

        # Extract hook line — first non-empty line, cleaned
        lines = [l.strip() for l in post_text.split("\n") if l.strip()]
        hook  = lines[0] if lines else ""
        hook  = re.sub(r"#\w+", "", hook).strip()
        hook  = re.sub(r"[^\x00-\x7F]+", " ", hook).strip()
        if len(hook) > 70:
            hook = hook[:67] + "..."

        # Dark gradient overlay at bottom
        overlay      = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        grad_h       = int(h * 0.45)
        for i in range(grad_h):
            alpha = int(210 * (i / grad_h))
            y     = h - grad_h + i
            draw_overlay.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img, overlay)

        draw     = ImageDraw.Draw(img)
        max_chars = max(20, w // (title_size // 2))
        wrapped   = textwrap.fill(hook, width=max_chars).split("\n")
        line_h    = title_size + 10
        text_y    = h - len(wrapped) * line_h - int(h * 0.07)

        for line in wrapped:
            bbox   = draw.textbbox((0, 0), line, font=font_hook)
            text_w = bbox[2] - bbox[0]
            x      = (w - text_w) // 2
            draw.text((x + 3, text_y + 3), line, font=font_hook, fill=(0, 0, 0, 180))
            draw.text((x, text_y),          line, font=font_hook, fill=(255, 255, 255, 255))
            text_y += line_h

        wm_bbox = draw.textbbox((0, 0), page_name, font=font_wm)
        draw.text(
            (w - (wm_bbox[2] - wm_bbox[0]) - 20, h - watermark_size - 15),
            page_name,
            font=font_wm,
            fill=(255, 255, 255, 160),
        )

        result = img.convert("RGB")
        buf    = io.BytesIO()
        result.save(buf, format="JPEG", quality=92)
        return buf.getvalue()

    except Exception as e:
        print(f"  Text overlay failed: {e} — using raw image")
        return img_bytes


def generate_and_download_image(niche: str, post_text: str, api_key: str,
                                 page_name: str = "AI with Abdullah") -> bytes | None:
    """
    1. Generate vivid prompt via Groq
    2. Fetch from Pollinations.ai (Flux model — free, no key)
    3. Apply hook text + watermark overlay

    Returns processed image bytes or None on download failure.
    """
    import urllib.parse

    prompt  = generate_image_prompt_via_groq(niche, post_text, api_key)
    encoded = urllib.parse.quote(prompt)
    seed    = random.randint(1, 999999)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1080&height=1080&nologo=true&enhance=true&model=flux&seed={seed}"
    )
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            processed = add_text_overlay(r.content, post_text, page_name)
            return processed
        print(f"  Image download failed: HTTP {r.status_code}")
    except Exception as e:
        print(f"  Image download error: {e}")
    return None


def post_image_to_facebook(page_id: str, page_token: str,
                            image_bytes: bytes, caption: str) -> dict:
    """
    Post image to Facebook timeline via /photos endpoint.
    published=true ensures it appears in feed (not just album).
    """
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/photos",
            data={
                "caption":      caption,
                "access_token": page_token,
                "published":    "true",
            },
            files={"source": ("post_image.jpg", image_bytes, "image/jpeg")},
            timeout=60,
        )
        data = r.json()
        print(f"  FB photo post response: {data}")
        if "id" in data or "post_id" in data:
            return {
                "success": True,
                "id":      data.get("post_id", data.get("id")),
                "method":  "photo",
            }
        return {
            "success": False,
            "error":   data.get("error", {}).get("message", str(data)),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
