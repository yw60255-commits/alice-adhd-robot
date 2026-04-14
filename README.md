# 🤖 Alice ADHD Companion — 多模态主动伴侣智能体

> **CityU CA5325 Group Project** | 面向香港 ADHD 儿童（6–12岁）的 LLM 驱动社交陪伴机器人

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://alice-adhd-robot.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

🔗 **演示链接**：https://alice-adhd-robot.streamlit.app/
📦 **代码仓库**：https://github.com/yw60255-commits/alice-adhd-robot

---

## 📖 项目简介

Alice 是一个基于 LLM 的多模态主动介入智能体，专为 ADHD 儿童设计。
通过实时生物信号监测（心率、专注度、噪音）+ 语音交互，在儿童情绪崩溃前主动介入，
提供个性化情绪调节策略，并向家长/老师推送安全警报。

---

## ✨ 核心功能

### 🎤 多模态输入
- **按住说话**：`st.audio_input` 录音 + **Whisper tiny** 本地语音识别（无需云端 API）
- **文字聊天**：多轮对话，支持上下文记忆（最近 20 条）
- **WAV 上传备用**：兼容老版本 Streamlit

### 🧠 实时生物信号监测
| 指标 | 范围 | 预警阈值 |
|------|------|---------|
| 心率 (HR) | 60–160 bpm | > 105 bpm |
| 心率变异性 (HRV) | 10–100 ms | < 30 ms |
| 专注度 (Attention) | 0–100% | < 40% |
| 环境噪音 | 30–120 dB | > 75 dB |

### 🚀 主动介入引擎
6 大场景自动识别 + 策略匹配：

| 场景 | 触发条件 | 策略 |
|------|---------|------|
| MTR Overload | HR > 125 + 噪音 > 95dB | Sensory Grounding |
| Homework Anxiety | 注意力 < 15% | Role Reversal |
| Home Hyperactive | HR > 110 + HRV < 35 | Task Chunking |
| Restaurant Waiting | 注意力 < 25% | Sensory Grounding |
| Toy Fixation | "want" + Mall 场景 | Delay of Gratification |
| Danger Alert | 危机词汇检测 | Breathing Anchor |

### 🛡️ Safety Fence（7 条安全规则）
Rule 1 🚫 禁止催促/命令词
Rule 2 🌡️ 情绪激动 → 自动降级任务
Rule 3 🆘 危机词汇 → 强制升级处理
Rule 4 ❤️ 高心率 → 切换感知介入模式
Rule 5 🔊 噪音 > 75dB → 环境提示
Rule 6 🧠 专注度 < 40% → 暂停当前任务
Rule 7 ✂️ 回复字数控制在 100 字内

text

### 🔊 TTS 语音朗读
- 使用 **Edge TTS**（`zh-HK-HiuMaanNeural`，粤语/普通话）
- 自动过滤英文/表情符号，仅朗读中文内容
- 音频缓存（相同文本只生成一次）

### 🔬 A/B 测试
- **Variant A**：`z-ai/glm-5-turbo`（快速、低成本）
- **Variant B**：`anthropic/claude-sonnet-4`（高质量）
- 自动记录延迟、Token 用量、场景分布

### 📊 Parent Dashboard（家长/老师看板）
- 实时 KPI：警报次数、平均专注度、高风险互动、Safety Rate
- 互动趋势图（每日心率/注意力变化）
- 场景分布饼图
- Safety Fence 触发日志
- 一键导出 CSV 报告

### 🚇 MTR 实时数据集成
- 接入 **DATA.GOV.HK MTR Next Train API**
- 候车时间 > 5 分钟自动触发 Pre-soothing 策略

---

## 🛠️ 技术架构
┌─────────────────────────────────────────────┐
│ Streamlit Frontend │
│ Child UI (实时监测 + 交互) │
│ Parent Dashboard (数据看板) │
└──────────────┬──────────────────────────────┘
│
┌──────────────▼──────────────────────────────┐
│ Core Modules (src/) │
│ PromptBuilder → 场景化 System Prompt │
│ SafetyFilter → 输入/输出过滤 │
│ CrisisHandler → 危机词汇检测 │
│ ParentNotifier → 家长警报推送 │
│ SafetyLogger → 安全事件日志 │
└──────────────┬──────────────────────────────┘
│
┌──────────────▼──────────────────────────────┐
│ AI / ML │
│ OpenRouter API → GLM-5-Turbo / Claude │
│ Whisper tiny → 本地语音识别 (ASR) │
│ Edge TTS → 香港粤语语音合成 (TTS) │
└─────────────────────────────────────────────┘

text

---

## 🚀 快速开始

### 前置要求
- Python 3.10+
- OpenRouter API Key（[获取免费 Key](https://openrouter.ai)）

### 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/yw60255-commits/alice-adhd-robot
cd alice-adhd-robot

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 5. 启动
streamlit run app.py
```

### 环境变量配置（`.env`）

```env
# OpenRouter（必填）
OPENROUTER_API_KEY=sk-or-v1-你的密钥
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# 模型配置（可选）
VARIANT_A_MODEL=z-ai/glm-5-turbo
VARIANT_B_MODEL=anthropic/claude-sonnet-4

# 功能开关
ENABLE_VOICE_INPUT=true
ENABLE_VOICE_OUTPUT=true
ENABLE_SAFETY_FENCE=true
```

### Streamlit Cloud 部署

在 **Secrets** 中添加：
```toml
OPENROUTER_API_KEY = "sk-or-v1-你的密钥"
```

---

## 📦 依赖库
streamlit
openai
python-dotenv
plotly
pandas
torch
transformers
librosa
soundfile
edge-tts
requests

text

---

## 📁 项目结构
alice-adhd-robot/
├── app.py # 主程序
├── .env # 环境变量（不上传 Git）
├── requirements.txt # Python 依赖
├── logs/ # 会话日志（自动生成）
│ ├── session_logs.jsonl
│ └── safety_events.jsonl
└── src/
├── prompt_builder.py # 场景化 Prompt 构建
├── api_client.py # FastAPI 后端客户端
├── config.py # 配置管理
├── safety_filter.py # 输入/输出安全过滤
├── crisis_handler.py # 危机事件处理
├── parent_notifier.py # 家长通知模块
└── safety_logger.py # 安全事件记录

text

---

## 👥 团队分工

| 角色 | 负责模块 |
|------|---------|
| Member 1 WANG Yifan | Coding, webpage construction, system architecture, prototype optimization, SafetyFence integration, dashboard improvement, and prototype support. |
| Member 2 LI Wanqi | Voice module research, STT/TTS integration, and ADHD-friendly voice design. |
| Member 3 GUO Ruibo | Demoscript, recording,editing, subtitles, and video presentation. |
| Member 4 LIU Sinuo | User research, persona design,journey map, dialogue scripts, and evidence collection.  |
| Member 5 GU Tianshu | Evaluation framework, A/B testing,impact analysis, deployment plan, and future
roadmap. |
---

## 📄 License

MIT License © 2026 CityU CA5325 Group Project
