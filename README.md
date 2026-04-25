# 🔥 Viral Content Machine — Facebook Auto Poster v2

A **psychology-driven Facebook content engine** that generates viral posts using Google Gemini AI — free, cloud-based, no local setup required.

---

## ✨ Features

| Feature | Status |
|---|---|
| 12 Psychology-backed Hook Styles | ✅ |
| 3 Post Variations (Emotional / Educational / Bold) | ✅ |
| 4-Part Structured Post Format (Hook → Value → Punch → CTA) | ✅ |
| Anti-Generic Filter (auto-rejects clichéd output) | ✅ |
| Niche Optimization (AI/Tech, Motivation, ASMR, Business) | ✅ |
| Tone Control Slider (Safe → Balanced → Aggressive) | ✅ |
| Dynamic CTA Engine | ✅ |
| Analytics Tab | ✅ |
| **Google Gemini AI Brain (free cloud API)** | ✅ NEW |
| **One-click Streamlit Cloud deploy (free hosting)** | ✅ NEW |

---

## 🚀 Deploy to Streamlit Cloud (Free — Recommended)

No server, no local computer needed. Runs in the cloud 24/7.

### Step 1 — Fork this repo
Click **Fork** on GitHub to copy it to your account.

### Step 2 — Get a free Gemini API key
Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → **Create API Key** — free, no credit card.

### Step 3 — Deploy
1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **New app** → select your forked repo
3. Set **Main file path** to `app.py`
4. Click **Advanced settings → Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your_key_here"
   ```
5. Click **Deploy** — live in ~1 minute ✅

---

## 💻 Run Locally

```bash
pip install -r requirements.txt

# Set API key via secrets file:
mkdir .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml and add your Gemini key

streamlit run app.py
```

Or skip the secrets file — just enter your API key in the **Settings** tab inside the app.

---

## 🗂️ Files

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit UI |
| `engine.py` | Gemini AI generation, hooks, anti-generic filter |
| `analytics.py` | History tracking & stats |
| `requirements.txt` | Dependencies |
| `.streamlit/secrets.toml.example` | API key template |
| `fb_config.json` | Auto-created locally — **gitignored, never commit** |
| `fb_history.json` | Post history — **gitignored, never commit** |

---

## 🧠 12 Hook Styles

Curiosity Gap · Controversy · Fear/Loss · Authority+Data · Relatable Pain · Bold Claim · Story Hook · List Promise · Provocative Question · Shocking Statistic · Direct Call-Out · Transformation Promise

---

## ⚡ Workflow

1. Sidebar → select Niche, Hook Style, Tone Level
2. **⚡ Generate 3 Variations**
3. Review Emotional / Educational / Bold tabs
4. Edit → **🚀 Approve & Post**
5. **📊 Analytics** to track which hooks work best
