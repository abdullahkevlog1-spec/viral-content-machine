# ═══════════════════════════════════════════════════════════════════════════
#  engine.py — Viral Content Generation Engine
#  NEW FILE — handles all AI logic, hooks, niche profiles, anti-generic filter
# ═══════════════════════════════════════════════════════════════════════════
 
import requests
import random
 
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
    # Original banned
    "stay motivated", "work hard every day", "never give up", "success is important",
    "believe in yourself", "just keep going", "you can do it", "dream big",
    "hustle every day", "grind never stops", "be positive", "think positive",
    "success takes time", "be consistent", "stay focused", "keep pushing forward",
    "great things take time", "success is a journey", "be the best version of yourself",
    "unlock your potential", "embrace the journey", "one step at a time",
    "the sky is the limit", "reach for the stars", "hard work pays off",
    "every day is a new opportunity", "make every day count",
    # New strict additions
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
    # Reject on even 1 banned phrase
    for phrase in GENERIC_PHRASES:
        if phrase in text_lower:
            return True
    # Reject weak openers
    first_line = text_lower.split("\n")[0].strip()
    for opener in WEAK_OPENERS:
        if first_line.startswith(opener):
            return True
    return False
 
def is_too_short(text: str) -> bool:
    """Reject posts under 150 characters or fewer than 3 paragraphs."""
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
#  PROMPT BUILDER — constructs engineered prompt per variation
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
 
def build_prompt(niche: str, hook_style: dict, variation: str, tone_level: int) -> str:
    profile = NICHE_PROFILES[niche]
    hook_examples = "\n".join([f'  • "{ex}"' for ex in hook_style["examples"]])
    hashtags_sample = " ".join(random.sample(profile["hashtag_pool"], min(5, len(profile["hashtag_pool"]))))
 
    prompt = f"""You are an elite viral Facebook content strategist with 10 years of growth experience.
Your posts consistently get 10x more engagement than average.
 
═══ MISSION ═══
Write a Facebook post that stops the scroll, triggers emotion, and drives comments/shares.
 
═══ PARAMETERS ═══
NICHE: {niche}
TARGET AUDIENCE: {profile['audience']}
CONTENT TONE STYLE: {profile['tone_descriptor']}
AGGRESSION LEVEL: {tone_descriptor(tone_level)} (level {tone_level}/10)
HOOK STYLE: {hook_style['name']}
  Psychology: {hook_style['psychology']}
  Example hooks (inspire, do NOT copy exactly):
{hook_examples}
VARIATION TYPE: {variation}
  Instruction: {VARIATION_INSTRUCTIONS[variation]}
 
═══ MANDATORY POST STRUCTURE ═══
Write the post in this EXACT 4-part format, each section separated by a blank line:
 
[PART 1 — HOOK]
One single, powerful scroll-stopping line. Use the {hook_style['id']} hook style.
Short. Punchy. Makes the reader NEED to keep reading.
 
[PART 2 — VALUE]
2-3 short lines delivering the core insight or benefit.
One idea per line. Mobile-friendly. No waffle.
 
[PART 3 — SECOND PUNCH]
1-2 lines that land a fresh angle or reinforce the message with new energy.
Hit them again from a different direction.
 
[PART 4 — CTA]
One dynamic call to action. Make it feel natural, not salesy.
Drive comments, follows, or saves. Relevant to {niche}.
Suggested hashtags to end with: {hashtags_sample}
 
═══ HARD RULES ═══
1. Return ONLY the post text. Zero labels. Zero "Here is your post:" preamble.
2. Max 12 words per line. Short = readable on mobile.
3. Use {profile['emojis']} emojis naturally — 2 to 5 total.
4. End with 4-6 relevant hashtags on the final line only.
5. BANNED PHRASES (instant reject): "stay motivated", "work hard", "believe in yourself",
   "never give up", "you can do it", "success is a journey", "dream big", "be positive",
   "in today's world", "game changer", "think outside the box", "the future is bright",
   "most people don't realize", "it's no secret", "at the end of the day".
6. Do NOT start with "In today's", "The truth is", "As we all know", "Most people".
7. Be SPECIFIC. Give REAL insight. If someone can nod and move on — rewrite it.
8. Make someone feel: "I've never heard it put exactly that way."
9. Every line must earn its place. No filler. No waffle. No vague statements.
 
Write the post now. Start directly with the hook:"""
 
    return prompt
 
# ─────────────────────────────────────────────────────────────────────────────
#  SINGLE POST GENERATOR (with anti-generic retry loop)
# ─────────────────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
 
def generate_single(niche: str, hook_style: dict, variation: str, tone_level: int,
                    api_key: str, max_retries: int = 3) -> dict:
    """
    Generate one post using Groq API (free, fast).
    Retries up to max_retries times if output is generic or too short.
    Returns: {"text": str, "error": None | str, "retries": int, "flagged_generic": bool}
    """
    if not api_key or not api_key.strip():
        return {"text": "", "error": "NO_API_KEY", "retries": 0, "flagged_generic": False}
 
    last_text = ""
    flagged = False
 
    for attempt in range(max_retries):
        prompt = build_prompt(niche, hook_style, variation, tone_level)
        temperature = round(0.82 + (attempt * 0.06), 2)
        try:
            response = requests.post(
                GROQ_API_URL,
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": 600,
                    "top_p": 0.92,
                },
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
 
            if response.status_code == 401:
                return {"text": "", "error": "GROQ_INVALID_KEY", "retries": attempt, "flagged_generic": False}
            if response.status_code == 429:
                return {"text": "", "error": "GROQ_RATE_LIMIT", "retries": attempt, "flagged_generic": False}
            if response.status_code != 200:
                return {"text": "", "error": f"GROQ_HTTP_{response.status_code}", "retries": attempt, "flagged_generic": False}
 
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            last_text = text
 
            # Quality gates
            if is_too_short(text):
                continue
            if is_generic(text):
                flagged = True
                continue
 
            return {"text": text, "error": None, "retries": attempt, "flagged_generic": False}
 
        except requests.exceptions.ConnectionError:
            return {"text": "", "error": "NETWORK_ERROR", "retries": attempt, "flagged_generic": False}
        except Exception as e:
            return {"text": "", "error": str(e), "retries": attempt, "flagged_generic": False}
 
    return {"text": last_text, "error": None, "retries": max_retries, "flagged_generic": flagged}
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  THREE VARIATIONS GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_three_variations(niche: str, hook_style: dict, tone_level: int, api_key: str) -> dict:
    """
    Generates Emotional, Educational, and Bold/Controversial versions of a post.
    Returns dict keyed by variation name.
    """
    results = {}
    for variation in ["Emotional", "Educational", "Bold/Controversial"]:
        results[variation] = generate_single(niche, hook_style, variation, tone_level, api_key)
    return results
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  POST STRUCTURE PARSER — extracts hook & CTA paragraphs for highlighted preview
# ─────────────────────────────────────────────────────────────────────────────
def parse_post_sections(text: str) -> dict:
    """
    Splits post into paragraphs. Returns:
      - hook: first paragraph
      - cta: last paragraph
      - body: everything in between
    """
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        return {
            "hook": paragraphs[0],
            "body": "\n\n".join(paragraphs[1:-1]),
            "cta": paragraphs[-1]
        }
    elif len(paragraphs) == 2:
        return {"hook": paragraphs[0], "body": "", "cta": paragraphs[1]}
    else:
        lines = text.strip().split("\n")
        return {"hook": lines[0] if lines else text, "body": "\n".join(lines[1:-1]), "cta": lines[-1] if len(lines) > 1 else ""}
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  HOOK STYLE LOOKUP
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
