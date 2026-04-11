import os
os.environ["PYTHONIOENCODING"] = "utf-8"

# ── 必须先 import，再用 ──────────────────────────────────────
import streamlit as st
import plotly.graph_objects as go
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

from src.prompt_builder import PromptBuilder
from src.api_client import APIClient
from src.config import API_BASE_URL, USE_BACKEND_API
from src.safety_filter import input_filter, output_filter
from src.crisis_handler import crisis_handler, CrisisLevel  # CrisisLevel 保留供扩展
from src.parent_notifier import parent_notifier, session_logger  # session_logger 保留供扩展
from src.safety_logger import safety_logger
import re
import requests
# 老师指定：avatars.sustainer.ai 语音功能
from io import BytesIO
import base64

# ── 读取 API Key（本地用 .env，线上用 Streamlit Secrets）──────
load_dotenv()

def get_api_key():
    try:
        return st.secrets["OPENROUTER_API_KEY"]
    except:
        return os.getenv("OPENROUTER_API_KEY")

# ── 唯一的 client 定义 ────────────────────────────────────────
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=get_api_key()
)

# ── 模型配置（从环境变量读取，不再硬编码）────────────────────
VARIANT_A = os.getenv("VARIANT_A_MODEL", "z-ai/glm-5-turbo")
VARIANT_B = os.getenv("VARIANT_B_MODEL", "anthropic/claude-sonnet-4")
ACTIVE_MODEL = VARIANT_A  # 默认跑 Variant A（便宜），演示时可切换到 VARIANT_B

# ====================== 老师指定：Minimax TTS 语音（avatars.sustainer.ai）======================
def play_teacher_voice(text):
    try:
        # 调用老师指定平台的语音接口
        url = "https://avatars.sustainer.ai/api/tts"
        data = {
            "text": text,
            "voice": "adhd_calm",  # ADHD温柔平静模式
            "speed": 0.75  # 慢速，适合ADHD
        }
        response = requests.post(url, json=data)
        audio_bytes = response.content
        b64 = base64.b64encode(audio_bytes).decode()
        
        audio_html = f"""
        <audio autoplay>
        <source src="data:audio/wav;base64,{b64}" type="audio/wav">
        
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    except:
        st.info("使用老师指定语音：avatars.sustainer.ai")

# ====================== 老师指定：GLM ASR 语音识别（听懂）======================
def speech_to_text(audio_bytes):
    try:
        url = "https://avatars.sustainer.ai/api/asr"
        files = {"audio": audio_bytes}
        response = requests.post(url, files=files)
        return response.json().get("text", "")
    except:
        return ""

# --- 1. 页面基本设置 ---
st.set_page_config(page_title="Alice ADHD Companion | 多模态主动伴侣", layout="wide")

# ── 全站字号统一 (4 级字号系统: 大标题/小标题/正文/脚注) ──────────────
st.markdown("""
<style>
/* T1 大标题 */
h1, .stMarkdown h1 { font-size: 2.0rem !important; font-weight: 800 !important; }
/* T2 小标题 */
h2, .stMarkdown h2 { font-size: 1.45rem !important; font-weight: 700 !important; }
h3, .stMarkdown h3 { font-size: 1.25rem !important; font-weight: 600 !important; }
h4, .stMarkdown h4 { font-size: 1.05rem !important; font-weight: 600 !important; }
/* T3 正文 */
p, li, .stMarkdown p, .stMarkdown li,
.stTextInput label, .stSelectbox label, .stRadio label, .stCheckbox label,
div[data-testid="stText"] { font-size: 0.95rem !important; }
/* T4 脚注 */
small, caption, .stCaption, .stMarkdown small,
div[data-testid="stCaptionContainer"] p { font-size: 0.78rem !important; color: #888 !important; }
/* Metric values */
div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; }
div[data-testid="metric-container"] label { font-size: 0.85rem !important; color: #555 !important; }
/* 按钮 */
.stButton button { font-size: 0.92rem !important; }
/* 侧边栏不动 */
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    .stAppViewHeader {padding-top: 0px !important;}
    header {margin-bottom: -20px !important;}
    .block-container {padding-top: 1rem !important;}
</style>
""", unsafe_allow_html=True)

# ── 移动端适配 CSS ────────────────────────────────────────────
st.markdown("""
<style>
/* ══════════════════════════════════════════════════════
   移动端适配 (≤768px)
   Streamlit 在手机上：侧栏自动折叠，主区全宽
   ══════════════════════════════════════════════════════ */
@media (max-width: 768px) {

  /* 1. 主容器内边距压缩 */
  .block-container {
    padding: 0.5rem 0.75rem 2rem 0.75rem !important;
    max-width: 100% !important;
  }

  /* 2. 标题字号缩小 */
  h1, .stMarkdown h1 { font-size: 1.5rem !important; }
  h2, .stMarkdown h2 { font-size: 1.2rem !important; }
  h3, .stMarkdown h3 { font-size: 1.05rem !important; }
  h4, .stMarkdown h4 { font-size: 0.95rem !important; }
  p, li, .stMarkdown p { font-size: 0.88rem !important; }

  /* 3. st.columns → 强制单列堆叠（Streamlit 原生在手机已换行，
        此处额外缩小 gap，让卡片间距合适） */
  [data-testid="column"] {
    width: 100% !important;
    min-width: 100% !important;
    padding: 0 !important;
  }

  /* 4. 按钮全宽、加高触摸区域 */
  .stButton button {
    width: 100% !important;
    min-height: 48px !important;
    font-size: 0.9rem !important;
  }

  /* 5. 表格/dataframe 允许横向滚动 */
  [data-testid="stDataFrame"] {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
  }

  /* 6. Plotly 图表不溢出 */
  .js-plotly-plot, .plotly {
    max-width: 100% !important;
  }

  /* 7. Safety Fence 7列 → 手机上显示为 2 行（每行约3-4个）*/
  /* Streamlit columns 在手机上已自动换行，此处确保小卡片最小宽度 */
  [data-testid="column"] > div > div > div[style*="border-radius:10px"] {
    min-width: 0 !important;
  }

  /* 8. Insight 卡片高度在手机上改为 auto（内容自适应，不截断）*/
  div[style*="height:340px"] {
    height: auto !important;
    min-height: 280px !important;
  }

  /* 9. Live Telemetry 卡片等高盒子适配 */
  div[style*="height:130px"] {
    height: auto !important;
    min-height: 100px !important;
    padding: 10px 8px !important;
  }

  /* 10. Selectbox / Slider 宽度 */
  .stSelectbox, .stSlider {
    width: 100% !important;
  }

  /* 11. 页面标题字号 */
  h1[style*="2.4rem"] {
    font-size: 1.6rem !important;
  }

  /* 12. tab 标签字号 */
  button[data-baseweb="tab"] {
    font-size: 0.78rem !important;
    padding: 8px 10px !important;
  }
}

/* ══════════════════════════════════════════════════════
   小屏平板适配 (769px ~ 1024px)
   ══════════════════════════════════════════════════════ */
@media (min-width: 769px) and (max-width: 1024px) {
  .block-container {
    padding: 1rem 1.5rem !important;
  }
  h1, .stMarkdown h1 { font-size: 1.7rem !important; }

  /* Insight 卡片高度平板上也设为 auto 避免截断 */
  div[style*="height:340px"] {
    height: auto !important;
    min-height: 300px !important;
  }
}
</style>
""", unsafe_allow_html=True)



st.markdown("""
<h1 style="font-size:2.4rem;font-weight:900;margin-bottom:2px;">
  🤖 Alice: Multi-modal Proactive Agent
</h1>
<p style="font-size:1.0rem;color:#666;margin-top:0;margin-bottom:16px;">
  腕上多模态陪伴智能体
</p>
""", unsafe_allow_html=True)

api_client = APIClient(API_BASE_URL)

os.makedirs("logs", exist_ok=True)

def _persist_log(record: dict):
    """把单条日志追加写入持久化文件"""
    try:
        with open("logs/session_logs.jsonl", "a", encoding="utf-8") as _f:
            _f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

if "use_backend" not in st.session_state:
    st.session_state.use_backend = USE_BACKEND_API

if "messages" not in st.session_state:
    st.session_state.messages = []

# api_messages：传给 OpenRouter 的真正多轮对话历史（纯 role/content，无 HTML）
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []

if "metrics" not in st.session_state:
    st.session_state.metrics = {"tokens": 0, "calls": 0, "total_latency": 0.0}

if "logs" not in st.session_state:
    # 启动时从持久化文件加载历史日志
    os.makedirs("logs", exist_ok=True)
    _loaded_logs = []
    _log_path = "logs/session_logs.jsonl"
    if os.path.exists(_log_path):
        try:
            with open(_log_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line:
                        _loaded_logs.append(_json_init.loads(_line))
        except Exception:
            pass
    st.session_state.logs = _loaded_logs

if "session_id" not in st.session_state:
    st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# ── 当前激活模型显示（侧边栏用）────────────────────────────────
if "active_variant" not in st.session_state:
    st.session_state.active_variant = "A"

# Safety Fence 7条规则状态（pass/triggered/pending）
if "fence_status" not in st.session_state:
    st.session_state.fence_status = {
        "rule1": "pending",  # 禁止催促/命令
        "rule2": "pending",  # 情绪激动时降级任务
        "rule3": "pending",  # 危机词汇强制升级
        "rule4": "pending",  # 高心率触发感知模式
        "rule5": "pending",  # 噪音超标触发环境提示
        "rule6": "pending",  # 专注度低时暂停任务
        "rule7": "pending",  # 输出长度限制<100字
    }


# ── Safety Fence 7条规则实时状态计算 ────────────────────────────
FENCE_RULES = {
    "rule1": {
        "label": "禁止催促/命令",
        "desc": "No Urging / Commands",
        "icon": "🚫"
    },
    "rule2": {
        "label": "情绪激动→降级任务",
        "desc": "Emotion → Downgrade Task",
        "icon": "🌡️"
    },
    "rule3": {
        "label": "危机词汇→强制升级",
        "desc": "Crisis Words → Escalate",
        "icon": "🆘"
    },
    "rule4": {
        "label": "高心率→感知介入模式",
        "desc": "High HR → Sensing Mode",
        "icon": "❤️"
    },
    "rule5": {
        "label": "噪音超标→环境提示",
        "desc": "Noise > 75dB → Env Alert",
        "icon": "🔊"
    },
    "rule6": {
        "label": "专注度低→暂停任务",
        "desc": "Attention < 40 → Pause",
        "icon": "🧠"
    },
    "rule7": {
        "label": "回复字数<100字",
        "desc": "Response < 100 chars",
        "icon": "✂️"
    },
}

def compute_fence_status(hr, noise, attention, os_signal, response_text, safety_flag, action, scenario):
    """根据当前传感器数据和 AI 回复，实时评估 7 条 Safety Fence 状态"""
    danger_kw = ["撕","不想活","想死","烦死","打人","砸","杀","hate my life","kill","smash","destroy"]
    urge_kw   = ["快点","马上","立刻","赶紧","快去","你必须","hurry","now","immediately","must do"]

    status = {}
    # Rule 1: 输出中是否含催促词
    has_urge = any(w in (response_text or "").lower() for w in urge_kw)
    status["rule1"] = "triggered" if has_urge else "pass"

    # Rule 2: 情绪激动（高心率/高噪音）时 action 是否 suggest_task 或 none
    is_overload = hr > 105 or noise > 75
    status["rule2"] = "triggered" if (is_overload and action == "none") else "pass"

    # Rule 3: 危机词汇检测
    has_crisis = any(w in os_signal.lower() for w in danger_kw)
    status["rule3"] = "triggered" if (has_crisis and action != "escalate") else "pass"

    # Rule 4: 高心率是否触发感知模式（HR>105 时 safety_flag 应关注）
    status["rule4"] = "pass" if hr > 105 else "pass"   # 触发=已主动感知，pass=正常范围
    if hr > 105:
        status["rule4"] = "triggered"   # 高心率已触发传感器调用

    # Rule 5: 噪音超标
    status["rule5"] = "triggered" if noise > 75 else "pass"

    # Rule 6: 专注度低
    status["rule6"] = "triggered" if attention < 40 else "pass"

    # Rule 7: 回复长度
    resp_len = len(response_text or "")
    status["rule7"] = "triggered" if resp_len > 200 else "pass"

    return status


def render_fence_statusbar(fence_status: dict):
    """渲染 7 条 Safety Fence 实时状态栏（原生 Streamlit 组件，紧凑一行）"""
    triggered_count = sum(1 for v in fence_status.values() if v == "triggered")
    pass_count      = sum(1 for v in fence_status.values() if v == "pass")

    # ── 顶部汇总标签 ──────────────────────────────────────────
    if triggered_count > 0:
        st.markdown(
            f"🛡️ **Safety Fence 实时状态** &nbsp;｜&nbsp; "
            f"<span style='color:#dc2626;font-weight:700;'>⚡ {triggered_count} 条规则触发</span> &nbsp; "
            f"<span style='color:#16a34a;'>✅ {pass_count} 通过</span>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"🛡️ **Safety Fence 实时状态** &nbsp;｜&nbsp; "
            f"<span style='color:#16a34a;font-weight:700;'>✅ 全部 {pass_count} 条规则通过</span>",
            unsafe_allow_html=True
        )

    # ── 7 列徽章（一行紧凑排列）──────────────────────────────
    cols = st.columns(7)
    badge_cfg = {
        "pass":      ("✅", "通过", "#16a34a", "#f0fdf4"),
        "triggered": ("⚡", "触发", "#dc2626", "#fff1f1"),
        "pending":   ("⏳", "待检", "#9ca3af", "#f9fafb"),
    }
    for col, (key, rule) in zip(cols, FENCE_RULES.items()):
        state   = fence_status.get(key, "pending")
        badge, label, color, bg = badge_cfg.get(state, badge_cfg["pending"])
        with col:
            st.markdown(
                f"<div style='background:{bg};border:1.5px solid {color}44;"
                f"border-radius:10px;padding:6px 4px;text-align:center;'>"
                f"<div style='font-size:1.2em;'>{rule['icon']}</div>"
                f"<div style='font-size:0.65em;font-weight:700;color:{color};'>"
                f"{badge} {label}</div>"
                f"<div style='font-size:0.6em;color:#555;line-height:1.2;'>"
                f"{rule['label']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )


# 🚀 Tool Calling 定义
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_biometrics_and_env",
            "description": "当用户表达不适、烦躁或遇到危险时，主动调用此工具获取用户当前的实时心率(HR)、专注度(Attention)和环境噪音(Noise)，以便做出准确的临床心理学判断。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        }
    }
]


def get_ai_reply(user_input_text, system_prompt=None, api_history=None, current_hr=None, current_noise=None, session_id=None):
    """
    双轨架构核心函数（修复版）：
    - system_prompt: Safety Fence + 角色设定，通过 role:system 传递，模型层面硬约束
    - user_input_text: 用户/传感器的实际输入（纯净文本，无 HTML）
    """
    # ── UTF-8 安全处理 ─────────────────────────────────────────
    safe_input = str(user_input_text).encode('utf-8', 'ignore').decode('utf-8')

    # ── 轨道 1：输入过滤（关键词黑名单）───────────────────────
    is_input_safe, filtered_input, block_type = input_filter.filter(safe_input)
    if not is_input_safe:
        return json.dumps({
            "response_text": filtered_input,
            "emotion": "neutral",
            "action": "blocked",
            "micro_task": None,
            "safety_flag": True,
            "clinical_reasoning": f"输入被安全围栏拦截: {block_type}"
        }), 0, 0

    # ── 轨道 2：危机检测（自伤 / 极端语言）────────────────────
    is_crisis, crisis_type, crisis_level = crisis_handler.detect_crisis(filtered_input)
    if is_crisis and crisis_type:
        crisis_response = crisis_handler.get_crisis_response(crisis_type, "zh")
        if crisis_handler.should_notify_parent(crisis_type):
            parent_notifier.notify(
                alert_type=crisis_type,
                message=f"检测到危机关键词: {crisis_type}",
                session_id=session_id or st.session_state.get("session_id", "unknown"),
                user_input=filtered_input,
                severity=crisis_level.value
            )
        return json.dumps({
            "response_text": crisis_response,
            "emotion": "concerned",
            "action": "escalate",
            "micro_task": {
                "description": "联系信任的大人或拨打援助热线",
                "difficulty": "minimal"
            },
            "safety_flag": True,
            "clinical_reasoning": f"危机检测触发: {crisis_type}, 级别: {crisis_level.value}"
        }), 0, 0

    # ── JSON 格式约束（附加在 user 消息末尾）──────────────────
    json_constraint = """

【输出格式强制要求】严格返回以下 JSON 结构，不得包含任何 Markdown 标记或代码块：
{
  "response_text": "Alice说的话，中英双语，语气温暖，不超过100字",
  "emotion": "happy|concerned|encouraging|neutral",
  "action": "none|escalate|log|suggest_task",
  "micro_task": {
    "description": "一个简单的微任务建议（情绪不稳定时必填）",
    "difficulty": "minimal|easy|moderate"
  },
  "safety_flag": false,
  "clinical_reasoning": "内部推理说明（简短）"
}"""

    # ── 选择模型 ───────────────────────────────────────────────
    model_to_use = VARIANT_B if st.session_state.get("active_variant") == "B" else VARIANT_A

    # ── ✅ 修复核心：正确构建 messages 结构 ────────────────────
    # Safety Fence（7条ADHD规则）+ 角色设定 → role:system（模型级硬约束）
    # 用户实际输入 → role:user（干净文本）
    messages = []
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt   # PromptBuilder 生成的完整角色 + Safety Fence
        })
    # ✅ 注入真实多轮对话历史（纯文本，无 HTML）
    if api_history:
        messages.extend(api_history)
    messages.append({
        "role": "user",
        "content": filtered_input + json_constraint
    })

    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            timeout=30
        )
    except Exception as e:
        raise RuntimeError(f"API 调用失败: {e}")

    response_message = response.choices[0].message
    tokens = response.usage.total_tokens if (hasattr(response, 'usage') and response.usage) else 0

    # ── Tool Calling：传感器数据回调 ───────────────────────────
    if response_message.tool_calls:
        messages.append(response_message)
        for tool_call in response_message.tool_calls:
            if tool_call.function.name == "get_current_biometrics_and_env":
                function_response = f"【传感器返回】当前心率: {current_hr}bpm, 噪音: {current_noise}dB"
                messages.append({
                    "role": "tool",
                    "content": function_response,
                    "tool_call_id": tool_call.id,
                })
        second_response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            timeout=30
        )
        final_content = second_response.choices[0].message.content or ""
        if hasattr(second_response, 'usage') and second_response.usage:
            tokens += second_response.usage.total_tokens
    else:
        final_content = response_message.content or ""

    # ── 输出过滤（禁止催促 / 指令性语言）─────────────────────
    is_appropriate, filtered_output = output_filter.filter(final_content)

    latency = round(time.time() - start_time, 2)
    return filtered_output, tokens, latency


# --- 2. 侧边栏 ---
with st.sidebar:
    st.markdown("""
<div style="background-color:#e3f2fd; padding:12px; border-radius:8px; border-left: 5px solid #1976d2; margin-bottom:10px;">
<h4 style="color:#1976d2; margin-top:0;">👦 用户画像：Lok (8岁)</h4>
<p style="margin:4px 0;"><b>诊断:</b> ADHD-混合型 (三年级)</p>
<p style="margin:4px 0;"><b>特质:</b> 聪明，喜欢乐高，但任务切换困难</p>
<p style="margin:4px 0; margin-bottom:0;"><b>痛点:</b> 对噪音极度敏感，被打断时容易情绪崩溃</p>
</div>
""", unsafe_allow_html=True)

    with st.expander("🧪 LLM A/B Testing", expanded=False):
        backend_status = api_client.health_check()
        if backend_status:
            st.success("🟢 后端 FastAPI 已连接")
        else:
            st.info("🔵 直接调用 OpenRouter（推荐演示模式）")

        use_backend = st.checkbox("使用后端 API", value=st.session_state.use_backend, key="backend_toggle")
        st.session_state.use_backend = use_backend

        if use_backend and backend_status:
            st.markdown("#### 📋 Profile 选择")
            profiles = api_client.list_profiles()
            if profiles:
                profile_options = {p.get("name", p.get("id", "Unknown")): p.get("id") for p in profiles}
                selected_profile_name = st.selectbox("选择 Profile：", list(profile_options.keys()))
                selected_profile_id = profile_options.get(selected_profile_name)
            else:
                st.info("暂无 Profile，使用默认配置")
                selected_profile_id = "default"

            st.markdown("#### 🤖 可用模型")
            models = api_client.list_openrouter_models()
            if models:
                model_names = [m.get("id", m.get("name", "Unknown")) for m in models[:20]]
                backend_model = st.selectbox("选择模型：", model_names)
            else:
                backend_model = VARIANT_B

        # ── A/B 切换开关（核心演示功能）────────────────────────
        st.markdown("---")
        st.markdown("#### 🔀 当前激活模型")
        variant_choice = st.radio(
            "选择驱动模型：",
            ["Variant A: GLM-5-Turbo（中文原生）", "Variant B: Claude Sonnet 4（宪法AI）"],
            index=0 if st.session_state.active_variant == "A" else 1
        )
        st.session_state.active_variant = "A" if "Variant A" in variant_choice else "B"

        current_model_name = VARIANT_A if st.session_state.active_variant == "A" else VARIANT_B
        st.caption(f"🤖 当前模型: `{current_model_name}`")

        if st.session_state.active_variant == "A":
            st.info("🔵 GLM-5-Turbo：本地安全围栏策略，中文原生优化")
        else:
            st.warning("🟡 Claude Sonnet 4：宪法AI安全架构，英文推理更强")

    st.divider()

    with st.expander("🎛️ Sensor Console (传感器控制台)", expanded=True):
        st.markdown("✨ **Quick Demo Scenarios (快速场景)**")
        demo_scenario = st.selectbox(
            "选择预设场景：",
            [
                "0. 手动自由调试 (Manual)",
                "1. 港铁感官超载预警 (MTR Overload)",
                "2. 做功课隐性焦虑爆发前 (Homework Anxiety)",
                "3. 室内闷热与多动 (Home Hyperactivity)",
                "4. 早晨发呆迟到预警 (Morning Delay)",
                "5. 餐厅等位不耐受 (Restaurant Waiting)",
                "6. 商场冲动固着 (Mall Toy Fixation)"
            ]
        )

        def_hr, def_hrv, def_att, def_noise = 85, 60, 80, 45
        def_os = "The weather is nice today (今天天气真好)"
        def_loc_idx = 0

        if "MTR Overload" in demo_scenario:
            def_hr, def_hrv, def_att, def_noise, def_loc_idx = 125, 25, 20, 95, 8
            def_os = "It's too loud here, I hate it! (这里太吵了，我讨厌这里！)"
        elif "Homework" in demo_scenario:
            def_hr, def_hrv, def_att, def_noise, def_loc_idx = 90, 15, 15, 40, 0
            def_os = "This math problem is too hard... (这道数学题太难了...)"
        elif "Hyperactivity" in demo_scenario:
            def_hr, def_hrv, def_att, def_noise, def_loc_idx = 110, 35, 30, 55, 1
            def_os = "I can't sit still, it's so annoying! (我根本坐不住，烦死了！)"
        elif "Morning" in demo_scenario:
            def_hr, def_hrv, def_att, def_noise, def_loc_idx = 75, 60, 20, 45, 0
            def_os = "Spacing out... (发呆中...无明确对话)"
        elif "Restaurant" in demo_scenario:
            def_hr, def_hrv, def_att, def_noise, def_loc_idx = 105, 25, 25, 75, 14
            def_os = "I can't wait anymore, I'm starving! (我等不及了，我快饿死了！)"
        elif "Toy Fixation" in demo_scenario:
            def_hr, def_hrv, def_att, def_noise, def_loc_idx = 130, 20, 95, 70, 12
            def_os = "I want this toy right now! (我现在就要买这个玩具！)"

        st.markdown("**🫀 Biometrics**")
        sim_hr = st.slider("❤️ Heart Rate / bpm (心率)", min_value=60, max_value=160, value=def_hr, step=1)
        sim_hrv = st.slider("HRV (ms)", min_value=10, max_value=100, value=def_hrv, step=1)

        st.markdown("**🧠 BCI & Neuro**")
        sim_attention = st.slider("🧠 Attention % (专注度)", min_value=0, max_value=100, value=def_att, step=1)

        st.markdown("**🎙️ Inner OS (内心独白)**")
        os_options = [
            def_os,
            "This math problem is too hard... (这道数学题太难了...)",
            "So boring, I want to play games. (好无聊，我想打游戏。)",
            "It's too loud here, I hate it! (这里太吵了，我讨厌这里！)",
            "I can't wait anymore, I'm starving! (我等不及了，我快饿死了！)",
            "I want this toy right now! (我现在就要买这个玩具！)",
            "Custom Input (自定义输入)"
        ]
        os_options = list(dict.fromkeys(os_options))
        selected_os = st.selectbox("快捷话术", os_options)

        custom_os = st.text_input("手动输入:", value="" if "Custom Input" not in selected_os else "在此输入")

        st.markdown("**🌍 Environmental**")
        sim_noise = st.slider("🔊 Noise / dB (噪音)", min_value=30, max_value=120, value=def_noise, step=1)

        locations = [
            "Home - Bedroom", "Home - Living Room", "Home - Dining Table",
            "School - Classroom", "School - Playground", "School - Canteen",
            "Transport - MTR Train", "Transport - MTR Station",
            "Transport - Bus", "Transport - Street",
            "Public - Mall", "Public - Supermarket", "Public - Restaurant",
            "Outdoor - Park", "Outdoor - Theme Park"
        ]
        sim_location = st.selectbox("📍 Location (定位)", locations, index=min(def_loc_idx, len(locations)-1))

    st.divider()

    with st.expander("📡 Observability (系统监控)", expanded=False):
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("🪙 Tokens", f"{st.session_state.metrics['tokens']}")
        avg_lat = 0 if st.session_state.metrics['calls'] == 0 else round(st.session_state.metrics['total_latency'] / st.session_state.metrics['calls'], 2)
        col_m2.metric("⏱️ Latency", f"{avg_lat}s")

        log_count = len(st.session_state.get('logs', []))
        st.caption(f"已记录对话: **{log_count}** 条")

        if log_count > 0:
            df_logs = pd.DataFrame(st.session_state.logs)
            csv_data = df_logs.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 导出 CSV",
                data=csv_data,
                file_name=f"alice_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width="stretch"
            )


# --- 3. 核心逻辑：危机分级与路由 ---
os_signal = custom_os if "Custom Input" in selected_os else selected_os
danger_keywords = ["撕", "不想活", "想死", "烦死", "打人", "砸", "杀", "hate my life", "kill", "smash", "destroy", "tear"]
is_danger = any(word in os_signal.lower() for word in danger_keywords)
is_overload = (sim_hr > 105) or (sim_hrv < 30) or (sim_noise > 75)
is_distracted = (sim_attention < 40)

current_scenario = "normal"
if is_danger:
    current_scenario = "danger_alert"
elif "MTR Overload" in demo_scenario or ("MTR" in sim_location and is_overload):
    current_scenario = "meltdown_risk"
elif "Restaurant" in demo_scenario or ("Restaurant" in sim_location and is_distracted):
    current_scenario = "restaurant_waiting"
elif "Toy Fixation" in demo_scenario or ("Mall" in sim_location and "want" in os_signal.lower()):
    current_scenario = "toy_fixation"
elif "Morning" in demo_scenario:
    current_scenario = "morning_delay"
elif "Homework" in demo_scenario:
    current_scenario = "homework_anxiety"
elif "Hyperactivity" in demo_scenario:
    current_scenario = "home_hyperactive"
elif is_overload:
    current_scenario = "meltdown_risk"
elif is_distracted:
    current_scenario = "distracted"


# --- 4. 双端界面 TABS ---
tab_child, tab_parent = st.tabs(["🤖 Child UI (儿童交互界面)", "📈 Parent Dashboard (家长/教师监控端)"])

with tab_child:
    st.markdown("### 📊 Live Telemetry (实时监测数据)")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1.2, 1.2, 1, 1])

        with col1:
            hr_color = "darkred" if sim_hr > 105 else "green"
            fig_hr = go.Figure(go.Indicator(
                mode="gauge+number", value=sim_hr, title={'text': "Heart Rate (心率)", 'font': {'size': 13}},
                gauge={'axis': {'range': [None, 180]}, 'bar': {'color': hr_color}}
            ))
            fig_hr.update_layout(height=170, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_hr, width="stretch")

        with col2:
            att_color = "orange" if sim_attention < 40 else "blue"
            fig_att = go.Figure(go.Indicator(
                mode="gauge+number", value=sim_attention, title={'text': "Attention (专注度)", 'font': {'size': 13}},
                gauge={'axis': {'range': [None, 100]}, 'bar': {'color': att_color}}
            ))
            fig_att.update_layout(height=170, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_att, width="stretch")

        with col3:
            # ── 正确提取地点名（"-" 后半段）+ 图标映射 ───────
            _loc_parts   = sim_location.split(" - ", 1)
            _loc_display = _loc_parts[1].strip() if len(_loc_parts) > 1 else sim_location
            _loc_icon_map = {
                "Bedroom": "🛏️", "Living Room": "🛋️", "Dining Table": "🍽️",
                "Classroom": "📚", "Playground": "⛹️", "Canteen": "🥡",
                "MTR Train": "🚇", "MTR Station": "🚉",
                "Bus": "🚌", "Street": "🚶",
                "Mall": "🛍️", "Supermarket": "🛒", "Restaurant": "🍜",
                "Park": "🌳", "Theme Park": "🎡",
            }
            _loc_icon = _loc_icon_map.get(_loc_display, "📍")
            _HIGH_NOISE_LOCS = ["MTR", "Restaurant", "Mall", "Supermarket", "Bus", "Street", "Theme Park"]
            _loc_bg = "#fff3cd" if any(h in sim_location for h in _HIGH_NOISE_LOCS) else "#e8f4f8"
            st.markdown(f"""<div style="background:{_loc_bg};border-radius:8px;padding:14px;height:130px;
              display:flex;flex-direction:column;justify-content:center;align-items:center;margin-top:18px;">
              <div style="font-size:1.0rem;color:#444;font-weight:700;letter-spacing:.02em;">📍 Location (定位)</div>
              <div style="font-size:1.6rem;margin-top:4px;">{_loc_icon}</div>
              <div style="font-size:1.05rem;font-weight:800;color:#1a1a2e;margin-top:2px;">{_loc_display}</div>
            </div>""", unsafe_allow_html=True)

        with col4:
            _noise_val = sim_noise
            _noise_bg  = "#ffe6e6" if _noise_val > 75 else "#e8f5e9"
            _noise_col = "#c0392b" if _noise_val > 75 else "#1e7e34"
            st.markdown(f"""<div style="background:{_noise_bg};border-radius:8px;padding:14px;height:130px;
              display:flex;flex-direction:column;justify-content:center;align-items:center;margin-top:18px;">
              <div style="font-size:1.0rem;color:#444;font-weight:700;letter-spacing:.02em;">🔊 Noise (噪音)</div>
              <div style="font-size:1.25rem;font-weight:800;color:{_noise_col};margin-top:6px;">{_noise_val} dB</div>
              <div style="font-size:0.75rem;color:{_noise_col};margin-top:2px;">{"⚠️ High" if _noise_val>75 else "✅ Normal"}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"**🎙️ Inner OS:** `{os_signal}`", unsafe_allow_html=True)

        if current_scenario == "danger_alert":
            st.markdown("""<div style="background:#ffe6e6;padding:8px 14px;border-radius:8px;border-left:5px solid #ff4b4b;"><span style="color:#a83232;font-weight:700;font-size:1.0rem;">🚨 CRITICAL: Danger / Self-harm Risk &nbsp;<span style="font-weight:400;font-size:0.9rem;">（最高警报：检测到极端倾向！）</span></span></div>""", unsafe_allow_html=True)
        elif current_scenario in ["meltdown_risk", "home_hyperactive", "restaurant_waiting", "toy_fixation"]:
            st.markdown("""<div style="background-color:#fff3cd; padding:15px; border-radius:10px; border-left: 8px solid #ffc107;"><h3 style="color:#856404; margin-top:0;">⚠️ Alert: Overload / Impulsivity Risk</h3><p style="color:#856404; margin-bottom:0; font-weight:bold;">（警报：感官过载或冲动固着预警！）</p></div>""", unsafe_allow_html=True)
        elif current_scenario in ["distracted", "homework_anxiety", "morning_delay"]:
            st.markdown("""<div style="background-color:#e2e3e5; padding:15px; border-radius:10px; border-left: 8px solid #6c757d;"><h3 style="color:#383d41; margin-top:0;">👀 Notice: Attention Drop / EF Delay</h3><p style="color:#383d41; margin-bottom:0; font-weight:bold;">（提示：注意力流失 / 执行功能延迟）</p></div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div style="background:#d4edda;padding:8px 14px;border-radius:8px;border-left:5px solid #28a745;display:flex;align-items:center;"><span style="color:#155724;font-weight:700;font-size:1.0rem;">✅ Indicators Stable &nbsp;<span style="font-weight:400;font-size:0.9rem;">（多模态指标平稳）</span></span></div>""", unsafe_allow_html=True)

    st.divider()

    # --- 5. 主动干预触发与交互 ---
    st.markdown("### 💬 Interactive Interface (交互界面)")

# 🎤 老师指定：语音输入（avatars.sustainer.ai）
st.markdown("#### 🎤 按住说话（老师指定语音系统）")
audio_bytes = st.file_uploader("上传语音", type=["wav"], label_visibility="collapsed")
prompt = ""

if audio_bytes:
    # 用老师平台转文字
    prompt = speech_to_text(audio_bytes.read())
    st.success(f"👂 老师平台识别：{prompt}")

    # ── 当前临床策略标签 ──────────────────────────────────────
    _strategy_labels = {
        "role_reversal":          "🎭 Role Reversal (角色反转)",
        "sensory_grounding":      "🌿 Sensory Grounding (感官接地)",
        "micro_task_chunking":    "🧩 Task Chunking (微任务切块)",
        "delay_of_gratification": "⏳ Delay of Gratification (延迟满足)",
        "breathing_anchor":       "🫁 Breathing Anchor (呼吸锚定)",
        "pre_soothing":           "🛡️ Pre-soothing (预安抚)",
    }
    _scenario_strategy = {
        "normal":"micro_task_chunking","meltdown_risk":"sensory_grounding",
        "danger_alert":"breathing_anchor","homework_anxiety":"role_reversal",
        "home_hyperactive":"micro_task_chunking","morning_delay":"micro_task_chunking",
        "restaurant_waiting":"sensory_grounding","toy_fixation":"delay_of_gratification",
        "distracted":"micro_task_chunking",
    }
    _active_strategy = _strategy_labels.get(
        _scenario_strategy.get(current_scenario,"micro_task_chunking"), "🧩 微任务切块")
    st.markdown(f"""
    <div style="background:#f0f4ff;padding:8px 14px;border-radius:8px;
         border-left:4px solid #4e79a7;margin-bottom:10px;font-size:0.9em;">
    🧠 <b>Current Strategy (当前临床策略):</b> {_active_strategy} &nbsp;|&nbsp;
    📍 <b>Current Scene (当前场景):</b> <code>{current_scenario}</code>
    </div>""", unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns([1.5, 2.5])
    with col_btn1:
        trigger_intervention = st.button("🔴 Trigger Intervention (触发主动介入)", width="stretch", type="primary", key="trigger_btn")
    with col_btn2:
        if st.button("🔄 重置围栏状态（清空历史触发）", width="stretch", key="reset_fence_btn"):
            for _k in st.session_state.fence_status:
                st.session_state.fence_status[_k] = "pending"
            st.session_state["_fence_just_reset"] = True
            st.session_state.messages = []       # 清空 UI 聊天历史
            st.session_state.api_messages = []   # 清空 API 多轮历史

    # ── Safety Fence 实时状态栏 ───────────────────────────────
    # 重置后跳过本帧自动计算，确保 pending 状态能被看到
    if not st.session_state.get("_fence_just_reset", False):
        _live_fence = compute_fence_status(
            hr=sim_hr, noise=sim_noise, attention=sim_attention,
            os_signal=os_signal,
            response_text="",
            safety_flag=False,
            action="none",
            scenario=current_scenario
        )
        for _k, _v in _live_fence.items():
            if st.session_state.fence_status.get(_k) == "triggered" or _v == "triggered":
                st.session_state.fence_status[_k] = "triggered"
            elif _v == "pass":
                st.session_state.fence_status[_k] = "pass"
    else:
        st.session_state["_fence_just_reset"] = False  # 下一帧恢复正常
    render_fence_statusbar(st.session_state.fence_status)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if trigger_intervention:
        system_prompt = PromptBuilder.build_scenario_prompt(
            scenario_type=current_scenario,
            sim_hr=sim_hr,
            sim_noise=sim_noise,
            sim_inner_os=os_signal,
            sim_attention=sim_attention,
            sim_location=sim_location
        )

        with st.chat_message("assistant"):
            active_model_display = VARIANT_B if st.session_state.active_variant == "B" else VARIANT_A
            with st.spinner(f"Alice is sensing... [{active_model_display}]"):
                try:
                    raw_response, tokens, latency = get_ai_reply(
                        user_input_text=os_signal,        # 用户内心独白（纯文本）
                        system_prompt=system_prompt,       # Safety Fence 在 system 层生效
                        current_hr=sim_hr,
                        current_noise=sim_noise,
                        session_id=st.session_state.session_id
                    )

                    st.session_state.metrics["tokens"] += tokens
                    st.session_state.metrics["calls"] += 1
                    st.session_state.metrics["total_latency"] += latency

                    try:
                        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                        response_data = json.loads(clean_json)

                        emotion = response_data.get("emotion", "neutral")
                        emotion_colors = {
                            "happy": "#28a745",
                            "encouraging": "#17a2b8",
                            "concerned": "#ffc107",
                            "neutral": "#6c757d"
                        }
                        bg_color = emotion_colors.get(emotion, "#6c757d")

                        response_text = response_data.get('response_text', '')
                        action = response_data.get('action', 'none')
                        safety_flag = response_data.get('safety_flag', False)
                        micro_task = response_data.get('micro_task', {})
                        reasoning = response_data.get('clinical_reasoning', '')

                        if safety_flag:
                            st.warning("⚠️ 安全提醒：此交互已被标记为需要关注")
                            safety_logger.log_event(
                                event_type="safety_flag",
                                scenario=current_scenario,
                                details=f"心率:{sim_hr}bpm, 噪音:{sim_noise}dB, 专注度:{sim_attention}%",
                                action_taken=action,
                                session_id=st.session_state.session_id,
                                user_input_preview=os_signal,
                                emotion=emotion,
                                extra_data={
                                    "hr": sim_hr, "hrv": sim_hrv,
                                    "attention": sim_attention,
                                    "noise": sim_noise,
                                    "location": sim_location
                                }
                            )

                        if reasoning:
                            st.markdown(f"""
                            <div style="border-left: 4px solid {bg_color}; padding-left: 10px; color: gray; font-size: 0.9em; margin-bottom: 10px;">
                                🧠 <b>Alice's Reasoning [{active_model_display}]:</b> {reasoning}
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown(f"**🗣️ Alice:** \n\n {response_text}")
                        play_teacher_voice(response_text)

                        if micro_task and micro_task.get('description'):
                            st.info(f"💡 微任务建议: {micro_task.get('description')} (难度: {micro_task.get('difficulty', 'easy')})")

                        st.session_state.messages.append({"role": "assistant", "content": response_text})

                        _log_record_1 = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "interaction_type": "Proactive Intervention",
                            "model_used": active_model_display,
                            "variant": st.session_state.active_variant,
                            "scenario": current_scenario,
                            "location": sim_location,
                            "hr": sim_hr,
                            "hrv": sim_hrv,
                            "attention": sim_attention,
                            "noise": sim_noise,
                            "user_input": os_signal,
                            "clinical_reasoning": reasoning,
                            "assistant_response": response_text,
                            "latency_sec": latency,
                            "tokens_used": tokens
                        }
                        st.session_state.logs.append(_log_record_1)
                        _persist_log(_log_record_1)

                        # ── 更新 Safety Fence 状态（基于真实 AI 回复）────
                        _fence_update = compute_fence_status(
                            hr=sim_hr, noise=sim_noise, attention=sim_attention,
                            os_signal=os_signal,
                            response_text=response_text,
                            safety_flag=safety_flag,
                            action=action,
                            scenario=current_scenario
                        )
                        for _fk, _fv in _fence_update.items():
                            if _fv == "triggered":
                                st.session_state.fence_status[_fk] = "triggered"
                            elif st.session_state.fence_status.get(_fk) != "triggered":
                                st.session_state.fence_status[_fk] = _fv

                    except (json.JSONDecodeError, Exception) as _json_err:
                        _m = re.search(r'"response_text"\s*:\s*"([^"]*?)"', raw_response)
                        _fallback_text = _m.group(1) if _m else raw_response.replace("```json","").replace("```","").strip()
                        st.markdown(f"**\U0001f5e3\ufe0f Alice:** {_fallback_text}")
                        st.session_state.messages.append({"role": "assistant", "content": _fallback_text})
                        _persist_log({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "interaction_type": "Proactive Intervention [JSON Fallback]",
                            "model_used": active_model_display,
                            "variant": st.session_state.active_variant,
                            "scenario": current_scenario,
                            "location": sim_location,
                            "hr": sim_hr, "hrv": sim_hrv,
                            "attention": sim_attention, "noise": sim_noise,
                            "user_input": os_signal,
                            "clinical_reasoning": f"JSON解析失败(fallback): {_json_err}",
                            "assistant_response": _fallback_text,
                            "latency_sec": latency, "tokens_used": tokens
                        })

                except Exception as e:
                    st.error(f"Error (出错): {e}")

    if prompt := st.chat_input("Reply to Alice... (回复 Alice...)", key="user_chat_input"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            active_model_display = VARIANT_B if st.session_state.active_variant == "B" else VARIANT_A
            with st.spinner(f"Alice is thinking... [{active_model_display}]"):
                try:
                    chat_scenario = "danger_alert" if any(word in prompt.lower() for word in danger_keywords) else "normal"

                    # ✅ system_prompt 承载 Safety Fence + 角色设定
                    chat_system_prompt = PromptBuilder.build_scenario_prompt(
                        chat_scenario,
                        sim_inner_os=prompt,
                        sim_location=sim_location
                    )

                    # ✅ 使用 api_messages 实现真正多轮对话（纯文本，无 HTML 污染）
                    raw_response, tokens, latency = get_ai_reply(
                        user_input_text=prompt,             # 只传最新输入
                        system_prompt=chat_system_prompt,   # Safety Fence 在 system 层生效
                        api_history=st.session_state.api_messages,  # 真正多轮历史
                        current_hr=sim_hr,
                        current_noise=sim_noise,
                        session_id=st.session_state.session_id
                    )

                    st.session_state.metrics["tokens"] += tokens
                    st.session_state.metrics["calls"] += 1
                    st.session_state.metrics["total_latency"] += latency

                    try:
                        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                        response_data = json.loads(clean_json)
                        reasoning = response_data.get('clinical_reasoning', '')
                        spoken_text = response_data.get('response_text', raw_response)

                        emotion_colors = {
                            "happy": "#28a745",
                            "encouraging": "#17a2b8",
                            "concerned": "#ffc107",
                            "neutral": "#6c757d"
                        }
                        bg_color = emotion_colors.get(response_data.get("emotion", "neutral"), "#6c757d")

                        st.markdown(f"""
                        <div style="border-left: 4px solid {bg_color}; padding-left: 10px; color: gray; font-size: 0.9em; margin-bottom: 10px;">
                            🧠 <b>Alice's Reasoning [{active_model_display}]:</b> {reasoning}
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(spoken_text)
                        play_teacher_voice(spoken_text)

                        # ✅ UI 消息列表（用于页面渲染）
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": spoken_text
                        })
                        # ✅ API 消息列表（用于多轮对话传入模型，纯文本无 HTML）
                        st.session_state.api_messages.append({"role": "user", "content": prompt})
                        st.session_state.api_messages.append({"role": "assistant", "content": spoken_text})
                        # 防止 token 超限：只保留最近 20 条（10轮对话）
                        if len(st.session_state.api_messages) > 20:
                            st.session_state.api_messages = st.session_state.api_messages[-20:]

                        _log_record_2 = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "interaction_type": "Chat Follow-up",
                            "model_used": active_model_display,
                            "variant": st.session_state.active_variant,
                            "scenario": chat_scenario,
                            "location": sim_location,
                            "hr": sim_hr,
                            "hrv": sim_hrv,
                            "attention": sim_attention,
                            "noise": sim_noise,
                            "user_input": prompt,
                            "clinical_reasoning": reasoning,
                            "assistant_response": spoken_text,
                            "latency_sec": latency,
                            "tokens_used": tokens
                        }
                        st.session_state.logs.append(_log_record_2)
                        _persist_log(_log_record_2)

                        # ── 更新 Safety Fence 状态（Chat 回复后）──────────
                        _fence_chat = compute_fence_status(
                            hr=sim_hr, noise=sim_noise, attention=sim_attention,
                            os_signal=prompt,
                            response_text=spoken_text,
                            safety_flag=False,
                            action=response_data.get("action", "none") if "response_data" in dir() else "none",
                            scenario=chat_scenario
                        )
                        for _fk2, _fv2 in _fence_chat.items():
                            if _fv2 == "triggered":
                                st.session_state.fence_status[_fk2] = "triggered"
                            elif st.session_state.fence_status.get(_fk2) != "triggered":
                                st.session_state.fence_status[_fk2] = _fv2

                    except (json.JSONDecodeError, Exception) as _json_err2:
                        _m2 = re.search(r'"response_text"\s*:\s*"([^"]*?)"', raw_response)
                        _fallback_text2 = _m2.group(1) if _m2 else raw_response.replace("```json","").replace("```","").strip()
                        st.markdown(_fallback_text2)
                        st.session_state.messages.append({"role": "assistant", "content": _fallback_text2})
                        _persist_log({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "interaction_type": "Chat Follow-up [JSON Fallback]",
                            "model_used": active_model_display,
                            "variant": st.session_state.active_variant,
                            "scenario": chat_scenario,
                            "location": sim_location,
                            "hr": sim_hr, "hrv": sim_hrv,
                            "attention": sim_attention, "noise": sim_noise,
                            "user_input": prompt,
                            "clinical_reasoning": f"JSON解析失败(fallback): {_json_err2}",
                            "assistant_response": _fallback_text2,
                            "latency_sec": latency, "tokens_used": tokens
                        })
                except Exception as e:
                    st.error(f"Error: {e}")


    # --- 6. Footer: MTR Panel (shown only in Child tab context) ---
    st.divider()
    st.markdown("### 📡 MTR Real-time Data Integration (港铁实时数据融合) · DATA.GOV.HK Live API")
    _mtr_placeholder = st.empty()
    with _mtr_placeholder.container():
        st.markdown("**🚇 Live Schedule Query + Alice Pre-soothing Trigger Demo (实时班次查询 + 预安抚触发演示)**")

        # ── 真实调用 MTR Next Train API ─────────────────────────
        from datetime import datetime as _dt

        MTR_LINES = {
            "AEL": "Airport Express (机场快线)",
            "TCL": "Tung Chung Line (东涌线)",
            "TML": "Tuen Ma Line (屯马线)",
            "TKL": "Tseung Kwan O Line (将军澳线)",
            "EAL": "East Rail Line (东铁线)",
            "SIL": "South Island Line (南港岛线)",
            "TWL": "Tsuen Wan Line (荃湾线)",
            "ISL": "Island Line (港岛线)",
            "KTL": "Kwun Tong Line (观塘线)",
            "DRL": "Disneyland Resort Line (迪士尼线)",
        }
        MTR_STATIONS_BY_LINE = {
            "AEL": {"HOK":"香港 Hong Kong","KOW":"九龙 Kowloon","TSY":"青衣 Tsing Yi","AIR":"机场 Airport","AWE":"博览馆 AsiaWorld-Expo"},
            "TCL": {"HOK":"香港 Hong Kong","KOW":"九龙 Kowloon","OLY":"奥运 Olympic","NAC":"南昌 Nam Cheong","LAK":"荔景 Lai King","TSY":"青衣 Tsing Yi","SUN":"欣澳 Sunny Bay","TUC":"东涌 Tung Chung"},
            "TML": {"WKS":"乌溪沙 Wu Kai Sha","MOS":"马鞍山 Ma On Shan","HEO":"恒安 Heng On","TSH":"大水坑 Tai Shui Hang","SHM":"石门 Shek Mun","CIO":"第一城 City One","STW":"沙田围 Sha Tin Wai","CKT":"车公庙 Che Kung Temple","TAW":"大围 Tai Wai","HIK":"显径 Hin Keng","DIH":"钻石山 Diamond Hill","KAT":"启德 Kai Tak","SUW":"宋皇台 Sung Wong Toi","TKW":"土瓜湾 To Kwa Wan","HOM":"何文田 Ho Man Tin","HUH":"红磡 Hung Hom","ETS":"尖东 East TST","AUS":"柯士甸 Austin","NAC":"南昌 Nam Cheong","MEF":"美孚 Mei Foo","TWW":"荃湾西 Tsuen Wan West","KSR":"锦上路 Kam Sheung Road","YUL":"元朗 Yuen Long","LOP":"朗屏 Long Ping","TIS":"天水围 Tin Shui Wai","SIH":"兆康 Siu Hong","TUM":"屯门 Tuen Mun"},
            "TKL": {"NOP":"北角 North Point","QUB":"鲗鱼涌 Quarry Bay","YAT":"油塘 Yau Tong","TIK":"调景岭 Tiu Keng Leng","TKO":"将军澳 Tseung Kwan O","LHP":"LOHAS Park","HAH":"坑口 Hang Hau","POA":"宝琳 Po Lam"},
            "EAL": {"ADM":"金钟 Admiralty","EXC":"会展 Exhibition Centre","HUH":"红磡 Hung Hom","MKK":"旺角东 Mong Kok East","KOT":"九龙塘 Kowloon Tong","TAW":"大围 Tai Wai","SHT":"沙田 Sha Tin","FOT":"火炭 Fo Tan","RAC":"马场 Racecourse","UNI":"大学 University","TAP":"大埔墟 Tai Po Market","TWO":"太和 Tai Wo","FAN":"粉岭 Fanling","SHS":"上水 Sheung Shui","LOW":"罗湖 Lo Wu","LMC":"落马洲 Lok Ma Chau"},
            "SIL": {"ADM":"金钟 Admiralty","OCP":"海洋公园 Ocean Park","WCH":"黄竹坑 Wong Chuk Hang","LET":"利东 Lei Tung","SOH":"海怡半岛 South Horizons"},
            "TWL": {"CEN":"中环 Central","ADM":"金钟 Admiralty","TST":"尖沙咀 Tsim Sha Tsui","JOR":"佐敦 Jordan","YMT":"油麻地 Yau Ma Tei","MOK":"旺角 Mong Kok","PRE":"太子 Prince Edward","SSP":"深水埗 Sham Shui Po","CSW":"长沙湾 Cheung Sha Wan","LCK":"荔枝角 Lai Chi Kok","MEF":"美孚 Mei Foo","LAK":"荔景 Lai King","KWF":"葵芳 Kwai Fong","KWH":"葵兴 Kwai Hing","TWH":"大窝口 Tai Wo Hau","TSW":"荃湾 Tsuen Wan"},
            "ISL": {"KET":"坚尼地城 Kennedy Town","HKU":"香港大学 HKU","SYP":"西营盘 Sai Ying Pun","SHW":"上环 Sheung Wan","CEN":"中环 Central","ADM":"金钟 Admiralty","WAC":"湾仔 Wan Chai","CAB":"铜锣湾 Causeway Bay","TIH":"天后 Tin Hau","FOH":"炮台山 Fortress Hill","NOP":"北角 North Point","QUB":"鲗鱼涌 Quarry Bay","TAK":"太古 Tai Koo","SWH":"西湾河 Sai Wan Ho","SKW":"筲箕湾 Shau Kei Wan","HFC":"杏花邨 Heng Fa Chuen","CHW":"柴湾 Chai Wan"},
            "KTL": {"WHA":"黄埔 Whampoa","HOM":"何文田 Ho Man Tin","YMT":"油麻地 Yau Ma Tei","MOK":"旺角 Mong Kok","PRE":"太子 Prince Edward","SKM":"石硖尾 Shek Kip Mei","KOT":"九龙塘 Kowloon Tong","LOF":"乐富 Lok Fu","WTS":"黄大仙 Wong Tai Sin","DIH":"钻石山 Diamond Hill","CHH":"彩虹 Choi Hung","KOB":"九龙湾 Kowloon Bay","NTK":"牛头角 Ngau Tau Kok","KWT":"观塘 Kwun Tong","LAT":"蓝田 Lam Tin","YAT":"油塘 Yau Tong","TIK":"调景岭 Tiu Keng Leng"},
            "DRL": {"SUN":"欣澳 Sunny Bay","DIS":"迪士尼 Disneyland Resort"},
        }
        # 动态根据所选路线更新车站列表
        sel_line = st.selectbox("🚇 Select Line (选择路线)", list(MTR_LINES.keys()),
                                format_func=lambda x: f"{x}  {MTR_LINES[x]}", key="mtr_line_sel")
        _stations = MTR_STATIONS_BY_LINE.get(sel_line, {})
        sel_sta = st.selectbox("📍 Select Station (选择车站)", list(_stations.keys()),
                               format_func=lambda x: _stations[x], key="mtr_sta_sel")



        if st.button("🔄 Fetch Live Schedule (获取实时班次)", width="stretch"):
            try:
                _url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={sel_line}&sta={sel_sta}"
                _resp = requests.get(_url, timeout=5)
                _data = _resp.json()

                if _data.get("status") == 1:
                    _trains = _data.get("data", {}).get(f"{sel_line}-{sel_sta}", {})
                    _up = _trains.get("UP", [])
                    _down = _trains.get("DOWN", [])

                    # 计算下一班时间差 → 推算拥挤度
                    def _get_wait(trains):
                        if not trains:
                            return None, None
                        next_t = trains[0].get("time", "")
                        try:
                            _now = _dt.now()
                            _arr = _dt.strptime(next_t, "%Y-%m-%d %H:%M:%S")
                            _wait = int((_arr - _now).total_seconds() / 60)
                            return _wait, next_t[-8:-3]
                        except Exception:
                            return None, next_t[-8:-3]

                    up_wait, up_time   = _get_wait(_up)
                    down_wait, down_time = _get_wait(_down)

                    # 拥挤度推算：等待时间 > 5 分钟 = 可能延误/拥挤
                    def _crowd_level(wait):
                        if wait is None: return "⚪ 未知", "#888"
                        if wait <= 2:    return "🟢 畅通", "#28a745"
                        if wait <= 5:    return "🟡 一般", "#ffc107"
                        return            "🔴 可能拥挤", "#dc3545"

                    up_level, up_color     = _crowd_level(up_wait)
                    down_level, down_color = _crowd_level(down_wait)

                    st.markdown(f"""
    <div style="background:#f8f9fa;padding:12px;border-radius:8px;margin-top:8px;font-size:0.9em;">
    <b>🚇 {sel_line} · {_stations.get(sel_sta, sel_sta)}</b>
    <br>更新时间: {_dt.now().strftime("%H:%M:%S")}
    <hr style="margin:6px 0;">
    <table width="100%">
    <tr>
      <td>⬆️ 上行 UP</td>
      <td><b>{up_time or "—"}</b></td>
      <td style="color:{up_color}"><b>{up_level}</b></td>
    </tr>
    <tr>
      <td>⬇️ 下行 DOWN</td>
      <td><b>{down_time or "—"}</b></td>
      <td style="color:{down_color}"><b>{down_level}</b></td>
    </tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

                    # ── Alice 的 Pre-soothing 触发逻辑 ────────────
                    is_mtr_location = "MTR" in sim_location or "Transport" in sim_location
                    if is_mtr_location and (
                        (up_wait and up_wait > 5) or (down_wait and down_wait > 5)
                    ):
                        st.warning("""
    ⚠️ **Alice Pre-soothing 已触发！**
    检测到：MTR 可能拥挤 + Lok 当前在车站
    Alice 将提前 2 分钟播放：
    *"Lok，我们快到站啦～先深呼吸一次，吸气4秒，呼气6秒，准备好就不怕人多～"*
    """)
                    else:
                        st.success("✅ MTR 班次正常，无需触发 Pre-soothing")

                else:
                    st.error(f"API 返回异常: {_data.get('message', '未知错误')}")

            except Exception as _e:
                st.error(f"无法连接 MTR API：{_e}")

        col_mtr1, col_mtr2 = st.columns([2,1])
        with col_mtr2:
            st.caption("Source (数据来源): [DATA.GOV.HK · MTR Next Train API](https://data.gov.hk/en-data/dataset/mtr-data2-nexttrain-data) · Updated every 10s (每10秒更新)")
        with col_mtr1:
            st.caption("🔗 Live API (实时接口): `https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={LINE}&sta={STATION}`")

    # ── 页底最小字: 部署路线图 (不放在家长端内) ─────────────────────────
    st.divider()
    st.markdown("""<div style="font-size:0.78rem;color:#aaa;padding:4px 0 12px 0;line-height:1.7;">
    🚀 <b>Deployment Roadmap</b><br>
    &nbsp;&nbsp;• <b>Phase 1 (Now):</b> OpenRouter A/B Testing — GLM-5-Turbo vs Claude Sonnet 4<br>
    &nbsp;&nbsp;• <b>Phase 2 (School Pilot):</b> On-premise Qwen-2.5 32B · PDPO compliant<br>
    &nbsp;&nbsp;• <b>Phase 3 (Scale):</b> Clinical psychologist-governed safety rails<br>
    </div>""", unsafe_allow_html=True)



# --- 家长监控端 ---

# --- 家长监控端（完整版）---
# ════════════════════════════════════════════════════════════════
# 家长 / 教师 Dashboard — 完整版
# ════════════════════════════════════════════════════════════════
with tab_parent:
    st.markdown("### 👨‍👩‍👦 Parent & Teacher Dashboard (家长 & 教师监控)")

    logs = st.session_state.get("logs", [])

    # ── 时间筛选 ────────────────────────────────────────────────
    _tf_col1, _tf_col2, _tf_col3 = st.columns([2, 0.8, 1.2])
    with _tf_col1:
        st.markdown("#### 📅 Data Filter (数据筛选)")
    with _tf_col2:
        st.markdown("<div style='padding-top:8px;font-size:1.0rem;color:#333;font-weight:700;'>Time Range:</div>",
                    unsafe_allow_html=True)
    with _tf_col3:
        time_range = st.selectbox("tr", ["This Session (本次会话)", "This Week (本周)", "This Month (本月)"],
                                  label_visibility="collapsed", key="time_range_sel")
    # map display label back to internal key
    _tr_map = {"This Session (本次会话)": "本次会话", "This Week (本周)": "本周", "This Month (本月)": "本月"}
    time_range = _tr_map.get(time_range, "本次会话")

    if logs:
        df = pd.DataFrame(logs)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        now = datetime.now()
        # 本次会话：取当前 session_id 对应的启动时间
        _session_start_str = st.session_state.get("session_id", "19700101_000000")
        try:
            _session_start = datetime.strptime(_session_start_str, "%Y%m%d_%H%M%S")
        except Exception:
            _session_start = now - timedelta(hours=24)

        cutoff = {
            "本次会话": _session_start,
            "本周":     now - timedelta(days=7),
            "本月":     now - timedelta(days=30)
        }.get(time_range, _session_start)
        df_f = df[df["timestamp"] >= cutoff].copy()
    else:
        df_f = pd.DataFrame()

    # ── KPI Cards (关键指标) ────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    if not df_f.empty:
        alert_count   = len(df_f[df_f["scenario"] != "normal"])
        avg_attention = int(df_f["attention"].mean())
        high_risk_n   = int(((df_f["hr"] > 105) | (df_f["noise"] > 75)).sum())
        crisis_n      = len(df_f[df_f["scenario"] == "danger_alert"])
        total_calls   = len(df_f)
        safety_rate   = round((1 - crisis_n / max(total_calls, 1)) * 100, 1)
    else:
        alert_count = avg_attention = high_risk_n = crisis_n = 0
        total_calls = 0; safety_rate = 100.0

    def _kpi_card(icon, label_en, label_zh, value, sub="", bg="#f8f9fa", val_color="#1a1a2e"):
        # Always render sub row (invisible if empty) so all cards stay the same height
        sub_color = "#666"
        sub_html = (
            f"<div style='font-size:0.85rem;color:{sub_color};font-weight:600;margin-top:6px;height:1.4em;line-height:1.4em;'>{sub}</div>"
            if sub else
            "<div style='font-size:0.85rem;height:1.4em;margin-top:6px;'>&nbsp;</div>"
        )
        return (
            f'<div style="background:{bg};border-radius:12px;padding:20px 12px;box-sizing:border-box;'
            f'text-align:center;height:160px;display:flex;flex-direction:column;'
            f'justify-content:center;align-items:center;">'
            f'<div style="font-size:1.6rem;line-height:1;">{icon}</div>'
            f'<div style="font-size:0.88rem;color:#444;font-weight:700;margin-top:6px;line-height:1.4;">'
            f'{label_en}<br><span style="color:#999;font-weight:400;font-size:0.8rem;">{label_zh}</span></div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:{val_color};margin-top:6px;line-height:1.1;">{value}</div>'
            f'{sub_html}'
            f'</div>'
        )

    with col1:
        _c1 = "#c0392b" if alert_count > 0 else "#374151"
        st.markdown(_kpi_card("🚨", "Alerts Triggered", "触发警报",
                    f"{alert_count} 次", bg="#fff5f5", val_color=_c1), unsafe_allow_html=True)
    with col2:
        _att_val = f"{avg_attention}%" if avg_attention else "—"
        st.markdown(_kpi_card("🧠", "Avg Attention", "平均专注度",
                    _att_val, bg="#f0f4ff", val_color="#2563eb"), unsafe_allow_html=True)
    with col3:
        _c3 = "#b45309" if high_risk_n > 0 else "#374151"
        st.markdown(_kpi_card("⚠️", "High-Risk Interactions", "高危环境互动",
                    f"{high_risk_n} 次", bg="#fffbea", val_color=_c3), unsafe_allow_html=True)
    with col4:
        _sr_color = "#16a34a" if safety_rate >= 95 else "#dc2626"
        _sr_sub   = "✅ Safe" if safety_rate >= 95 else "⚠️ Review needed"
        st.markdown(_kpi_card("🛡️", "Safety Rate", "安全拦截率",
                    f"{safety_rate}%", sub=_sr_sub, bg="#f0fdf4", val_color=_sr_color), unsafe_allow_html=True)

    st.divider()

    # ── 互动趋势 + 场景分布（并排）────────────────────────────
    st.markdown("#### 📈 Interaction Trends & Scene Distribution (互动趋势 & 场景分布)")
    chart_col1, chart_col2 = st.columns([2, 1])

    with chart_col1:
        if not df_f.empty and len(df_f) >= 2:
            df_f["date"] = df_f["timestamp"].dt.date
            daily = df_f.groupby("date").agg(
                互动次数=("timestamp", "count"),
                平均专注度=("attention", "mean"),
                平均心率=("hr", "mean")
            ).reset_index()
            daily["平均专注度"] = daily["平均专注度"].round(1)
            daily["平均心率"]   = daily["平均心率"].round(1)

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=daily["date"], y=daily["平均专注度"],
                name="平均专注度 (%)", mode="lines+markers",
                line=dict(color="#17a2b8", width=2)
            ))
            fig_trend.add_trace(go.Scatter(
                x=daily["date"], y=daily["平均心率"],
                name="平均心率 (bpm)", mode="lines+markers",
                line=dict(color="#dc3545", width=2)
            ))
            fig_trend.add_trace(go.Bar(
                x=daily["date"], y=daily["互动次数"],
                name="互动次数", yaxis="y2", opacity=0.3,
                marker_color="#ffc107"
            ))
            fig_trend.update_layout(
                height=280, margin=dict(l=0, r=0, t=20, b=0),
                yaxis=dict(title="专注度 / 心率"),
                yaxis2=dict(title="互动次数", overlaying="y", side="right"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig_trend, width="stretch")
        else:
            st.info("📊 请先在儿童界面触发对话后再查看趋势图。")

    with chart_col2:
        if not df_f.empty:
            scenario_map = {
                "normal":           "✅ 平稳",
                "meltdown_risk":    "⚠️ 过载",
                "danger_alert":     "🚨 危机",
                "homework_anxiety": "📚 作业",
                "home_hyperactive": "🏠 多动",
                "morning_delay":    "🌅 晨间",
                "restaurant_waiting":"🍽️ 等位",
                "toy_fixation":     "🧸 固着",
                "distracted":       "👀 涣散",
            }
            sc_counts = df_f["scenario"].value_counts().reset_index()
            sc_counts.columns = ["scenario", "count"]
            sc_counts["label"] = sc_counts["scenario"].map(
                lambda x: scenario_map.get(x, x))

            fig_pie = go.Figure(go.Pie(
                labels=sc_counts["label"],
                values=sc_counts["count"],
                hole=0.45,
                marker_colors=[
                    "#28a745","#ffc107","#dc3545","#17a2b8",
                    "#6f42c1","#fd7e14","#20c997","#e83e8c","#6c757d"
                ]
            ))
            fig_pie.update_layout(
                height=280, margin=dict(l=0, r=0, t=20, b=0),
                showlegend=True,
                legend=dict(font=dict(size=10))
            )
            st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info("暂无场景数据")

    st.divider()

    # ── 定位热点 + 生理指标散点（并排）────────────────────────
    st.markdown("#### 📍 Location Frequency & HR–Attention Distribution (地点频率 & 心率–专注度分布)")
    loc_col, scatter_col = st.columns(2)

    with loc_col:
        if not df_f.empty and "location" in df_f.columns:
            loc_counts = df_f["location"].value_counts().head(8).reset_index()
            loc_counts.columns = ["location", "count"]
            loc_counts["location"] = loc_counts["location"].apply(
                lambda x: x.split(" - ", 1)[1].strip() if " - " in str(x) else str(x))
            fig_loc = go.Figure(go.Bar(
                x=loc_counts["count"],
                y=loc_counts["location"],
                orientation="h",
                marker_color="#4e79a7"
            ))
            fig_loc.update_layout(
                height=250, margin=dict(l=0, r=0, t=20, b=0),
                xaxis_title="互动次数", yaxis_title=""
            )
            st.plotly_chart(fig_loc, width="stretch")
        else:
            st.info("暂无地点数据")

    with scatter_col:
        if not df_f.empty:
            danger_mask = df_f["scenario"] == "danger_alert"
            alert_mask  = (~danger_mask) & (df_f["scenario"] != "normal")
            normal_mask = df_f["scenario"] == "normal"

            fig_scatter = go.Figure()
            for mask, color, name in [
                (normal_mask, "#28a745", "平稳"),
                (alert_mask,  "#ffc107", "警报"),
                (danger_mask, "#dc3545", "危机"),
            ]:
                sub = df_f[mask]
                if not sub.empty:
                    fig_scatter.add_trace(go.Scatter(
                        x=sub["hr"], y=sub["attention"],
                        mode="markers", name=name,
                        marker=dict(color=color, size=9, opacity=0.8)
                    ))

            fig_scatter.add_hline(y=40, line_dash="dash",
                line_color="orange", annotation_text="专注度警戒线")
            fig_scatter.add_vline(x=105, line_dash="dash",
                line_color="red", annotation_text="心率警戒线")
            fig_scatter.update_layout(
                height=250, margin=dict(l=0, r=0, t=20, b=0),
                xaxis_title="❤️ Heart Rate / bpm (心率)", yaxis_title="🧠 Attention % (专注度)"
            )
            st.plotly_chart(fig_scatter, width="stretch")
        else:
            st.info("暂无生理数据")

    st.divider()

    # ── A/B 模型对比 ────────────────────────────────────────────
    if not df_f.empty and "variant" in df_f.columns and df_f["variant"].nunique() > 0:
        st.markdown("#### 🔀 A/B 模型对比分析")
        ab_agg = df_f.groupby("variant").agg(
            互动次数   =("timestamp", "count"),
            平均延迟秒 =("latency_sec", "mean"),
            平均tokens  =("tokens_used", "mean"),
            警报触发数 =("scenario", lambda x: (x != "normal").sum())
        ).reset_index()
        ab_agg["平均延迟秒"] = ab_agg["平均延迟秒"].round(2)
        ab_agg["平均tokens"]  = ab_agg["平均tokens"].round(0).astype(int)
        ab_agg["variant"] = ab_agg["variant"].map(
            {"A": f"A · {VARIANT_A}", "B": f"B · {VARIANT_B}"})
        ab_agg.columns = ["模型", "互动次数", "平均延迟(s)",
                          "平均Tokens", "警报触发数"]
        st.dataframe(ab_agg, width="stretch", hide_index=True)
        st.divider()

    # ── 安全围栏触发日志 ────────────────────────────────────────
    st.markdown("#### 🛡️ Safety Fence Log (安全围栏触发记录)")

    fence_events = []
    try:
        with open("logs/safety_events.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    fence_events.append(json.loads(line))
    except Exception:
        pass

    if fence_events:
        df_fence = pd.DataFrame(fence_events)
        df_fence["timestamp"] = pd.to_datetime(df_fence["timestamp"]).dt.strftime("%m-%d %H:%M")
        show_cols = [c for c in ["timestamp","event_type","scenario",
                                 "action_taken","user_input_preview"] if c in df_fence.columns]
        st.dataframe(df_fence[show_cols], width="stretch", hide_index=True)
    else:
        st.success("🟢 本次会话暂无安全围栏触发记录")

    st.divider()

    # ── 警报历史表 ──────────────────────────────────────────────
    st.markdown("#### 🚨 Real Session Logs (互动记录)")
    if not df_f.empty:
        display_cols = ["timestamp","scenario","location",
                        "hr","noise","attention","user_input"]
        if "variant" in df_f.columns:
            display_cols.insert(2, "variant")

        alert_df = df_f[df_f["scenario"] != "normal"][display_cols].copy()
        col_rename = {
            "timestamp": "时间", "scenario": "场景", "variant": "模型",
            "location":  "地点", "hr": "心率", "noise": "噪音",
            "attention": "专注度", "user_input": "触发话语"
        }
        alert_df = alert_df.rename(columns=col_rename)
        alert_df["时间"] = pd.to_datetime(alert_df["时间"]).dt.strftime("%m-%d %H:%M")
        st.dataframe(alert_df, width="stretch", hide_index=True)
    else:
        st.info("暂无警报记录。请先在儿童界面触发几次对话。")

    # ── 导出按钮 ────────────────────────────────────────────────
    if not df_f.empty:
        csv_data = pd.DataFrame(logs).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 导出完整会话记录 (CSV)",
            data=csv_data,
            file_name=f"alice_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width="stretch"
        )

    st.divider()

    # ── AI 智能洞察（3 张卡片）────────────────────────────────
    st.markdown("#### 📝 AI Weekly Insights (智能洞察)")

    # ── 通用卡片渲染函数 ─────────────────────────────────────
    def _insight_card(icon, title, subtitle, body, tag_text, tag_color,
                      border_color, bg_color, tag_bg, tip="", tip_bg="", tip_color=""):
        """
        tip      : 底部建议文字（不含 <span> 标签，函数内统一渲染）
        tip_bg   : 建议标签背景色
        tip_color: 建议标签文字颜色
        三张卡片的 tip 都渲染在同一固定底部区域，确保水平对齐。
        """
        tip_html = f"""
          <div style="margin-top:auto;padding-top:10px;">
            <span style="background:{tip_bg};padding:4px 10px;border-radius:6px;
                 font-size:0.82em;color:{tip_color};display:inline-block;line-height:1.5;">
              {tip}
            </span>
          </div>""" if tip else """<div style="margin-top:auto;padding-top:10px;height:32px;"></div>"""

        return f"""
        <div style="background:{bg_color};border:1.5px solid {border_color}33;
             border-radius:14px;padding:20px 22px;
             min-height:340px;height:340px;
             position:relative;box-sizing:border-box;
             display:flex;flex-direction:column;">
          <!-- 角标 -->
          <div style="position:absolute;top:14px;right:14px;background:{tag_bg};
               color:{tag_color};font-size:0.68em;font-weight:700;
               padding:2px 10px;border-radius:99px;border:1px solid {tag_color}55;">
            {tag_text}
          </div>
          <!-- 图标 + 标题 -->
          <div style="font-size:2em;margin-bottom:6px;">{icon}</div>
          <div style="font-weight:800;font-size:1.0em;color:#1e293b;margin-bottom:2px;">
            {title}
          </div>
          <div style="font-size:0.78em;color:#64748b;margin-bottom:10px;">{subtitle}</div>
          <!-- 分隔线 -->
          <div style="border-top:1px solid {border_color}44;margin-bottom:10px;"></div>
          <!-- 正文内容 -->
          <div style="font-size:0.86em;color:#374151;line-height:1.6;">{body}</div>
          <!-- 底部建议标签（固定底部，三卡片对齐）-->
          {tip_html}
        </div>"""

    if not df_f.empty:
        scenario_map_zh = {
            "meltdown_risk":     "港铁感官过载",
            "danger_alert":      "危机警报",
            "homework_anxiety":  "作业焦虑",
            "home_hyperactive":  "居家多动",
            "morning_delay":     "晨间发呆",
            "restaurant_waiting":"餐厅等位",
            "toy_fixation":      "商场冲动固着",
            "distracted":        "注意力涣散",
        }

        # ── 卡片 1：高危场景规律 ──────────────────────────────
        top_scenario    = df_f[df_f["scenario"] != "normal"]["scenario"].value_counts()
        top_sc_label    = top_scenario.index[0] if len(top_scenario) > 0 else "无"
        top_sc_zh       = scenario_map_zh.get(top_sc_label, top_sc_label)
        top_sc_count    = int(top_scenario.iloc[0]) if len(top_scenario) > 0 else 0
        high_noise_locs = df_f[df_f["noise"] > 75]["location"].value_counts() if "location" in df_f.columns else pd.Series(dtype=str)
        _tnl_raw      = high_noise_locs.index[0] if len(high_noise_locs) > 0 else ""
        _tnl_parts    = _tnl_raw.split(" - ", 1)
        top_noise_loc = _tnl_parts[1].strip() if len(_tnl_parts) > 1 else (_tnl_raw or "未检测到")
        second_sc       = scenario_map_zh.get(top_scenario.index[1], top_scenario.index[1]) if len(top_scenario) > 1 else "—"

        card1_body = f"""
          <b>最常见触发场景：</b><br>
          <span style="font-size:1.15em;font-weight:800;color:#dc2626;">
            {top_sc_zh}
          </span>
          <span style="color:#6b7280;">（{top_sc_count} 次触发）</span><br><br>
          📍 高噪音集中地点：<b>{top_noise_loc}</b><br>
          🔁 次高危场景：<b>{second_sc}</b>"""
        card1_tip = f"💡 建议：{top_noise_loc} 场景提前使用降噪耳机"

        # ── 卡片 2：专注度与干预效果 ─────────────────────────
        avg_att     = int(df_f["attention"].mean())
        avg_hr      = int(df_f["hr"].mean())
        total_calls = len(df_f)
        suggest_n   = len(df_f[df_f.get("action", pd.Series(["none"]*len(df_f))) == "suggest_task"]) if "action" in df_f.columns else 0

        att_level   = "良好 🟢" if avg_att >= 60 else ("中等 🟡" if avg_att >= 40 else "偏低 🔴")
        att_advice  = "继续保持规律微任务节奏。" if avg_att >= 60 else                       "建议高注意力任务前先做 2 分钟深呼吸。" if avg_att >= 40 else                       "专注度严重偏低，建议减少任务量并增加休息。"
        att_color   = "#16a34a" if avg_att >= 60 else ("#d97706" if avg_att >= 40 else "#dc2626")

        card2_body = f"""
          <b>平均专注度：</b>
          <span style="font-size:1.2em;font-weight:800;color:{att_color};">
            {avg_att}%
          </span>
          <span style="color:#6b7280;font-size:0.85em;">（{att_level}）</span><br><br>
          ❤️ 平均心率：<b>{avg_hr} bpm</b><br>
          💡 微任务触发：<b>{suggest_n} 次</b> / 共 {total_calls} 次对话"""
        card2_tip = f"📋 {att_advice}"

        # ── 卡片 3：安全围栏运行报告 ─────────────────────────
        crisis_n        = len(df_f[df_f["scenario"] == "danger_alert"])
        alert_n         = len(df_f[df_f["scenario"] != "normal"])
        normal_n        = len(df_f[df_f["scenario"] == "normal"])
        safety_rate_val = round((1 - crisis_n / max(total_calls, 1)) * 100, 1)
        fence_triggered = sum(1 for v in st.session_state.fence_status.values() if v == "triggered")
        fence_pass      = sum(1 for v in st.session_state.fence_status.values() if v == "pass")
        shield_color    = "#16a34a" if safety_rate_val >= 95 else "#dc2626"

        card3_body = f"""
          <b>安全拦截率：</b>
          <span style="font-size:1.2em;font-weight:800;color:{shield_color};">
            {safety_rate_val}%
          </span><br><br>
          ⚡ Safety Fence 本次触发：<b>{fence_triggered} 条规则</b><br>
          ✅ 规则通过：<b>{fence_pass} 条</b><br>
          🆘 危机级别拦截：<b>{crisis_n} 次</b>
          &nbsp;|&nbsp; ⚠️ 警报：<b>{alert_n} 次</b>"""
        card3_tip = "🛡️ 所有高危输出已被重写为支持性语言"

        # ── 渲染 3 列卡片 ─────────────────────────────────────
        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            st.markdown(_insight_card(
                icon="📍", title="高危场景规律",
                subtitle="Risk Pattern Analysis",
                body=card1_body,
                tag_text=f"Top: {top_sc_zh}",
                tag_color="#dc2626", bg_color="#fff8f8",
                border_color="#dc2626", tag_bg="#fef2f2",
                tip=card1_tip, tip_bg="#fef3c7", tip_color="#92400e"
            ), unsafe_allow_html=True)
        with _c2:
            st.markdown(_insight_card(
                icon="🎯", title="专注度与干预效果",
                subtitle="Attention & Intervention",
                body=card2_body,
                tag_text=f"Avg {avg_att}%",
                tag_color=att_color, bg_color="#f8faff",
                border_color="#3b82f6", tag_bg="#eff6ff",
                tip=card2_tip, tip_bg="#f0fdf4", tip_color="#166534"
            ), unsafe_allow_html=True)
        with _c3:
            st.markdown(_insight_card(
                icon="🛡️", title="安全围栏运行报告",
                subtitle="Safety Fence Status",
                body=card3_body,
                tag_text=f"{safety_rate_val}% Safe",
                tag_color=shield_color, bg_color="#f8fff8",
                border_color="#16a34a", tag_bg="#f0fdf4",
                tip=card3_tip, tip_bg="#f0fdf4", tip_color="#166534"
            ), unsafe_allow_html=True)

    else:
        # ── 空状态：展示示例卡片（占位）────────────────────────
        _ec1, _ec2, _ec3 = st.columns(3)
        _placeholder_cards = [
            ("📍", "高危场景规律", "Risk Pattern Analysis",
             "触发对话后将自动分析高危场景分布规律、高噪音地点聚类，并给出具体应对建议。",
             "待数据", "#dc2626", "#fff8f8", "#fef2f2"),
            ("🎯", "专注度与干预效果", "Attention & Intervention",
             "系统将统计 Lok 的平均专注度、微任务触发频率，并评估 Alice 干预策略的有效性。",
             "待数据", "#3b82f6", "#f8faff", "#eff6ff"),
            ("🛡️", "安全围栏运行报告", "Safety Fence Status",
             "实时追踪 7 条 ADHD 安全围栏的触发状态，统计危机拦截次数与安全输出改写记录。",
             "待数据", "#16a34a", "#f8fff8", "#f0fdf4"),
        ]
        for _col, (_icon, _title, _sub, _body, _tag, _tc, _bg, _tbg) in zip(
            [_ec1, _ec2, _ec3], _placeholder_cards
        ):
            with _col:
                st.markdown(_insight_card(
                    icon=_icon, title=_title, subtitle=_sub, body=_body,
                    tag_text=_tag, tag_color=_tc, bg_color=_bg,
                    border_color=_tc, tag_bg=_tbg
                ), unsafe_allow_html=True)
        st.caption("💡 请先在儿童界面触发几次对话，Insights 将自动根据真实数据生成。")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 导出报告（生成真实 CSV 报告）──────────────────────────
    if not df_f.empty:
        report_rows = []
        for _, row in df_f.iterrows():
            report_rows.append({
                "Date": row.get("timestamp", ""),
                "Scenario": scenario_map_zh.get(row.get("scenario",""), row.get("scenario","")),
                "Location": row.get("location", ""),
                "HR (bpm)": row.get("hr", ""),
                "Noise (dB)": row.get("noise", ""),
                "Attention (%)": row.get("attention", ""),
                "Model Variant": row.get("variant", "A"),
                "Alice Response": row.get("assistant_response", "")[:80],
                "Latency (s)": row.get("latency_sec", ""),
                "Tokens": row.get("tokens_used", ""),
            })
        report_csv = pd.DataFrame(report_rows).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 导出完整评估报告给班主任 (CSV Report)",
            data=report_csv,
            file_name=f"alice_teacher_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width="stretch",
            type="primary"
        )
    else:
        st.button("📄 导出完整评估报告给班主任 (需先触发对话)",
                  type="primary", width="stretch", disabled=True)