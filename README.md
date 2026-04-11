# 🤖 Alice: ADHD Companion Robot | CA5325 Group Project

Multi-modal proactive AI companion for ADHD children (6–12), built with Streamlit + OpenRouter API.

## 🚀 Deploy on Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → "New app"
3. Select your repo, branch `main`, file `app.py`
4. In **Advanced settings → Secrets**, paste:

```toml
OPENROUTER_API_KEY = "sk-or-your-key-here"
VARIANT_A_MODEL = "z-ai/glm-5-turbo"
VARIANT_B_MODEL = "anthropic/claude-sonnet-4"
```

5. Click **Deploy** ✅

## 🖥️ Run Locally

```bash
pip install -r requirements.txt
# Create .env file with: OPENROUTER_API_KEY=sk-or-your-key
streamlit run app.py
```

## 📁 Project Structure

```
├── app.py                  # Main Streamlit app
├── src/
│   ├── prompt_builder.py   # System prompt + Safety Fence
│   ├── safety_filter.py    # Input/output filter
│   ├── crisis_handler.py   # Crisis detection
│   ├── safety_logger.py    # Safety event logging
│   ├── parent_notifier.py  # Parent notification
│   ├── api_client.py       # Backend API client
│   └── config.py           # Configuration
├── requirements.txt
└── .streamlit/
    └── config.toml
```

## 👥 Team

| Member | Role |
|--------|------|
| 王一凡 | Technical Lead & System Architecture |
| Member B | Voice Module (STT/TTS) |
| Member C | Demo Video |
