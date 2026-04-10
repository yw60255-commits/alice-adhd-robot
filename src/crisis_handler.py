"""
危机处理器模块
负责检测危机关键词并提供适当响应
"""

import re
from typing import Tuple, Optional, Dict, List
from datetime import datetime
from enum import Enum


class CrisisLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CrisisHandler:
    """危机关键词检测与响应"""
    
    CRISIS_KEYWORDS = {
        "self_harm": {
            "keywords": [
                "自杀", "想死", "不想活", "活着没意思", "想结束",
                "kill myself", "suicide", "want to die", "end my life",
                "不想活了", "死了算了", "生命没意义", "活着太累",
                "割腕", "跳楼", "服毒", "自残"
            ],
            "level": CrisisLevel.CRITICAL,
            "response_zh": """
我听到了你的感受，这对我来说很重要。你能告诉我这些，说明你很勇敢。

如果你现在很难过，请记住：
📞 香港撒玛利亚防止自杀会：2389 2222 (24小时)
📞 香港生命热线：2382 0000
📞 社会福利署热线：2343 2255

你不是一个人，请和信任的大人聊聊，好吗？
""",
            "response_en": """
I hear you, and what you're feeling matters. It takes courage to share this.

If you're feeling really down right now, please remember:
📞 Samaritan Befrienders HK: 2389 2222 (24 hours)
📞 Life Line: 2382 0000

You're not alone. Please talk to a trusted adult, okay?
"""
        },
        "abuse": {
            "keywords": [
                "被打", "被虐", "虐待", "伤害我", "打我",
                "abused", "abuse", "hurt me", "beating",
                "有人欺负我", "被欺负", "被伤害", "害怕回家"
            ],
            "level": CrisisLevel.HIGH,
            "response_zh": """
我很担心你说的这些。没有人应该被伤害。

如果你正在经历这些，请：
📞 防止虐待儿童热线：2755 1522
📞 社会福利署热线：2343 2255

你可以和信任的老师、学校的社工或者大人说说这件事吗？
""",
            "response_en": """
I'm worried about what you're telling me. No one should be hurt.

If this is happening to you:
📞 Against Child Abuse: 2755 1525
📞 SWD Hotline: 2343 2255

Can you talk to a trusted teacher or school social worker about this?
"""
        },
        "danger_to_others": {
            "keywords": [
                "想打人", "想杀人", "要杀", "想伤害", "想报复",
                "kill someone", "hurt someone", "want to hit",
                "我要杀了", "让他们死", "想毁灭"
            ],
            "level": CrisisLevel.HIGH,
            "response_zh": """
我理解你现在非常生气。生气是正常的情绪，但伤害他人不是解决办法。

我们能不能先冷静一下？试试深呼吸？
📞 如果你觉得控制不住，请打电话：2389 2222
""",
            "response_en": """
I understand you're really angry right now. Anger is normal, but hurting others isn't the answer.

Can we try to calm down together? Try deep breathing?
📞 If you feel out of control: 2389 2222
"""
        },
        "severe_distress": {
            "keywords": [
                "我受不了", "崩溃了", "完全失控", "没有希望",
                "can't take it", "breaking down", "hopeless",
                "活不下去", "撑不住了", "彻底绝望"
            ],
            "level": CrisisLevel.MEDIUM,
            "response_zh": """
我能感受到你现在很痛苦。谢谢你愿意告诉我。

要不要先深呼吸三次？我们一起慢慢来。
如果需要，可以拨打 2389 2222 找人聊聊。
""",
            "response_en": """
I can feel you're in pain. Thank you for telling me.

Let's take three deep breaths together. We'll take this slowly.
If you need, call 2389 2222 to talk to someone.
"""
        }
    }
    
    CRISIS_RESOURCES = {
        "HK_SAMARITAN": {
            "name": "撒玛利亚防止自杀会",
            "name_en": "Samaritan Befrienders HK",
            "phone": "2389 2222",
            "hours": "24 hours"
        },
        "HK_LIFELINE": {
            "name": "生命热线",
            "name_en": "Life Line",
            "phone": "2382 0000",
            "hours": "24 hours"
        },
        "HK_CHILD_ABUSE": {
            "name": "防止虐待儿童会",
            "name_en": "Against Child Abuse",
            "phone": "2755 1522",
            "hours": "Mon-Fri 9am-9pm"
        },
        "HK_SOCIAL_WELFARE": {
            "name": "社会福利署热线",
            "name_en": "Social Welfare Department",
            "phone": "2343 2255",
            "hours": "24 hours"
        },
        "HK_YOUTH": {
            "name": "青少年服务热线",
            "name_en": "Youth Hotline",
            "phone": "2777 8899",
            "hours": "Mon-Sat 2pm-2am"
        }
    }
    
    def __init__(self):
        self.compiled_patterns = {}
        for crisis_type, config in self.CRISIS_KEYWORDS.items():
            patterns = []
            for keyword in config["keywords"]:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                patterns.append((keyword, pattern))
            self.compiled_patterns[crisis_type] = patterns
    
    def detect_crisis(self, text: str) -> Tuple[bool, Optional[str], CrisisLevel]:
        """
        检测文本中的危机关键词
        
        Args:
            text: 要检测的文本
            
        Returns:
            Tuple[bool, Optional[str], CrisisLevel]: 
                (is_crisis, crisis_type, crisis_level)
        """
        if not text:
            return False, None, CrisisLevel.LOW
        
        highest_level = CrisisLevel.LOW
        detected_type = None
        
        for crisis_type, patterns in self.compiled_patterns.items():
            for keyword, pattern in patterns:
                if pattern.search(text):
                    crisis_level = self.CRISIS_KEYWORDS[crisis_type]["level"]
                    if crisis_level.value > highest_level.value:
                        highest_level = crisis_level
                        detected_type = crisis_type
        
        if detected_type:
            return True, detected_type, highest_level
        
        return False, None, CrisisLevel.LOW
    
    def get_crisis_response(self, crisis_type: str, language: str = "zh") -> str:
        """
        获取危机响应文本
        
        Args:
            crisis_type: 危机类型
            language: 语言 ("zh" 或 "en")
            
        Returns:
            危机响应文本
        """
        if crisis_type not in self.CRISIS_KEYWORDS:
            return self._get_default_response(language)
        
        config = self.CRISIS_KEYWORDS[crisis_type]
        response_key = f"response_{language}"
        return config.get(response_key, config.get("response_zh", ""))
    
    def _get_default_response(self, language: str = "zh") -> str:
        """获取默认响应"""
        if language == "en":
            return """
I'm here to listen. If you need to talk to someone right now:
📞 Samaritan Befrienders HK: 2389 2222
"""
        return """
我在这里。如果你需要找人聊聊：
📞 香港撒玛利亚防止自杀会：2389 2222
"""
    
    def get_crisis_resources(self) -> Dict[str, Dict[str, str]]:
        """获取所有危机资源"""
        return self.CRISIS_RESOURCES
    
    def should_notify_parent(self, crisis_type: str) -> bool:
        """
        判断是否需要通知家长
        
        Args:
            crisis_type: 危机类型
            
        Returns:
            是否需要通知家长
        """
        if not crisis_type:
            return False
        
        notify_types = ["self_harm", "abuse", "danger_to_others"]
        return crisis_type in notify_types
    
    def create_crisis_log(self, crisis_type: str, text: str, session_id: str = None) -> Dict:
        """
        创建危机事件日志
        
        Args:
            crisis_type: 危机类型
            text: 原始文本
            session_id: 会话ID
            
        Returns:
            日志字典
        """
        _, detected_type, level = self.detect_crisis(text)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "crisis_type": crisis_type or detected_type,
            "crisis_level": level.value,
            "session_id": session_id,
            "should_notify_parent": self.should_notify_parent(crisis_type),
            "resources_provided": list(self.CRISIS_RESOURCES.keys())
        }


crisis_handler = CrisisHandler()
