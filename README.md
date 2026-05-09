# 🔥 Viral Content Machine — Facebook Auto Poster v2

A **psychology-driven Facebook content engine** that generates viral posts using **Groq AI** — free, cloud-based, and Streamlit-powered.

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
| Groq AI Brain (free API) | ✅ |
| Streamlit Cloud Deploy | ✅ |

---

## 🚀 Deploy to Streamlit Cloud

Runs as a Streamlit app in the cloud. For reliable scheduled posting, use an external scheduler or GitHub Actions.

### Setup
1. Fork this repo
2. Get a free Groq API key
3. Deploy on Streamlit Cloud with `app.py`
4. Add secret:
```toml
GEMINI_API_KEY = "your_groq_key_here"
```

---

## 💻 Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Files

- `app.py` → Main Streamlit UI
- `engine.py` → Groq AI generation engine
- `analytics.py` → History + stats
- `requirements.txt` → Dependencies

---

## Workflow
1. Select niche, hook, tone
2. Generate 3 variations
3. Review and edit
4. Post to Facebook
5. Track analytics
