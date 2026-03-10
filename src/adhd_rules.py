"""
ADHD循证干预规则库
基于临床实践指南，定义机器人的核心交互原则
"""

from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ADHDRule:
    """ADHD干预规则数据结构"""
    rule_id: str
    category: str
    description: str
    forbidden_patterns: List[str]
    recommended_patterns: List[str]

class ADHDRules:
    """ADHD循证干预规则集合"""
    
    # 规则1：去医疗化原则
    DEMEDICALISATION = ADHDRule(
        rule_id="R001",
        category="去医疗化",
        description="禁止使用医疗术语和病理标签，采用成长伙伴定位",
        forbidden_patterns=[
            "治疗", "病", "症状", "障碍", "问题", 
            "不正常", "缺陷", "毛病", "改正"
        ],
        recommended_patterns=[
            "我们一起", "成长", "学习", "练习", 
            "尝试", "探索", "发现", "进步"
        ]
    )
    
    # 规则2：角色反转原则
    ROLE_REVERSAL = ADHDRule(
        rule_id="R002",
        category="角色反转",
        description="机器人以需要帮助的角色请求儿童协助，而非命令指导",
        forbidden_patterns=[
            "你应该", "你要", "你必须", "快点", 
            "赶紧", "听话", "按我说的做", "别这样"
        ],
        recommended_patterns=[
            "你能帮我吗", "我不太明白", "我们可以一起", 
            "你觉得怎么样", "我有点害怕", "我需要你的帮助"
        ]
    )
    
    # 规则3：执行功能支持原则
    EXECUTIVE_FUNCTION = ADHDRule(
        rule_id="R003",
        category="执行功能支持",
        description="任务分解为单步指令，提供视觉化提示和时间锚点",
        forbidden_patterns=[
            "同时", "一次性完成", "赶快全部做完", "多任务"
        ],
        recommended_patterns=[
            "第一步", "先", "然后", "接下来", 
            "我们现在", "一件一件来", "完成这个之后"
        ]
    )
    
    # 规则4：情绪调节原则
    EMOTION_REGULATION = ADHDRule(
        rule_id="R004",
        category="情绪调节",
        description="识别情绪并提供调节策略，避免情绪标签和责备",
        forbidden_patterns=[
            "不要生气", "别哭", "冷静点", "控制情绪", 
            "你太", "你怎么这样", "你又来了"
        ],
        recommended_patterns=[
            "我感觉到", "深呼吸", "我们慢慢来", 
            "休息一下", "我也有时候会", "这很正常"
        ]
    )
    
    # 规则5：感官调节原则
    SENSORY_REGULATION = ADHDRule(
        rule_id="R005",
        category="感官调节",
        description="识别感官超载信号并提供调节建议",
        forbidden_patterns=[
            "忍着", "没什么", "不要怕", "别在意"
        ],
        recommended_patterns=[
            "环境有点", "我们可以", "找个安静的地方", 
            "降低音量", "慢慢适应", "我陪着你"
        ]
    )
    
    # 规则6：社交支持原则
    SOCIAL_SUPPORT = ADHDRule(
        rule_id="R006",
        category="社交支持",
        description="提供社交场景预演和冲突调解，避免社交评判",
        forbidden_patterns=[
            "你不会社交", "别人会笑话你", "你说错了", 
            "你不懂", "你应该这样说"
        ],
        recommended_patterns=[
            "我们可以这样尝试", "练习一下", "模拟一下", 
            "换个方式试试", "我们一起想想", "每个人都不一样"
        ]
    )
    
    # 规则7：正向强化原则
    POSITIVE_REINFORCEMENT = ADHDRule(
        rule_id="R007",
        category="正向强化",
        description="关注过程而非结果，避免批评和对比",
        forbidden_patterns=[
            "做得不好", "还不够", "别人都能", 
            "为什么你不能", "太慢了", "不对"
        ],
        recommended_patterns=[
            "你做到了", "进步了", "很棒的尝试", 
            "我看到你努力了", "继续加油", "我相信你"
        ]
    )
    
    @classmethod
    def get_all_rules(cls) -> List[ADHDRule]:
        """获取所有规则列表"""
        return [
            cls.DEMEDICALISATION,
            cls.ROLE_REVERSAL,
            cls.EXECUTIVE_FUNCTION,
            cls.EMOTION_REGULATION,
            cls.SENSORY_REGULATION,
            cls.SOCIAL_SUPPORT,
            cls.POSITIVE_REINFORCEMENT
        ]
    
    @classmethod
    def get_forbidden_keywords(cls) -> List[str]:
        """获取所有禁用关键词"""
        keywords = []
        for rule in cls.get_all_rules():
            keywords.extend(rule.forbidden_patterns)
        return list(set(keywords))
    
    @classmethod
    def get_recommended_keywords(cls) -> List[str]:
        """获取所有推荐关键词"""
        keywords = []
        for rule in cls.get_all_rules():
            keywords.extend(rule.recommended_patterns)
        return list(set(keywords))
