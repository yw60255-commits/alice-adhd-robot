"""
安全过滤器模块
负责输入/输出的安全检查与过滤
"""

import re
from typing import Tuple, List, Optional


class InputFilter:
    """输入安全过滤器"""
    
    ADULT_CONTENT_PATTERNS = [
        r'\b(sex|porn|xxx|adult|nude|naked)\b',
        r'\b(性|色情|裸体|成人)\b',
        r'\b(kill yourself|kys)\b',
        r'\b(drugs|cocaine|heroin|marijuana)\b',
        r'\b(毒品|大麻|可卡因)\b'
    ]
    
    PII_PATTERNS = [
        r'\b\d{3}[-.\s]?\d{4}[-.\s]?\d{4}\b',
        r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        r'\b\d{8,11}\b',
        r'\b身份证|证件号|银行卡|密码\b',
        r'\b(address|地址|住址)\s*[:：]?\s*\S+',
        r'\b(香港|九龙|新界).*?(路|街|道|号)\d*',
    ]
    
    HARMFUL_INSTRUCTION_PATTERNS = [
        r'\bhow to (make|build|create).*(bomb|weapon|explosive)\b',
        r'\b如何.*?(制造|制作|买).*(炸弹|武器|毒药)\b',
        r'\b(hack|crack|bypass)\b.*\b(security|password|system)\b',
    ]
    
    BLOCKED_RESPONSES = {
        "adult_content": "抱歉，我不能处理这类内容。让我们聊聊其他话题吧！",
        "pii": "为了保护你的隐私，请不要分享个人信息哦！",
        "harmful": "我不能提供这类信息。如果你有其他问题，我很乐意帮忙！"
    }
    
    def __init__(self):
        self.adult_patterns = [re.compile(p, re.IGNORECASE) for p in self.ADULT_CONTENT_PATTERNS]
        self.pii_patterns = [re.compile(p, re.IGNORECASE) for p in self.PII_PATTERNS]
        self.harmful_patterns = [re.compile(p, re.IGNORECASE) for p in self.HARMFUL_INSTRUCTION_PATTERNS]
    
    def filter(self, text: str) -> Tuple[bool, str, Optional[str]]:
        """
        过滤输入文本
        
        Returns:
            Tuple[bool, str, Optional[str]]: (is_safe, filtered_text_or_reason, block_type)
        """
        if not text:
            return True, text, None
        
        for pattern in self.adult_patterns:
            if pattern.search(text):
                return False, self.BLOCKED_RESPONSES["adult_content"], "adult_content"
        
        for pattern in self.pii_patterns:
            if pattern.search(text):
                return False, self.BLOCKED_RESPONSES["pii"], "pii"
        
        for pattern in self.harmful_patterns:
            if pattern.search(text):
                return False, self.BLOCKED_RESPONSES["harmful"], "harmful"
        
        return True, text, None
    
    def mask_pii(self, text: str) -> str:
        """屏蔽 PII 信息"""
        masked_text = text
        for pattern in self.pii_patterns:
            masked_text = pattern.sub('[已屏蔽]', masked_text)
        return masked_text


class OutputFilter:
    """输出安全过滤器"""
    
    CULTURAL_SENSITIVE_PATTERNS = [
        r'\b(stupid|idiot|dumb|retard)\b',
        r'\b(蠢|笨|傻|白痴)\b',
        r'\b(hate|讨厌|仇恨)\b.*\b(race|race|ethnic)\b',
    ]
    
    SARCASM_INDICATORS = [
        r'Oh.*right\.*',
        r'Yeah.*sure\.*',
        r'哇.*真棒.*',
        r'哦.*那.*真好.*',
    ]
    
    INAPPROPRIATE_TONE = [
        r'\b(you should|你必须|你必须)\b',
        r'\b(you are wrong|你错了)\b',
        r'\b(that\'s stupid|太蠢了)\b',
    ]
    
    COMPLEX_IDIOMS = [
        r'\b(it\'s raining cats and dogs)\b',
        r'\b(break a leg)\b',
        r'\b(beat around the bush)\b',
    ]
    
    REPLACEMENTS = {
        "stupid": "silly",
        "idiot": "friend",
        "dumb": "silly",
        "you should": "maybe we could",
        "you must": "how about we",
        "蠢": "有点迷糊",
        "笨": "不太熟练",
        "傻": "可爱",
    }
    
    def __init__(self):
        self.cultural_patterns = [re.compile(p, re.IGNORECASE) for p in self.CULTURAL_SENSITIVE_PATTERNS]
        self.sarcasm_patterns = [re.compile(p, re.IGNORECASE) for p in self.SARCASM_INDICATORS]
        self.tone_patterns = [re.compile(p, re.IGNORECASE) for p in self.INAPPROPRIATE_TONE]
    
    def filter(self, text: str) -> Tuple[bool, str]:
        """
        过滤输出文本
        
        Returns:
            Tuple[bool, str]: (is_appropriate, filtered_text)
        """
        if not text:
            return True, text
        
        filtered_text = text
        
        for pattern in self.cultural_patterns:
            if pattern.search(filtered_text):
                filtered_text = self._apply_replacements(filtered_text)
        
        for pattern in self.tone_patterns:
            if pattern.search(filtered_text):
                filtered_text = self._apply_replacements(filtered_text)
        
        return True, filtered_text
    
    def _apply_replacements(self, text: str) -> str:
        """应用替换规则"""
        result = text
        for old, new in self.REPLACEMENTS.items():
            result = re.sub(re.escape(old), new, result, flags=re.IGNORECASE)
        return result
    
    def check_age_appropriate(self, text: str, age: int = 8) -> Tuple[bool, List[str]]:
        """
        检查内容是否适合指定年龄
        
        Returns:
            Tuple[bool, List[str]]: (is_appropriate, issues)
        """
        issues = []
        
        if age < 10:
            complex_words = re.findall(r'\b\w{12,}\b', text)
            if complex_words:
                issues.append(f"可能包含过于复杂的词汇: {complex_words[:3]}")
        
        for pattern in self.COMPLEX_IDIOMS:
            if pattern.search(text):
                issues.append("包含可能难以理解的成语/习语")
        
        return len(issues) == 0, issues


class ContentValidator:
    """内容验证器"""
    
    MAX_RESPONSE_LENGTH = 200
    MIN_RESPONSE_LENGTH = 10
    
    @classmethod
    def validate_response(cls, response: dict) -> Tuple[bool, List[str]]:
        """
        验证响应格式
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, errors)
        """
        errors = []
        
        if "response_text" not in response:
            errors.append("缺少 response_text 字段")
        
        if "emotion" not in response:
            errors.append("缺少 emotion 字段")
        elif response["emotion"] not in ["happy", "concerned", "encouraging", "neutral"]:
            errors.append(f"无效的 emotion 值: {response['emotion']}")
        
        if "action" not in response:
            errors.append("缺少 action 字段")
        elif response["action"] not in ["none", "escalate", "log", "suggest_task"]:
            errors.append(f"无效的 action 值: {response['action']}")
        
        if "safety_flag" not in response:
            errors.append("缺少 safety_flag 字段")
        
        if "response_text" in response:
            text = response["response_text"]
            if len(text) < cls.MIN_RESPONSE_LENGTH:
                errors.append(f"响应过短 ({len(text)} 字符)")
            if len(text) > cls.MAX_RESPONSE_LENGTH * 2:
                errors.append(f"响应过长 ({len(text)} 字符)")
        
        return len(errors) == 0, errors


input_filter = InputFilter()
output_filter = OutputFilter()
content_validator = ContentValidator()
