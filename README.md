# 🤖 Alice: ADHD Companion Robot | CA5325 Group Project

Multi-modal proactive AI companion for ADHD children (6–12), built with Streamlit + OpenRouter API.

## 📚 Repository Contents

This repository includes:
- Main Streamlit application
- Safety and crisis-handling modules
- Voice feature development documents for Member B
- STT / TTS comparison and testing records
- Prompt design for ADHD-oriented voice interaction
- Scenario-based test documentation

## 🎤 Voice Module Documentation

Member B is responsible for the voice interaction module, including:
- Speech-to-Text (STT) research and comparison
- Text-to-Speech (TTS) research and comparison
- ADHD-oriented voice prompt design
- End-to-end voice interaction workflow
- Scenario-based testing

Related documents:
- [STT Comparison](docs/stt_comparison.md)
- [TTS Comparison](docs/tts_comparison.md)
- [Prompt Design](docs/prompt_design.md)
- [Scenario Test](docs/scenario_test.md)
- [Voice Test Log](docs/voice_test_log.md)

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
├── app.py                      # Main Streamlit app
├── src/
│   ├── prompt_builder.py       # System prompt + Safety Fence
│   ├── safety_filter.py        # Input/output filter
│   ├── crisis_handler.py       # Crisis detection
│   ├── safety_logger.py        # Safety event logging
│   ├── parent_notifier.py      # Parent notification
│   ├── api_client.py           # Backend API client
│   └── config.py               # Configuration
├── docs/
│   ├── stt_comparison.md       # STT testing and selection
│   ├── tts_comparison.md       # TTS testing and selection
│   ├── prompt_design.md        # ADHD-oriented voice prompt design
│   ├── scenario_test.md        # Four scenario-based tests
│   └── voice_test_log.md       # Test records
├── screenshots/                # Test screenshots and evidence
├── demo/                       # Optional front-end voice demo files
├── requirements.txt
└── .streamlit/
    └── config.toml
```

## 👥 Team

| Member | Role |
|--------|------|
| 王一凡 | Technical Lead & System Architecture |
| 李琬琪 | Voice Module Development (STT/TTS, Prompt Design, Testing) |
| Member C | Demo Video |
