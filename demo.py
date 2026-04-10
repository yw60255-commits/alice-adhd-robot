"""
ADHD陪伴机器人 (Alice) - 交互式演示终端
用于课堂展示：实时交互 + 规则合规性实时检测
"""

import sys
import os
import time

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.llm_client import LLMClient
from src.prompt_builder import PromptBuilder
from src.rule_validator import RuleValidator

class AliceDemoConsole:
    def __init__(self):
        self.client = LLMClient()
        self.validator = RuleValidator()
        self.current_scenario = "morning_routine"
        
        # 场景菜单
        self.scenarios = {
            "1": {"id": "morning_routine", "name": "早晨出门准备 (执行功能挑战)"},
            "2": {"id": "homework_time", "name": "作业时间 (任务拆解/拖延)"},
            "3": {"id": "emotion_meltdown", "name": "遭遇挫折 (情绪崩溃)"},
            "4": {"id": "sensory_overload", "name": "港铁/商场 (感官超载)"}
        }

    def print_header(self):
        """打印漂亮的欢迎界面"""
        # 清屏
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n" + "="*70)
        print("🤖  Alice - ADHD智能陪伴机器人 (香港学龄期儿童版)  🤖")
        print("="*70)
        print("CA5325 项目展示 Demo | 基于大语言模型与循证干预规则双轨管控\n")

    def print_scenario_menu(self):
        """打印场景选择菜单"""
        print("【请选择交互场景】")
        for key, val in self.scenarios.items():
            print(f"  [{key}] {val['name']}")
        print("  [q] 退出程序")
        print("-" * 70)

    def print_chat_history(self, user_msg, bot_response, validation_result):
        """打印聊天记录和验证结果"""
        print("\n" + "-" * 70)
        print(f"👦 孩子/家长: {user_msg}")
        print(f"🤖 Alice:    {bot_response}")
        
        # 打印合规性分析徽章
        if validation_result["is_compliant"]:
            status = f"✅ 合规通过 (得分:{validation_result['score']:.1f})"
            color_code = "\033[92m" # 绿色
        else:
            status = f"❌ 规则告警 (得分:{validation_result['score']:.1f})"
            color_code = "\033[91m" # 红色
            
        reset_code = "\033[0m"
        
        print(f"\n📊 [系统安全围栏检测]: {color_code}{status}{reset_code}")
        
        # 如果有违规或建议，显示出来（Demo的亮点！）
        if validation_result["violations"]:
            print("   ⚠️ 违规项:")
            for v in validation_result["violations"]:
                print(f"      - {v}")
                
        if validation_result["recommended_found"]:
            print("   ✨ 循证策略命中:")
            for r in validation_result["recommended_found"]:
                print(f"      - 关键词: '{r}'")
                
        print("-" * 70 + "\n")

    def run(self):
        """运行交互循环"""
        self.print_header()
        
        while True:
            self.print_scenario_menu()
            choice = input("\n请输入选项 (1-4, 或 q): ").strip()
            
            if choice.lower() == 'q':
                print("\n感谢使用 Alice Demo，再见！👋\n")
                break
                
            if choice not in self.scenarios:
                print("\n⚠️ 无效选项，请重新选择。\n")
                continue
                
            scenario_info = self.scenarios[choice]
            self.current_scenario = scenario_info["id"]
            
            # 清屏并进入聊天模式
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*70)
            print(f"🔄 当前场景: {scenario_info['name']}")
            print("="*70)
            print("提示: 输入 'b' 返回场景菜单, 输入 'q' 退出程序\n")
            
            system_prompt = PromptBuilder.build_scenario_prompt(self.current_scenario)
            
            # 内部聊天循环
            while True:
                user_msg = input("👦 孩子/家长输入: ").strip()
                
                if user_msg.lower() == 'q':
                    print("\n感谢使用 Alice Demo，再见！👋\n")
                    return
                if user_msg.lower() == 'b':
                    self.print_header()
                    break
                if not user_msg:
                    continue
                    
                print("🤖 Alice 正在思考...")
                
                try:
                    # 获取回复
                    response = self.client.chat(system_prompt, user_msg)
                    # 验证合规性
                    validation = self.validator.validate_response(response)
                    # 清除"思考中"并打印结果
                    sys.stdout.write("\033[F\033[K") # 删除上一行
                    self.print_chat_history(user_msg, response, validation)
                    
                except Exception as e:
                    print(f"\n❌ 发生错误: {str(e)}\n")

if __name__ == "__main__":
    try:
        demo = AliceDemoConsole()
        demo.run()
    except KeyboardInterrupt:
        print("\n\n强制退出，再见！👋\n")
