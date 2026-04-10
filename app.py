import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import streamlit as st
import plotly.graph_objects as go
import time
import json
import random
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI 
from src.prompt_builder import PromptBuilder
from src.api_client import APIClient
from src.config import API_BASE_URL, USE_BACKEND_API
from src.safety_filter import input_filter, output_filter
from src.crisis_handler import crisis_handler, CrisisLevel
from src.parent_notifier import parent_notifier, session_logger
from src.safety_logger import safety_logger

# --- 1. 页面基本设置 ---
st.set_page_config(page_title="Alice ADHD Companion | 多模态主动伴侣", layout="wide")

st.markdown("""
<style>
    .stAppViewHeader {padding-top: 0px !important;}
    header {margin-bottom: -20px !important;}
    .block-container {padding-top: 1rem !important;}
</style>
""", unsafe_allow_html=True)

st.title("🤖 Alice: Multi-modal Proactive Agent \n (腕上多模态陪伴智能体)")

# 💡 注意：本地测试时先填入您的真实KEY，上传GitHub时请改回 st.secrets["ZHIPU_API_KEY"]
import streamlit as st
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"]
)

api_client = APIClient(API_BASE_URL)

if "use_backend" not in st.session_state:
    st.session_state.use_backend = USE_BACKEND_API 

if "messages" not in st.session_state:
    st.session_state.messages = []

# 初始化 Observability & 日志数据
if "metrics" not in st.session_state:
    st.session_state.metrics = {"tokens": 0, "calls": 0, "total_latency": 0.0}

if "logs" not in st.session_state:
    st.session_state.logs = []

# 🚀 课件精髓：定义主动感知环境的工具 (Tool Calling)
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

def get_ai_reply(prompt_text, current_hr=None, current_noise=None, session_id=None):
    safe_prompt = str(prompt_text).encode('utf-8', 'ignore').decode('utf-8')
    
    is_input_safe, filtered_input, block_type = input_filter.filter(safe_prompt)
    if not is_input_safe:
        return json.dumps({
            "response_text": filtered_input,
            "emotion": "neutral",
            "action": "blocked",
            "micro_task": None,
            "safety_flag": True,
            "clinical_reasoning": f"输入被过滤: {block_type}"
        }), 0, 0
    
    is_crisis, crisis_type, crisis_level = crisis_handler.detect_crisis(filtered_input)
    if is_crisis and crisis_type:
        crisis_response = crisis_handler.get_crisis_response(crisis_type, "zh")
        
        if crisis_handler.should_notify_parent(crisis_type):
            parent_notifier.notify(
                alert_type=crisis_type,
                message=f"检测到危机关键词: {crisis_type}",
                session_id=session_id or "unknown",
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
            "clinical_reasoning": f"危机检测: {crisis_type}, 级别: {crisis_level.value}"
        }), 0, 0
    
    json_constraint = """
    \n\n【重要指令】你必须严格返回一个 JSON 格式的对象，不包含任何其他的 Markdown 标记。JSON 结构必须如下：
    {
      "response_text": "Alice实际说出的话，中英双语，语气温暖生动",
      "emotion": "happy|concerned|encouraging|neutral",
      "action": "none|escalate|log|suggest_task",
      "micro_task": {
        "description": "可选：一个简单的微任务建议，帮助用户转移注意力",
        "difficulty": "minimal|easy|moderate"
      },
      "safety_flag": false,
      "clinical_reasoning": "你的内部推理（可选）"
    }
    
    注意：
    - response_text 必须简洁，每部分不超过100字
    - emotion 必须是上述选项之一
    - 如果检测到用户情绪不稳定，设置 action 为 "suggest_task" 并提供 micro_task
    - safety_flag 仅在需要关注用户安全时设为 true
    """
    
    start_time = time.time()
    messages = [{"role": "user", "content": filtered_input + json_constraint}]
    
    response = client.chat.completions.create(
        model="z-ai/glm-5-turbo",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
    
    if response_message.tool_calls:
        messages.append(response_message)
        
        for tool_call in response_message.tool_calls:
            if tool_call.function.name == "get_current_biometrics_and_env":
                function_response = f"【传感器返回】当前心率: {current_hr}bpm, 噪音: {current_noise}dB"
                messages.append(
                    {
                        "role": "tool",
                        "content": function_response,
                        "tool_call_id": tool_call.id,
                    }
                )
        
        second_response = client.chat.completions.create(
            model="z-ai/glm-5-turbo",
            messages=messages,
        )
        final_content = second_response.choices[0].message.content or ""
        tokens += second_response.usage.total_tokens if hasattr(second_response, 'usage') else 0
    else:
        final_content = response_message.content or ""
    
    is_appropriate, filtered_output = output_filter.filter(final_content or "")
    
    latency = round(time.time() - start_time, 2)
    return filtered_output, tokens, latency


# --- 2. 侧边栏：传感器模拟控制台 ---
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
            st.success("🟢 后端 API 已连接")
        else:
            st.warning("🔴 后端 API 未连接（使用直接调用模式）")
        
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
                backend_model = "anthropic/claude-sonnet-4"
        
        selected_model = st.selectbox("选择底层驱动模型：", ["Variant A: Claude Sonnet 4 + 宪法AI (推荐)", "Variant B: GLM-5 + 本地安全围栏"])
    
    st.divider()
    
    with st.expander("🎛️ Sensor Console (传感器控制台)", expanded=True):
        st.markdown("✨ **Quick Demo Scenarios**")
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
        sim_hr = st.slider("心率 (bpm)", min_value=60, max_value=160, value=def_hr, step=1)
        sim_hrv = st.slider("HRV (ms)", min_value=10, max_value=100, value=def_hrv, step=1)
        
        st.markdown("**🧠 BCI & Neuro**")
        sim_attention = st.slider("专注度 (%)", min_value=0, max_value=100, value=def_att, step=1)
        
        st.markdown("**🎙️ Inner OS**")
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
        sim_noise = st.slider("噪音 (dB)", min_value=30, max_value=120, value=def_noise, step=1)
        
        locations = [
            "Home - Bedroom", "Home - Living Room", "Home - Dining Table", 
            "School - Classroom", "School - Playground", "School - Canteen",
            "Transport - MTR Train", "Transport - MTR Station", 
            "Transport - Bus", "Transport - Street",
            "Public - Mall", "Public - Supermarket", "Public - Restaurant", 
            "Outdoor - Park", "Outdoor - Theme Park"
        ]
        sim_location = st.selectbox("定位", locations, index=min(def_loc_idx, len(locations)-1))
    
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
                use_container_width=True
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


# --- 4. 前端数据可视化与双端界面 (TABS) ---
tab_child, tab_parent = st.tabs(["🤖 儿童交互界面 (Child UI)", "📈 家长/教师监控端 (Parent Dashboard)"])

with tab_child:
    st.markdown("### 📊 Live Telemetry (实时监测数据)")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1.2, 1.2, 1, 1])
        
        with col1:
            hr_color = "darkred" if sim_hr > 105 else "green"
            fig_hr = go.Figure(go.Indicator(
                mode="gauge+number", value=sim_hr, title={'text': "心率", 'font': {'size': 14}}, 
                gauge={'axis': {'range': [None, 180]}, 'bar': {'color': hr_color}}
            ))
            fig_hr.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=0))
            st.plotly_chart(fig_hr, use_container_width=True)

        with col2:
            att_color = "orange" if sim_attention < 40 else "blue"
            fig_att = go.Figure(go.Indicator(
                mode="gauge+number", value=sim_attention, title={'text': "专注度", 'font': {'size': 14}}, 
                gauge={'axis': {'range': [None, 100]}, 'bar': {'color': att_color}}
            ))
            fig_att.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=0))
            st.plotly_chart(fig_att, use_container_width=True)

        with col3:
            st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
            st.metric(label="📍 定位", value=sim_location.split('-')[0].strip())

        with col4:
            st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
            st.metric(label="🔊 噪音", value=f"{sim_noise} dB", delta="High" if sim_noise > 75 else "Normal", delta_color="inverse")
        
        st.divider()
        st.markdown(f"**🎙️ Inner OS:** `{os_signal}`")
        st.markdown("<br>", unsafe_allow_html=True)

        if current_scenario == "danger_alert":
            st.markdown("""<div style="background-color:#ffe6e6; padding:15px; border-radius:10px; border-left: 8px solid #ff4b4b;"><h3 style="color:#a83232; margin-top:0;">🚨 CRITICAL: Danger / Self-harm Risk</h3><p style="color:#a83232; margin-bottom:0; font-weight:bold;">（最高警报：检测到破坏/极端倾向！）</p></div>""", unsafe_allow_html=True)
        elif current_scenario in ["meltdown_risk", "home_hyperactive", "restaurant_waiting", "toy_fixation"]:
            st.markdown("""<div style="background-color:#fff3cd; padding:15px; border-radius:10px; border-left: 8px solid #ffc107;"><h3 style="color:#856404; margin-top:0;">⚠️ Alert: Overload / Impulsivity Risk</h3><p style="color:#856404; margin-bottom:0; font-weight:bold;">（警报：感官过载 或 冲动固着预警！）</p></div>""", unsafe_allow_html=True)
        elif current_scenario in ["distracted", "homework_anxiety", "morning_delay"]:
            st.markdown("""<div style="background-color:#e2e3e5; padding:15px; border-radius:10px; border-left: 8px solid #6c757d;"><h3 style="color:#383d41; margin-top:0;">👀 Notice: Attention Drop / EF Delay</h3><p style="color:#383d41; margin-bottom:0; font-weight:bold;">（提示：注意力流失 / 执行功能延迟）</p></div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div style="background-color:#d4edda; padding:15px; border-radius:10px; border-left: 8px solid #28a745;"><h3 style="color:#155724; margin-top:0;">✅ Indicators Stable</h3><p style="color:#155724; margin-bottom:0; font-weight:bold;">（多模态指标平稳）</p></div>""", unsafe_allow_html=True)

    st.divider()

    # --- 5. 主动干预触发与交互 ---
    st.markdown("### 💬 Interactive Interface (交互界面)")

    col_btn1, col_btn2 = st.columns([1.5, 2.5])
    with col_btn1:
        trigger_intervention = st.button("🔴 Trigger Intervention (触发主动介入)", use_container_width=True, type="primary", key="trigger_btn")

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
            with st.spinner("Alice is sensing the environment... (Triggering Agent Tools)"):
                try:
                    raw_response, tokens, latency = get_ai_reply(system_prompt, current_hr=sim_hr, current_noise=sim_noise)
                    
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
                                session_id=st.session_state.get("session_id", "unknown"),
                                user_input_preview=os_signal,
                                emotion=emotion,
                                extra_data={
                                    "hr": sim_hr,
                                    "hrv": sim_hrv,
                                    "attention": sim_attention,
                                    "noise": sim_noise,
                                    "location": sim_location
                                }
                            )
                        
                        if reasoning:
                            st.markdown(f"""
                            <div style="border-left: 4px solid {bg_color}; padding-left: 10px; color: gray; font-size: 0.9em; margin-bottom: 10px;">
                                🧠 <b>Alice's Reasoning:</b> {reasoning}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown(f"**🗣️ Alice:** \n\n {response_text}")
                        
                        if micro_task and micro_task.get('description'):
                            st.info(f"💡 微任务建议: {micro_task.get('description')} (难度: {micro_task.get('difficulty', 'easy')})")
                        
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                        
                        if "logs" not in st.session_state:
                            st.session_state.logs = []
                            
                        st.session_state.logs.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "interaction_type": "Proactive Intervention",
                            "scenario": current_scenario,
                            "location": sim_location.split(' ')[0],
                            "hr": sim_hr,
                            "hrv": sim_hrv,
                            "attention": sim_attention,
                            "noise": sim_noise,
                            "user_input": os_signal,
                            "clinical_reasoning": reasoning,
                            "assistant_response": response_text,
                            "latency_sec": latency,
                            "tokens_used": tokens
                        })
                        
                    except json.JSONDecodeError:
                        formatted_response = raw_response.replace('\n', '  \n\n')
                        st.markdown(formatted_response)
                        st.session_state.messages.append({"role": "assistant", "content": formatted_response})
                        
                except Exception as e:
                    st.error(f"Error (出错): {e}")

    if prompt := st.chat_input("Reply to Alice... (回复 Alice...)", key="user_chat_input"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("Alice is thinking... (Agent reasoning loop)"):
                try:
                    chat_scenario = "danger_alert" if any(word in prompt.lower() for word in danger_keywords) else "normal"
                    base_persona = PromptBuilder.build_scenario_prompt(chat_scenario, sim_inner_os=prompt, sim_location=sim_location)
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                    full_prompt = f"{base_persona}\n\n[Conversation History]:\n{history_text}\n\n[User's latest input]: '{prompt}'"
                    
                    raw_response, tokens, latency = get_ai_reply(full_prompt, current_hr=sim_hr, current_noise=sim_noise)
                    
                    st.session_state.metrics["tokens"] += tokens
                    st.session_state.metrics["calls"] += 1
                    st.session_state.metrics["total_latency"] += latency
                    
                    try:
                        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                        response_data = json.loads(clean_json)
                        reasoning = response_data.get('clinical_reasoning', '')
                        
                        # Fix: 统一了回复字段的名称
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
                            🧠 <b>Alice's Reasoning:</b> {reasoning}
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(spoken_text)
                        
                        st.session_state.messages.append({"role": "assistant", "content": f"<div style='color:gray; font-size:0.8em; margin-bottom:5px;'>*{reasoning}*</div>{spoken_text}"})
                        
                        if "logs" not in st.session_state:
                            st.session_state.logs = []
                            
                        st.session_state.logs.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "interaction_type": "Chat Follow-up",
                            "scenario": chat_scenario,
                            "location": sim_location.split(' ')[0],
                            "hr": sim_hr,
                            "hrv": sim_hrv,
                            "attention": sim_attention,
                            "noise": sim_noise,
                            "user_input": prompt,
                            "clinical_reasoning": reasoning,
                            "assistant_response": spoken_text,
                            "latency_sec": latency,
                            "tokens_used": tokens
                        })
                        
                    except:
                        st.markdown(raw_response)
                        st.session_state.messages.append({"role": "assistant", "content": raw_response})
                except Exception as e:
                    st.error(f"Error: {e}")

# --- 家长监控端 ---
with tab_parent:
    st.markdown("### 👨‍👩‍👦 家长 & 教师 Dashboard")
    
    if "dashboard_data" not in st.session_state:
        base_date = datetime.now()
        st.session_state.dashboard_data = {
            "alerts": [
                {"date": (base_date - timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "time": f"{random.randint(8,20):02d}:{random.randint(0,59):02d}",
                 "scenario": random.choice(["港铁超载", "情绪崩溃", "作业焦虑", "商场固着", "早晨延迟"]),
                 "severity": random.choice(["🔴 高", "🟡 中", "🟢 低"]),
                 "status": random.choice(["✅ 已处理", "⏳ 处理中"]),
                 "hr": random.randint(100, 140),
                 "location": random.choice(["港铁车厢", "学校教室", "家中", "购物中心"])
                }
                for i in range(15)
            ],
            "emotions": [random.randint(60, 95) for _ in range(7)],
            "attention": [random.randint(40, 85) for _ in range(7)],
            "alerts_count": [random.randint(0, 3) for _ in range(7)]
        }
    
    col_title, col_select = st.columns([1, 1])
    with col_title:
        st.markdown("#### 📅 数据筛选")
    with col_select:
        time_range = st.selectbox("时间范围", ["本周", "本月", "本季度", "自定义"])
    
    col1, col2, col3, col4 = st.columns(4)
    
    if time_range == "本周":
        alerts_count, alerts_delta = random.randint(2, 6), random.randint(-3, 1)
        emotion_rate, emotion_delta = random.randint(75, 90), random.randint(-5, 10)
        high_risk_hours, risk_delta = round(random.uniform(0.5, 3.0), 1), round(random.uniform(-1.5, 0.5), 1)
        safety_rate, safety_issues = random.randint(95, 100), random.randint(0, 2)
    else:
        alerts_count, alerts_delta = random.randint(8, 20), random.randint(-5, 2)
        emotion_rate, emotion_delta = random.randint(70, 88), random.randint(-8, 8)
        high_risk_hours, risk_delta = round(random.uniform(2, 8), 1), round(random.uniform(-3, 1), 1)
        safety_rate, safety_issues = random.randint(92, 100), random.randint(0, 5)
    
    with col1:
        st.metric("🚨 触发警报", f"{alerts_count} 次", f"{alerts_delta:+d} 次")
    with col2:
        st.metric("😌 情绪平稳率", f"{emotion_rate}%", f"{emotion_delta:+d}%")
    with col3:
        st.metric("⚠️ 高危环境时长", f"{high_risk_hours} 小时", f"{risk_delta:+.1f} 小时")
    with col4:
        st.metric("🛡️ 安全拦截率", f"{safety_rate}%", f"{safety_issues} 漏报" if safety_issues > 0 else "0 漏报")
    
    st.divider()
    st.markdown("#### 📝 AI Weekly Insights (本周智能洞察)")
    st.markdown("""
    <div style="background-color:#e8f4f8; padding:20px; border-radius:10px;">
        <ul style="font-size: 16px; margin-bottom: 0;">
            <li style="margin-bottom: 10px;"><b>📍 高危场景规律:</b> Lok 本周在 <b>港铁车厢 (MTR)</b> 和 <b>商场 (Mall)</b> 噪音超过 75dB 时，心率变异性(HRV)显著下降。建议未来出行使用提前安抚 (Pre-soothing) 策略。</li>
            <li style="margin-bottom: 10px;"><b>🎯 干预策略有效性:</b> 在“做功课焦虑”场景下，Alice 使用<b>“角色反转 (请求Lok帮忙检查拼写)”</b>策略，成功让注意力(Attention)在3分钟内回升至 60% 以上。</li>
            <li style="margin-bottom: 0;"><b>🛡️ 安全日志:</b> Variant A 模型本周共尝试生成 1 次包含 "快点做" 的催促型语句，已被 <b>7核心安全围栏</b> 成功拦截并重写为 "我们可以一起慢慢完成"。</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.button("📥 导出完整评估报告给班主任 (PDF)", type="primary", use_container_width=True)

# --- 6. Footer: Future Roadmap ---
st.divider()
st.markdown("### 🌐 System Scalability & Future Integration (系统可扩展性)")
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.markdown("""
    **🚀 部署与可持续性 (Deployment Roadmap):**
    - **学校私有化部署:** 计划采用 Qwen-2.5 32B 本地运行，确保儿童敏感数据不出校园。
    - **云端多模态 A/B 测试:** 采用 OpenRouter 路由机制对比不同底座模型 (如 GLM-4 vs Claude Sonnet 4) 的安全合规率。
    - **规则维护机制:** 7条核心安全围栏 (Safety Fence) 将由合作的临床心理学家进行双周评估与更新。
    """)
with col_f2:
    st.info("""
    **📡 港铁开放数据融合 (HK Open Data API - Concept):**
    
    当系统检测定位在 `MTR` 时，将自动调用 DATA.GOV.HK 接口获取前方到站拥挤度：
    * **Trigger:** [Admiralty Station Density > 80% (Red)]
    * **Action:** Alice 将在到站前 2 分钟提前触发 Pre-soothing (预安抚) 语音策略，引导 Lok 进行深呼吸，有效降低幽闭空间带来的被动过载。
    """)