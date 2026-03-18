import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import streamlit as st
import plotly.graph_objects as go
from zhipuai import ZhipuAI 
from src.prompt_builder import PromptBuilder

# --- 1. 页面基本设置 ---
st.set_page_config(page_title="Alice ADHD Companion | 多模态主动伴侣", layout="wide")
st.title("🤖 Alice: Multi-modal Proactive Agent \n (腕上多模态陪伴智能体)")

client = ZhipuAI(api_key="4ec5f1fcab3d44ecaa75b6f0f16f1924.dU68s62CR7kfuBMH") 

if "messages" not in st.session_state:
    st.session_state.messages = []

def get_ai_reply(prompt_text):
    safe_prompt = str(prompt_text).encode('utf-8', 'ignore').decode('utf-8')
    response = client.chat.completions.create(
        model="glm-4",
        messages=[{"role": "user", "content": safe_prompt}],
    )
    return response.choices[0].message.content

# --- 2. 侧边栏：传感器模拟控制台 ---
with st.sidebar:
    st.header("🎛️ Sensor Console \n (传感器控制台)")
    
    st.markdown("✨ **Quick Demo Scenarios (一键演示场景)**")
    demo_scenario = st.selectbox(
        "选择预设场景自动填充参数：",
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
    st.divider()

    # 预设参数逻辑优化 (符合真实儿童生理与环境数据逻辑)
    def_hr, def_hrv, def_att, def_noise = 85, 60, 80, 45
    def_os = "The weather is nice today (今天天气真好)"
    def_loc_idx = 0

    if "MTR Overload" in demo_scenario:
        # 港铁过载：心率飙升，HRV极低(压力大)，噪音极高，专注度被噪音击碎
        def_hr, def_hrv, def_att, def_noise, def_loc_idx = 125, 25, 20, 95, 8
        def_os = "It's too loud here, I hate it! (这里太吵了，我讨厌这里！)"
    elif "Homework" in demo_scenario:
        # 隐性焦虑：坐着所以心率不高，但HRV极低(心理崩溃)，极其安静但完全看不进书
        def_hr, def_hrv, def_att, def_noise, def_loc_idx = 90, 15, 15, 40, 0
        def_os = "This math problem is too hard... (这道数学题太难了...)"
    elif "Hyperactivity" in demo_scenario:
        # 多动发作：来回踱步导致心率偏高，烦躁，走神
        def_hr, def_hrv, def_att, def_noise, def_loc_idx = 110, 35, 30, 55, 1
        def_os = "I can't sit still, it's so annoying! (我根本坐不住，烦死了！)"
    elif "Morning" in demo_scenario:
        # 迟到发呆：毫无压力(心率/HRV正常)，但完全没在干正事(专注度极低)
        def_hr, def_hrv, def_att, def_noise, def_loc_idx = 75, 60, 20, 45, 0
        def_os = "Spacing out... (发呆中...无明确对话)"
    elif "Restaurant" in demo_scenario:
        # 等位不耐受：跺脚催促(心率高)，极度失去耐心(HRV低)，茶餐厅环境嘈杂
        def_hr, def_hrv, def_att, def_noise, def_loc_idx = 105, 25, 25, 75, 14
        def_os = "I can't wait anymore, I'm starving! (我等不及了，我快饿死了！)"
    elif "Toy Fixation" in demo_scenario:
        # 冲动固着：极度兴奋(心率暴增)，但出现了ADHD特有的病理性超专注(Hyperfocus)
        def_hr, def_hrv, def_att, def_noise, def_loc_idx = 130, 20, 95, 70, 12
        def_os = "I want this toy right now! (我现在就要买这个玩具！)"

    st.subheader("🫀 Biometrics (生理监测)")
    sim_hr = st.slider("Heart Rate (心率 - bpm)", min_value=60, max_value=160, value=def_hr, step=1)
    sim_hrv = st.slider("HRV (心率变异性 - ms)", min_value=10, max_value=100, value=def_hrv, step=1)
    
    st.subheader("🧠 BCI & Neuro (脑机数据)")
    sim_attention = st.slider("Attention Level (专注度 %)", min_value=0, max_value=100, value=def_att, step=1)
    
    st.subheader("🎙️ Mic / Inner OS (内心OS)")
    # 格式彻底统一：全为干净的“英文 (中文)”格式
    os_options = [
        def_os,
        "This math problem is too hard... (这道数学题太难了...)",
        "So boring, I want to play games. (好无聊，我想打游戏。)",
        "It's too loud here, I hate it! (这里太吵了，我讨厌这里！)",
        "I can't wait anymore, I'm starving! (我等不及了，我快饿死了！)",
        "I want this toy right now! (我现在就要买这个玩具！)",
        "I want to tear my homework apart! (烦死了，我想把作业撕了！)",
        "I feel terrible, everything is ruined! (我不想活了，一切都糟透了！)",
        "I'm so angry I want to hit someone! (别管我，我想打人！)",
        "Custom Input (自定义输入...在下方填写)"
    ]
    # 使用 set 去重，防止 def_os 重复出现，并保持顺序
    os_options = list(dict.fromkeys(os_options))
    selected_os = st.selectbox("快捷选择话术", os_options)
    
    custom_os = st.text_input("手动输入:", value="" if "Custom Input" not in selected_os else "在此输入")
    
    st.subheader("🌍 Environmental (环境)")
    sim_noise = st.slider("Noise Level (噪音 - dB)", min_value=30, max_value=120, value=def_noise, step=1)
    
    # 位置列表，确保下标对应
    locations = [
        "Home - Bedroom (家 - 卧室)", "Home - Living Room (家 - 客厅)", "Home - Dining Table (家 - 餐桌)", # 0, 1, 2
        "Home - Bathroom (家 - 浴室)", # 3
        "School - Classroom (学校 - 教室)", "School - Playground (学校 - 操场)", "School - Canteen/Cafeteria (学校 - 食堂)", # 4, 5, 6
        "School - Library (学校 - 图书馆)", # 7
        "Transport - Inside MTR Train (交通 - 港铁车厢内)", "Transport - MTR Station (交通 - 港铁站内)", # 8, 9
        "Transport - Inside Bus/Minibus (交通 - 巴士/小巴内)", "Transport - Street/Crosswalk (交通 - 街道/斑马线)", # 10, 11
        "Public - Shopping Mall (公共 - 购物中心)", "Public - Supermarket (公共 - 超市)", # 12, 13
        "Public - Cha Chaan Teng/Restaurant (公共 - 茶餐厅/餐厅)", "Public - Cinema (公共 - 电影院)", # 14, 15
        "Outdoor - Park/Playground (户外 - 公园/游乐场)", "Outdoor - Theme Park (户外 - 游乐园/主题公园)" # 16, 17
    ]
    sim_location = st.selectbox("Location (定位)", locations, index=def_loc_idx)

# --- 3. 核心逻辑：危机分级与路由 ---
os_signal = custom_os if "Custom Input" in selected_os else selected_os

# 危险词判定
danger_keywords = ["撕", "不想活", "想死", "烦死", "打人", "砸", "杀", "hate my life", "kill", "smash", "destroy", "tear"]

is_danger = any(word in os_signal.lower() for word in danger_keywords)
is_overload = (sim_hr > 105) or (sim_hrv < 30) or (sim_noise > 75)
is_distracted = (sim_attention < 40)

# 精准强制场景路由
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

# --- 4. 前端数据可视化 (极致排版版) ---
st.markdown("### 📊 Live Telemetry (实时监测数据)")

with st.container(border=True):
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1, 1])
    
    with col1:
        fig_hr = go.Figure(go.Indicator(mode="gauge+number", value=sim_hr, title={'text': "Heart Rate (心率)", 'font': {'size': 14}}, gauge={'axis': {'range': [None, 180]}, 'bar': {'color': "darkred" if sim_hr > 105 else "green"}}))
        fig_hr.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=0))
        st.plotly_chart(fig_hr, use_container_width=True)

    with col2:
        fig_att = go.Figure(go.Indicator(mode="gauge+number", value=sim_attention, title={'text': "Attention (专注度)", 'font': {'size': 14}}, gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "orange" if sim_attention < 40 else "blue"}}))
        fig_att.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=0))
        st.plotly_chart(fig_att, use_container_width=True)

    with col3:
        st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
        st.metric(label="📍 Location (定位)", value=sim_location.split(' ')[0])

    with col4:
        st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
        st.metric(label="🔊 Noise (噪音)", value=f"{sim_noise} dB", delta="High" if sim_noise > 75 else "Normal", delta_color="inverse")
    
    st.divider()
    st.markdown(f"**🎙️ Mic/OS:** `{os_signal}`")
    st.markdown("<br>", unsafe_allow_html=True)

    # 动态高级警报栏
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
        scenario_type=current_scenario, sim_hr=sim_hr, sim_noise=sim_noise, sim_inner_os=os_signal, sim_attention=sim_attention, sim_location=sim_location
    )
    
    with st.chat_message("assistant"):
        with st.spinner("Alice is sensing the environment..."):
            try:
                raw_response = get_ai_reply(system_prompt)
                formatted_response = raw_response.replace('\n', '  \n\n')
                st.markdown(formatted_response)
                st.session_state.messages.append({"role": "assistant", "content": formatted_response})
            except Exception as e:
                st.error(f"Error (出错): {e}")

if prompt := st.chat_input("Reply to Alice... (回复 Alice...)"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("Alice is thinking..."):
            try:
                chat_scenario = "danger_alert" if any(word in prompt.lower() for word in danger_keywords) else "normal"
                base_persona = PromptBuilder.build_scenario_prompt(chat_scenario, sim_inner_os=prompt, sim_location=sim_location)
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                full_prompt = f"{base_persona}\n\n[Conversation History]:\n{history_text}\n\n[User's latest input]: '{prompt}'"
                
                raw_response = get_ai_reply(full_prompt)
                formatted_response = raw_response.replace('\n', '  \n\n')
                st.markdown(formatted_response)
                st.session_state.messages.append({"role": "assistant", "content": formatted_response})
            except Exception as e:
                st.error(f"Error: {e}")