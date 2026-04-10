import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_client import LLMClient

def test_basic_connection():
    """测试1：验证API连接是否正常"""
    print("\n" + "="*60)
    print("测试1：验证智谱AI API连接")
    print("="*60)
    
    client = LLMClient()
    system_prompt = "你是一个友好的助手。"
    user_message = "你好，这是一个连接测试。"
    
    print(f"发送消息: {user_message}")
    response = client.chat(system_prompt, user_message)
    print(f"收到回复: {response}\n")
    
    if "[错误]" not in response:
        print("✅ 测试1通过：API连接正常\n")
        return True
    else:
        print("❌ 测试1失败：API连接异常\n")
        return False

def test_adhd_role_reversal():
    """测试2：验证角色反转逻辑"""
    print("="*60)
    print("测试2：验证ADHD角色反转交互")
    print("="*60)
    
    client = LLMClient()
    system_prompt = """
你是一个需要帮助的8岁机器人小伙伴。
当遇到困难时，你会向孩子求助，而不是命令孩子。
绝不使用命令式语气（禁止说：你应该、你要、快点）。
只能用请求帮助的方式（例如：你能帮我吗？我有点害怕）。
"""
    user_message = "早晨出门前，孩子在玩玩具忘记穿鞋"
    
    print(f"场景输入: {user_message}")
    response = client.chat(system_prompt, user_message)
    print(f"机器人回复: {response}\n")
    
    # 检查是否包含请求帮助的语气
    help_keywords = ["帮我", "你能", "我忘记", "我不知道", "我们一起", "我有点"]
    has_help_tone = any(keyword in response for keyword in help_keywords)
    
    if has_help_tone:
        print("✅ 测试2通过：角色反转逻辑正常\n")
        return True
    else:
        print("⚠️  测试2警告：回复中未检测到明显的请求帮助语气\n")
        return False

if __name__ == "__main__":
    print("\n🤖 ADHD陪伴机器人 - 开发环境测试")
    print("测试时间:", __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 运行测试
    test1_passed = test_basic_connection()
    test2_passed = test_adhd_role_reversal()
    
    # 总结
    print("="*60)
    print("测试总结")
    print("="*60)
    if test1_passed and test2_passed:
        print("🎉 所有测试通过！开发环境搭建完成，可以进入下一阶段。")
    elif test1_passed:
        print("✅ API连接正常")
        print("⚠️  建议优化System Prompt以增强角色反转效果")
    else:
        print("❌ 请检查API密钥配置")
    print("="*60 + "\n")
