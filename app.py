"""
ADHD陪伴机器人 (Alice) - Web演示版 (使用 Streamlit)
"""
import streamlit as st
import sys
import os
import time

# 确保能找到src目录
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.llm_client import LLMClient
from src.prompt_builder import PromptBuilder
from src.rule_validator import RuleValidator

import os

# 在这里直接写入您的智谱 API Key
os.environ["ZHIPUAI_API_KEY"] = "4ec5f1fcab3d44ecaa75b6f0f16f1924.dU68s62CR7kfuBMH"

# 页面配置
st.set_page_config(
    page_title="Alice - ADHD智能陪伴机器人",
    page_icon="🤖",
    layout="centered"
)

# 初始化Session State（用于保存跨页面的聊天记录和状态）
if 'client' not in st.session_state:
    st.session_state.client = LLMClient()
    st.session_state.validator = RuleValidator()
    st.session_state.messages = []
    st.session_state.current_scenario = "morning_routine"

# 场景定义
SCENARIOS = {
    "morning_routine": "🌅 早晨出门准备 (执行功能挑战)",
    "homework_time": "📚 作业时间 (任务拆解/拖延)",
    "emotion_meltdown": "😭 遭遇挫折 (情绪崩溃)",
    "sensory_overload": "🚇 港铁/商场 (感官超载)"
}

# 侧边栏：控制面板和场景选择
with st.sidebar:
    st.image("https://api.dicebear.com/7.x/bottts/svg?seed=Alice&backgroundColor=b6e3f4", width=150)
    st.title("🤖 Alice 控制台")
    st.markdown("---")
    
    st.subheader("📋 选择测试场景")
    selected_scenario_name = st.radio(
        "切换场景会清空当前对话",
        list(SCENARIOS.values()),
        index=list(SCENARIOS.keys()).index(st.session_state.current_scenario)
    )
    
    # 根据用户选择的名称反查场景ID
    new_scenario_id = [k for k, v in SCENARIOS.items() if v == selected_scenario_name][0]
    
    # 如果切换了场景，清空聊天记录
    if new_scenario_id != st.session_state.current_scenario:
        st.session_state.current_scenario = new_scenario_id
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.subheader("⚙️ 系统监控面板")
    st.info("💡 **双轨管控系统**运行中\n\n1️⃣ 大语言模型生成\n2️⃣ 循证医学规则二次校验")
    
    if st.button("🗑️ 清空当前对话"):
        st.session_state.messages = []
        st.rerun()

# 主界面：标题
st.title("🤖 Alice - ADHD专属成长陪伴者")
st.markdown(f"**当前测试场景：** `{SCENARIOS[st.session_state.current_scenario]}`")
st.markdown("---")

# 主界面：渲染历史聊天记录
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user", avatar="👦"):
            st.markdown(message["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(message["content"])
            
            # 显示该条回复的合规性检测卡片
            validation = message.get("validation", None)
            if validation:
                with st.expander("📊 查看系统安全围栏检测报告", expanded=False):
                    if validation["is_compliant"]:
                        st.success(f"✅ 合规通过 (得分: {validation['score']:.1f}/1.0)")
                    else:
                        st.error(f"❌ 规则告警 (得分: {validation['score']:.1f}/1.0)")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if validation["recommended_found"]:
                            st.markdown("**✨ 命中的循证策略关键词:**")
                            for r in validation["recommended_found"]:
                                st.markdown(f"- `{r}`")
                        else:
                            st.markdown("**✨ 命中的循证策略关键词:** 无")
                            
                    with col2:
                        if validation["violations"]:
                            st.markdown("**⚠️ 违规项预警:**")
                            for v in validation["violations"]:
                                st.markdown(f"- `{v}`")
                        else:
                            st.markdown("**⚠️ 违规项预警:** 无")

# 聊天输入框
if prompt := st.chat_input("输入对话进行测试（例如：Alice，你要迟到了快点穿鞋！）"):
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👦"):
        st.markdown(prompt)

    # 显示Alice的思考过程和回复
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Alice 正在思考... 🔄")
        
        try:
            # 获取系统Prompt
            system_prompt = PromptBuilder.build_scenario_prompt(st.session_state.current_scenario)
            
            # 调用API
            bot_response = st.session_state.client.chat(system_prompt, prompt)
            
            # 进行规则校验
            validation_result = st.session_state.validator.validate_response(bot_response)
            
            # 渲染回复
            message_placeholder.markdown(bot_response)
            
            # 渲染校验结果卡片
            with st.expander("📊 查看系统安全围栏检测报告", expanded=True):
                if validation_result["is_compliant"]:
                    st.success(f"✅ 合规通过 (得分: {validation_result['score']:.1f}/1.0)")
                else:
                    st.error(f"❌ 规则告警 (得分: {validation_result['score']:.1f}/1.0)")
                
                col1, col2 = st.columns(2)
                with col1:
                    if validation_result["recommended_found"]:
                        st.markdown("**✨ 命中的循证策略关键词:**")
                        for r in validation_result["recommended_found"]:
                            st.markdown(f"- `{r}`")
                with col2:
                    if validation_result["violations"]:
                        st.markdown("**⚠️ 违规项预警:**")
                        for v in validation_result["violations"]:
                            st.markdown(f"- `{v}`")
            
            # 将完整数据存入历史记录
            st.session_state.messages.append({
                "role": "assistant", 
                "content": bot_response,
                "validation": validation_result
            })
            
        except Exception as e:
            message_placeholder.error(f"遇到错误: {str(e)}")
