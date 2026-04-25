# ═══════════════════════════════════════════════════════════════════════════
#  app.py — Viral Content Machine (Facebook Auto Poster v2)
#  MODIFIED from original — all new/changed sections marked with # [NEW] or # [MODIFIED]
# ═══════════════════════════════════════════════════════════════════════════

import streamlit as st
import requests
import json
import os
import random
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

# [NEW] Import our new modules
from engine import (
    HOOK_STYLES, NICHE_PROFILES,
    get_hook_names, get_hook_by_name,
    generate_three_variations, generate_single,
    parse_post_sections, get_hook_by_id,
    generate_image_url, post_image_to_facebook,
)
import analytics

# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULE CONFIG — Fixed slots, same every day (Pakistan Standard Time)
# ─────────────────────────────────────────────────────────────────────────────
PKT = pytz.timezone("Asia/Karachi")

SCHEDULE_SLOTS = [
    {
        "label": "🌅 Subah 9:00 AM",
        "hour": 9, "minute": 0,
        "niche": "AI & Tech",
        "hook_id": "curiosity",
        "tone": 7,
        "variation": "Bold/Controversial",
        "language": "English",
    },
    {
        "label": "☀️ Dopahar 2:00 PM",
        "hour": 14, "minute": 0,
        "niche": "Motivation",
        "hook_id": "bold_claim",
        "tone": 8,
        "variation": "Bold/Controversial",
        "language": "Roman Urdu",
    },
    {
        "label": "🌙 Raat 9:00 PM",
        "hour": 21, "minute": 0,
        "niche": "ASMR / Satisfying",
        "hook_id": "relatable_pain",
        "tone": 5,
        "variation": "Emotional",
        "language": "Hinglish",
    },
]

def scheduled_post_job(slot: dict):
    """Called automatically by scheduler — generates + posts without any user action."""
    cfg = load_config()
    api_key = get_api_key(cfg)
    page_token = cfg.get("page_token", "")
    page_id = cfg.get("page_id", "")

    if not api_key or not page_token or not page_id:
        _log_schedule(slot["label"], "SKIPPED — missing API key or Facebook credentials")
        return

    hook = get_hook_by_id(slot["hook_id"])
    result = generate_single(
        niche=slot["niche"],
        hook_style=hook,
        variation=slot["variation"],
        tone_level=slot["tone"],
        api_key=api_key,
        max_retries=4,
        language=slot.get("language", "English"),
    )

    if result.get("error") or not result.get("text"):
        _log_schedule(slot["label"], f"FAILED — {result.get('error')}")
        return

    # Post with image
    img_url = generate_image_url(slot["niche"], result["text"])
    post_result = post_image_to_facebook(page_id, page_token, img_url, result["text"])

    # Fallback to text-only if image post fails
    if not post_result.get("success"):
        post_result = post_to_facebook(page_id, page_token, result["text"])
    status = "POSTED ✅" if post_result.get("success") else f"FB ERROR — {post_result.get('error')}"
    _log_schedule(slot["label"], status, result["text"])

    # Save to history
    analytics.add_to_history({
        "text": result["text"],
        "niche": slot["niche"],
        "hook_style": hook["name"],
        "variation": slot["variation"],
        "tone_level": slot["tone"],
        "auto_scheduled": True,
        "timestamp": datetime.now(PKT).strftime("%Y-%m-%d %H:%M"),
    })

def _log_schedule(label: str, status: str, text: str = ""):
    """Append to schedule log file."""
    log_entry = {
        "time": datetime.now(PKT).strftime("%Y-%m-%d %H:%M:%S"),
        "slot": label,
        "status": status,
        "preview": text[:80] if text else "",
    }
    log_file = "schedule_log.json"
    logs = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    logs.insert(0, log_entry)
    logs = logs[:50]  # Keep last 50 entries
    with open(log_file, "w") as f:
        json.dump(logs, f)

def start_scheduler():
    """Start background scheduler once per app session."""
    if "scheduler_started" not in st.session_state:
        scheduler = BackgroundScheduler(timezone=PKT)
        for slot in SCHEDULE_SLOTS:
            scheduler.add_job(
                scheduled_post_job,
                trigger="cron",
                hour=slot["hour"],
                minute=slot["minute"],
                args=[slot],
                id=f"slot_{slot['hour']}_{slot['minute']}",
                replace_existing=True,
            )
        scheduler.start()
        st.session_state["scheduler_started"] = True
        st.session_state["scheduler"] = scheduler

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG  [MODIFIED — layout changed to wide for new sidebar]
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Viral Content Machine",
    page_icon="🔥",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────────
#  CSS  [MODIFIED — extended original styles + new components]
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #080a14;
    color: #e2e0f0;
}
h1, h2, h3 { font-family: 'Syne', sans-serif !important; }

/* ── Header ── */
.main-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #f97316, #ec4899, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
    line-height: 1.15;
}
.subtitle {
    color: #6b6b8a;
    font-size: 0.88rem;
    margin-top: 3px;
    margin-bottom: 1.6rem;
}

/* ── Variation tabs ── */
.var-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 3px 10px;
    border-radius: 20px;
    display: inline-block;
    margin-bottom: 8px;
}
.var-emotional   { background:#2d1b3d; color:#c084fc; border:1px solid #7c3aed; }
.var-educational { background:#0f2030; color:#38bdf8; border:1px solid #0369a1; }
.var-bold        { background:#2d1000; color:#fb923c; border:1px solid #c2410c; }

/* ── Post preview sections ── */
.preview-container {
    background: #10121f;
    border: 1px solid #1e2138;
    border-radius: 14px;
    overflow: hidden;
    margin: 0.6rem 0 1rem;
}
.preview-hook {
    background: linear-gradient(135deg, #1a0f2e, #150d28);
    border-left: 4px solid #a855f7;
    padding: 1rem 1.3rem;
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2d9f3;
    line-height: 1.5;
}
.preview-hook-label {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #7c3aed;
    margin-bottom: 5px;
}
.preview-body {
    padding: 1rem 1.3rem;
    font-size: 0.95rem;
    color: #c4c2d8;
    line-height: 1.75;
    white-space: pre-wrap;
    border-bottom: 1px solid #1e2138;
}
.preview-cta {
    background: linear-gradient(135deg, #0f1f10, #0a180b);
    border-left: 4px solid #22c55e;
    padding: 0.9rem 1.3rem;
    font-size: 0.92rem;
    color: #86efac;
    line-height: 1.5;
    white-space: pre-wrap;
}
.preview-cta-label {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #16a34a;
    margin-bottom: 5px;
}

/* ── Status banners ── */
.status-success {
    background: #0a2010;
    border: 1px solid #166534;
    color: #4ade80;
    border-radius: 9px;
    padding: 0.7rem 1rem;
    font-size: 0.88rem;
    margin-top: 0.5rem;
}
.status-error {
    background: #200a0a;
    border: 1px solid #7f1d1d;
    color: #fca5a5;
    border-radius: 9px;
    padding: 0.7rem 1rem;
    font-size: 0.88rem;
    margin-top: 0.5rem;
}
.status-warning {
    background: #1c1500;
    border: 1px solid #78350f;
    color: #fcd34d;
    border-radius: 9px;
    padding: 0.7rem 1rem;
    font-size: 0.88rem;
    margin-top: 0.5rem;
}

/* ── Badges ── */
.badge {
    display: inline-block;
    background: #14162a;
    color: #a78bfa;
    border: 1px solid #312e6e;
    border-radius: 20px;
    padding: 2px 11px;
    font-size: 0.76rem;
    font-weight: 500;
    margin-right: 5px;
    margin-bottom: 5px;
}

/* ── Stat cards ── */
.stat-card {
    background: #10121f;
    border: 1px solid #1a1d35;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    text-align: center;
}
.stat-number {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: #a78bfa;
    line-height: 1;
}
.stat-label {
    font-size: 0.72rem;
    color: #5a5878;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
}

/* ── History items ── */
.history-item {
    background: #0d0f1e;
    border: 1px solid #1a1d35;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.55rem;
    font-size: 0.86rem;
    color: #8886a4;
}
.history-meta {
    font-size: 0.73rem;
    color: #3d3d5a;
    margin-bottom: 5px;
}
.history-hook-badge {
    display: inline-block;
    font-size: 0.68rem;
    padding: 1px 8px;
    border-radius: 10px;
    background: #1a1430;
    color: #8b5cf6;
    border: 1px solid #4c1d95;
    margin-left: 6px;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0c0e1b !important;
    border-right: 1px solid #14172b;
}

/* ── Tone slider label override ── */
.tone-safe    { color: #4ade80; }
.tone-mid     { color: #facc15; }
.tone-aggro   { color: #f97316; }

/* ── Hook card ── */
.hook-info {
    background: #0f112a;
    border: 1px solid #1e2248;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-size: 0.82rem;
    color: #7e7ca0;
    margin-bottom: 1rem;
    font-style: italic;
}

div[data-testid="stButton"] button {
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG  [kept from original, extended with new fields]
# ─────────────────────────────────────────────────────────────────────────────
CONFIG_FILE = "fb_config.json"

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"page_token": "", "page_id": "", "gemini_api_key": ""}

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

def get_api_key(cfg: dict) -> str:
    """Get Gemini API key — Streamlit Secrets (cloud) first, then local config."""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return cfg.get("gemini_api_key", "")

# ── Facebook Poster [kept from original, unchanged] ──
def post_to_facebook(page_id: str, page_token: str, message: str):
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    try:
        r = requests.post(url, data={"message": message, "access_token": page_token}, timeout=15)
        data = r.json()
        if "id" in data:
            return {"success": True, "id": data["id"]}
        return {"success": False, "error": data.get("error", {}).get("message", "Unknown Facebook error")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD STATE + START SCHEDULER
# ─────────────────────────────────────────────────────────────────────────────
cfg     = load_config()
history = analytics.load_history()
start_scheduler()  # Starts once per session — runs in background 24/7

# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🔥 Viral Content Machine</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Facebook growth engine · Powered by Groq AI (free, cloud, auto-scheduler)</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  [NEW] SIDEBAR — Niche, Hook Style, Tone Slider
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Content Controls")
    st.markdown("---")

    # [NEW] Niche selector
    st.markdown("**Niche**")
    niche = st.selectbox(
        "niche",
        list(NICHE_PROFILES.keys()),
        label_visibility="collapsed"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # [NEW] Hook style selector
    st.markdown("**Hook Style**")
    hook_options = get_hook_names()
    selected_hook_name = st.selectbox(
        "hook",
        hook_options,
        label_visibility="collapsed"
    )
    selected_hook = get_hook_by_name(selected_hook_name)

    # Show hook psychology tip
    st.markdown(
        f'<div class="hook-info">🧠 <b>Psychology:</b> {selected_hook["psychology"]}</div>',
        unsafe_allow_html=True
    )

    # [NEW] Random hook button
    if st.button("🎲 Random Hook", use_container_width=True):
        st.session_state["random_hook"] = random.choice(HOOK_STYLES)
        st.rerun()

    if "random_hook" in st.session_state:
        selected_hook = st.session_state["random_hook"]
        st.markdown(f'<span class="badge">{selected_hook["name"]}</span>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # [NEW] Tone control slider
    st.markdown("**Tone Level**")
    tone_level = st.slider(
        "tone_level",
        min_value=1, max_value=10, value=5,
        label_visibility="collapsed"
    )

    if tone_level <= 3:
        tone_label = '<span class="tone-safe">🟢 Safe — informative, warm</span>'
    elif tone_level <= 6:
        tone_label = '<span class="tone-mid">🟡 Balanced — direct, engaging</span>'
    else:
        tone_label = '<span class="tone-aggro">🔴 Aggressive — bold, provocative</span>'
    st.markdown(tone_label, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # [NEW] Language selector
    st.markdown("**🌐 Language**")
    language = st.selectbox(
        "language",
        ["English", "Roman Urdu", "Hinglish"],
        label_visibility="collapsed",
        help="Roman Urdu = Urdu in English letters | Hinglish = mixed English+Urdu"
    )
    lang_note = {
        "English": "🇬🇧 International audience",
        "Roman Urdu": "🇵🇰 Pakistani audience — 3-4x more engagement",
        "Hinglish": "🔀 Mixed audience — natural, relatable",
    }
    st.caption(lang_note[language])

    # [NEW] Image toggle
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**🖼️ Post with Image**")
    use_image = st.toggle("Generate image automatically", value=True)
    if use_image:
        st.caption("Free via Pollinations.ai — no API key needed")

    st.markdown("---")
    st.markdown("### 📊 Quick Stats")

    # [NEW] Mini stats
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(history)}</div>
            <div class="stat-label">Total Posts</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{analytics.posts_today(history)}</div>
            <div class="stat-label">Today</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-card" style="margin-top:8px">
        <div class="stat-number">{analytics.posts_this_week(history)}</div>
        <div class="stat-label">This Week</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN TABS  [MODIFIED — 4 tabs now, Analytics is new]
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔥 Generate & Post",
    "⏰ Auto Schedule",
    "⚙️ Settings",
    "📜 History",
    "📊 Analytics"
])


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 1 — GENERATE & POST  [HEAVILY MODIFIED]
# ═════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Generate button row ──
    col1, col2 = st.columns([2, 1])
    with col1:
        generate_btn = st.button(
            "⚡ Generate 3 Variations",
            use_container_width=True,
            type="primary"
        )
    with col2:
        # [NEW] Quick single regenerate
        regen_single = st.button("🎲 New Hook + Regen", use_container_width=True)

    # [NEW] Handle random hook + regenerate
    if regen_single:
        st.session_state["random_hook"] = random.choice(HOOK_STYLES)
        selected_hook = st.session_state["random_hook"]
        generate_btn = True  # Trigger generation below

    # ── [NEW] GENERATION — 3 variations ──
    if generate_btn:
        _api_key = get_api_key(cfg)
        if not _api_key:
            st.markdown('<div class="status-error">❌ Set your Google AI Studio API key in Settings first.</div>', unsafe_allow_html=True)
        else:
            progress = st.progress(0, text="Starting generation...")
            variations_result = {}

            for i, var_type in enumerate(["Emotional", "Educational", "Bold/Controversial"]):
                progress.progress((i * 33), text=f"Generating {var_type} version...")
                result = generate_single(niche, selected_hook, var_type, tone_level, _api_key, language=language)
                variations_result[var_type] = result

            progress.progress(100, text="Done!")
            progress.empty()

            if any(r.get("error") in ("GROQ_INVALID_KEY", "NO_API_KEY") for r in variations_result.values()):
                st.markdown('<div class="status-error">❌ Invalid or missing Groq API key. Check Settings.</div>', unsafe_allow_html=True)
            else:
                st.session_state["variations"]       = variations_result
                st.session_state["generation_niche"] = niche
                st.session_state["generation_hook"]  = selected_hook["name"]
                st.session_state["generation_tone"]  = tone_level
                st.session_state["generation_lang"]  = language
                st.session_state["generation_img"]   = use_image

    # ── [NEW] VARIATIONS DISPLAY — 3 tabs with highlighted preview ──
    if "variations" in st.session_state:
        variations = st.session_state["variations"]

        st.markdown("---")
        st.markdown("#### Choose a Version to Post")

        # Meta badges
        gen_niche = st.session_state.get("generation_niche", niche)
        gen_hook  = st.session_state.get("generation_hook", selected_hook["name"])
        gen_tone  = st.session_state.get("generation_tone", tone_level)
        tone_icon = "🟢" if gen_tone <= 3 else ("🟡" if gen_tone <= 6 else "🔴")

        st.markdown(
            f'<span class="badge">{gen_niche}</span>'
            f'<span class="badge">{gen_hook}</span>'
            f'<span class="badge">{tone_icon} Tone {gen_tone}/10</span>',
            unsafe_allow_html=True
        )

        var_labels = {
            "Emotional": ("var-emotional", "💜 Emotional"),
            "Educational": ("var-educational", "💙 Educational"),
            "Bold/Controversial": ("var-bold", "🔥 Bold/Controversial")
        }

        v_tab1, v_tab2, v_tab3 = st.tabs([
            "💜 Emotional",
            "💙 Educational",
            "🔥 Bold/Controversial"
        ])

        def render_variation_tab(tab_obj, var_key, css_class, label):
            with tab_obj:
                result = variations.get(var_key, {})
                text   = result.get("text", "")
                error  = result.get("error")
                retries = result.get("retries", 0)
                flagged = result.get("flagged_generic", False)

                if error and error != "generic_warning":
                    st.markdown(f'<div class="status-error">❌ {error}</div>', unsafe_allow_html=True)
                    return

                if flagged:
                    st.markdown(
                        '<div class="status-warning">⚠️ Anti-generic filter triggered. Output may be borderline — consider regenerating.</div>',
                        unsafe_allow_html=True
                    )
                if retries > 0 and not flagged:
                    st.caption(f"ℹ️ Regenerated {retries}x to pass quality filter.")

                # [NEW] Highlighted preview with hook + CTA sections
                if text:
                    sections = parse_post_sections(text)
                    st.markdown(f"""
                    <div class="preview-container">
                        <div class="preview-hook">
                            <div class="preview-hook-label">⚡ Hook</div>
                            {sections['hook']}
                        </div>
                        <div class="preview-body">{sections['body']}</div>
                        <div class="preview-cta">
                            <div class="preview-cta-label">🎯 CTA</div>
                            {sections['cta']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # [NEW] Editable text area
                session_key = f"edit_{var_key}"
                if session_key not in st.session_state:
                    st.session_state[session_key] = text

                edited = st.text_area(
                    "✏️ Edit before posting:",
                    value=st.session_state[session_key],
                    height=200,
                    key=f"textarea_{var_key}"
                )
                st.session_state[session_key] = edited

                # [NEW] Action buttons: Approve & Post + Regen this one
                c1, c2 = st.columns([3, 1])
                with c1:
                    post_btn = st.button(
                        f"🚀 Approve & Post — {label}",
                        key=f"post_{var_key}",
                        use_container_width=True,
                        type="primary"
                    )
                with c2:
                    regen_this = st.button("🔄", key=f"regen_{var_key}", use_container_width=True,
                                           help=f"Regenerate only this variation")

                # Regen single variation
                if regen_this:
                    with st.spinner(f"Regenerating {var_key}..."):
                        new_result = generate_single(
                            st.session_state.get("generation_niche", niche),
                            get_hook_by_name(st.session_state.get("generation_hook", selected_hook["name"])),
                            var_key, gen_tone, get_api_key(cfg),
                            language=st.session_state.get("generation_lang", "English")
                        )
                    st.session_state["variations"][var_key] = new_result
                    st.session_state[session_key] = new_result.get("text", "")
                    st.rerun()

                # Post to Facebook
                if post_btn:
                    token   = cfg.get("page_token", "")
                    page_id = cfg.get("page_id", "")
                    final_text = edited.strip()
                    want_image = st.session_state.get("generation_img", True)

                    if not token or not page_id:
                        st.markdown(
                            '<div class="status-error">❌ Add your Facebook credentials in Settings first.</div>',
                            unsafe_allow_html=True
                        )
                    elif not final_text:
                        st.markdown('<div class="status-error">❌ Post text is empty.</div>', unsafe_allow_html=True)
                    else:
                        # Show image preview first if enabled
                        if want_image:
                            gen_niche_img = st.session_state.get("generation_niche", niche)
                            img_url = generate_image_url(gen_niche_img, final_text)
                            st.markdown("**🖼️ Post Image Preview:**")
                            st.image(img_url, use_column_width=True)
                            st.caption("Image auto-generated by Pollinations.ai")

                            col_img, col_txt = st.columns(2)
                            with col_img:
                                post_with_img = st.button("📸 Post with Image", type="primary", key=f"post_img_{var_key}")
                            with col_txt:
                                post_text_only = st.button("📝 Post Text Only", key=f"post_txt_{var_key}")
                        else:
                            post_with_img = False
                            post_text_only = True

                        # Execute post
                        if post_with_img:
                            with st.spinner("Generating image & posting to Facebook..."):
                                gen_niche_img = st.session_state.get("generation_niche", niche)
                                img_url = generate_image_url(gen_niche_img, final_text)
                                fb_result = post_image_to_facebook(page_id, token, img_url, final_text)
                        elif post_text_only:
                            with st.spinner("Posting to Facebook..."):
                                fb_result = post_to_facebook(page_id, token, final_text)
                        else:
                            fb_result = None

                        if fb_result and fb_result.get("success"):
                            st.markdown(
                                f'<div class="status-success">✅ Posted! Post ID: {fb_result.get("id")}</div>',
                                unsafe_allow_html=True
                            )
                            record = analytics.record_post(
                                text=final_text,
                                niche=st.session_state.get("generation_niche", niche),
                                hook_style_name=st.session_state.get("generation_hook", selected_hook["name"]),
                                variation=var_key,
                                tone_level=st.session_state.get("generation_tone", tone_level),
                                post_id=fb_result.get("id")
                            )
                            history.append(record)
                            analytics.save_history(history)
                            del st.session_state["variations"]
                            st.balloons()
                            st.rerun()
                        elif fb_result and not fb_result.get("success"):
                            st.markdown(
                                f'<div class="status-error">❌ Facebook Error: {fb_result.get("error")}</div>',
                                unsafe_allow_html=True
                            )

        render_variation_tab(v_tab1, "Emotional",         "var-emotional", "💜 Emotional")
        render_variation_tab(v_tab2, "Educational",       "var-educational", "💙 Educational")
        render_variation_tab(v_tab3, "Bold/Controversial","var-bold", "🔥 Bold")


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 2 — AUTO SCHEDULE
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("#### ⏰ Auto Schedule — Pakistan Standard Time")
    st.info("App kin waqton par khud post karti hai — tumhara laptop band ho ya tum so rahe ho, koi farq nahi. Streamlit Cloud 24/7 chalta rehta hai.")

    # Scheduler status
    if st.session_state.get("scheduler_started"):
        st.success("✅ Scheduler chal raha hai — 3 posts rozana automatic")
    else:
        st.warning("⚠️ Scheduler abhi start nahi hua — page refresh karo")

    st.markdown("---")
    st.markdown("#### 📅 Fixed Daily Schedule")

    for slot in SCHEDULE_SLOTS:
        hook = get_hook_by_id(slot["hook_id"])
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {slot['label']}")
            with col2:
                st.markdown(f"**Niche:** {slot['niche']}")
                st.markdown(f"**Hook:** {hook['name']} · **Language:** {slot.get('language','English')}")
                st.markdown(f"**Variation:** {slot['variation']} · **Tone:** {slot['tone']}/10")
        st.markdown("---")

    st.markdown("#### 📋 Schedule Log (Last 20 auto-posts)")
    log_file = "schedule_log.json"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
        if logs:
            for log in logs[:20]:
                icon = "✅" if "POSTED" in log.get("status","") else "❌"
                st.markdown(f"{icon} **{log['time']}** — {log['slot']} — {log['status']}")
                if log.get("preview"):
                    st.caption(log["preview"] + "...")
        else:
            st.caption("Abhi koi auto-post nahi hua. Pehli post subah 9 baje hogi.")
    else:
        st.caption("Abhi koi auto-post nahi hua. Pehli post subah 9 baje hogi.")

    st.markdown("---")
    st.warning("⚠️ **Zaruri:** Settings tab mein Facebook credentials aur Groq API key zarur save karo — warna auto-posts fail hongi.")


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 3 — SETTINGS  [kept from original + minor UX improvements]
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### 🔐 Facebook Credentials")
    st.info("Saved locally on your PC in `fb_config.json`. Never transmitted anywhere except Facebook's own API.")

    page_token = st.text_input(
        "Page Access Token",
        value=cfg.get("page_token", ""),
        type="password",
        placeholder="Paste your Facebook Page Access Token here"
    )
    page_id_input = st.text_input(
        "Page ID",
        value=cfg.get("page_id", ""),
        placeholder="e.g. 123456789012345"
    )
    st.markdown("#### 🤖 Groq AI (Free & Fast)")
    st.markdown("Get your **free** API key at [console.groq.com](https://console.groq.com) → API Keys → Create API Key")

    # Show info if key is coming from Streamlit Secrets (cloud deployment)
    cloud_key = False
    try:
        if st.secrets.get("GEMINI_API_KEY", ""):
            cloud_key = True
    except Exception:
        pass

    if cloud_key:
        st.success("✅ Gemini API key loaded from Streamlit Secrets (cloud deployment)")
    else:
        gemini_key_input = st.text_input(
            "Gemini API Key",
            value=cfg.get("gemini_api_key", ""),
            type="password",
            placeholder="AIza..."
        )

    if st.button("💾 Save Settings", type="primary"):
        new_cfg = {
            "page_token": page_token,
            "page_id": page_id_input,
        }
        if not cloud_key:
            new_cfg["gemini_api_key"] = gemini_key_input
        else:
            new_cfg["gemini_api_key"] = cfg.get("gemini_api_key", "")
        save_config(new_cfg)
        cfg = load_config()
        st.success("✅ Saved!")

    st.markdown("---")
    st.markdown("#### 🔌 Test Groq Connection")
    if st.button("Test Connection"):
        test_key = get_api_key(cfg)
        if not test_key:
            st.error("❌ No API key set.")
        else:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 5},
                    headers={"Authorization": f"Bearer {test_key}", "Content-Type": "application/json"},
                    timeout=10
                )
                if r.status_code == 200:
                    st.success("✅ Groq API connected! Model: llama-3.3-70b-versatile")
                elif r.status_code in (401, 403):
                    st.error("❌ Invalid API key. Check your Groq key.")
                else:
                    st.error(f"❌ API error {r.status_code}: {r.text[:200]}")
            except Exception as e:
                st.error(f"❌ Network error: {e}")


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 3 — HISTORY  [MODIFIED — shows new fields: hook, variation, tone]
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### 📜 Post History")

    if not history:
        st.markdown('<div style="color:#3d3d5a; font-size:0.9rem; padding:1rem 0;">No posts yet. Generate your first viral post above!</div>', unsafe_allow_html=True)
    else:
        for item in reversed(history):
            niche_badge   = item.get("niche") or item.get("type", "—")
            hook_badge    = item.get("hook_style", "")
            var_badge     = item.get("variation", "")
            tone_val      = item.get("tone_level", "")
            tone_disp     = f"Tone {tone_val}" if tone_val else ""
            post_id_disp  = item.get('post_id', '—')

            st.markdown(f"""
            <div class="history-item">
                <div class="history-meta">
                    🕐 {item.get('time','—')}
                    &nbsp;·&nbsp; {niche_badge}
                    {f'<span class="history-hook-badge">{hook_badge}</span>' if hook_badge else ''}
                    {f'<span class="history-hook-badge">{var_badge}</span>' if var_badge else ''}
                    {f'<span class="history-hook-badge">{tone_disp}</span>' if tone_disp else ''}
                    &nbsp;·&nbsp; ID: {post_id_disp}
                </div>
                {item.get('text','')[:220]}{'...' if len(item.get('text','')) > 220 else ''}
            </div>
            """, unsafe_allow_html=True)

        if st.button("🗑️ Clear History", type="secondary"):
            analytics.save_history([])
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 4 — ANALYTICS  [NEW TAB]
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("#### 📊 Engagement Analytics")
    st.caption("Hook and niche performance tracking. Engagement fields (likes/comments/shares) are ready — connect Facebook Insights API in the future to auto-fill them.")

    if not history:
        st.info("Post some content first to see analytics here.")
    else:
        # ── Top-level stats row ──
        total  = len(history)
        today  = analytics.posts_today(history)
        weekly = analytics.posts_this_week(history)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{total}</div><div class="stat-label">Total Posts</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{weekly}</div><div class="stat-label">This Week</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{today}</div><div class="stat-label">Today</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_left, col_right = st.columns(2)

        # [NEW] Hook usage breakdown
        with col_left:
            st.markdown("**🔍 Hook Style Usage**")
            hook_summary = analytics.hook_performance_summary(history)
            if hook_summary:
                sorted_hooks = sorted(hook_summary.items(), key=lambda x: x[1]["count"], reverse=True)
                for hook_name, data in sorted_hooks:
                    count = data["count"]
                    pct   = int((count / total) * 100)
                    bar   = "█" * max(1, pct // 5)
                    st.markdown(
                        f'<div style="margin-bottom:6px;font-size:0.82rem;color:#9490b0;">'
                        f'<span style="color:#a78bfa">{hook_name}</span><br>'
                        f'<span style="color:#5a5878">{bar}</span> {count} post{"s" if count!=1 else ""} ({pct}%)'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No hook data yet.")

        # [NEW] Niche + Variation breakdown
        with col_right:
            st.markdown("**📂 Niche Distribution**")
            niche_summary = analytics.niche_usage_summary(history)
            for n, count in sorted(niche_summary.items(), key=lambda x: x[1], reverse=True):
                pct = int((count / total) * 100)
                st.markdown(
                    f'<div style="margin-bottom:6px;font-size:0.82rem;color:#9490b0;">'
                    f'<span style="color:#38bdf8">{n}</span> — {count} ({pct}%)'
                    f'</div>',
                    unsafe_allow_html=True
                )

            st.markdown("<br>**🎭 Variation Usage**")
            var_summary = analytics.variation_usage_summary(history)
            var_colors  = {"Emotional": "#c084fc", "Educational": "#38bdf8", "Bold/Controversial": "#fb923c"}
            for v, count in sorted(var_summary.items(), key=lambda x: x[1], reverse=True):
                color = var_colors.get(v, "#9490b0")
                pct   = int((count / total) * 100)
                st.markdown(
                    f'<div style="margin-bottom:6px;font-size:0.82rem;">'
                    f'<span style="color:{color}">{v}</span> — {count} ({pct}%)'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown("**🎛️ Tone Level Distribution**")
        tone_data = analytics.tone_distribution(history)
        for bucket, count in tone_data.items():
            if count == 0:
                continue
            pct  = int((count / total) * 100)
            bar  = "█" * max(1, pct // 4)
            color = "#4ade80" if "Safe" in bucket else ("#facc15" if "Balanced" in bucket else "#f97316")
            st.markdown(
                f'<div style="margin-bottom:8px;font-size:0.85rem;">'
                f'<span style="color:{color}">{bucket}</span><br>'
                f'<span style="color:#3d3d5a">{bar}</span> {count} post{"s" if count!=1 else ""}'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.caption("💡 Future upgrade: connect Facebook Graph API Insights to auto-pull likes, comments, and reach per post — then this page will show which hook styles actually drive engagement for your audience.")
