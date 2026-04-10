import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_client import LLMClient
from src.prompt_builder import PromptBuilder
from src.rule_validator import RuleValidator

def test_scenario_responses():
    """测试不同场景下的机器人回复"""
    
    print("\n🤖 ADHD陪伴机器人 - 场景测试")
    print("="*60)
    
    client = LLMClient()
    validator = RuleValidator()
    
    # 测试场景列表
    scenarios = [
        {
            "name": "早晨出门准备",
            "type": "morning_routine",
            "user_input": "孩子在玩玩具，忘记穿鞋，快要迟到了"
        },
        {
            "name": "作业拖延",
            "type": "homework_time",
            "user_input": "孩子盯着作业本发呆，不知道从哪里开始"
        },
        {
            "name": "情绪崩溃",
            "type": "emotion_meltdown",
            "user_input": "孩子因为拼图拼不好而哭泣"
        },
        {
            "name": "港铁感官超载",
            "type": "sensory_overload",
            "user_input": "在港铁上，孩子捂着耳朵说太吵"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*60}")
        print(f"场景{i}：{scenario['name']}")
        print(f"{'='*60}")
        print(f"情景描述: {scenario['user_input']}")
        
        # 构建场景Prompt
        system_prompt = PromptBuilder.build_scenario_prompt(scenario['type'])
        
        # 获取LLM回复
        response = client.chat(system_prompt, scenario['user_input'])
        print(f"\n机器人回复: {response}")
        
        # 验证合规性
        validator.print_validation_report(response)
    
    print("\n" + "="*60)
    print("✅ 所有场景测试完成")
    print("="*60)

if __name__ == "__main__":
    test_scenario_responses()
