"""
规则合规性验证器
检查LLM生成的回复是否符合ADHD循证干预规则
"""

from typing import Dict, List
from src.adhd_rules import ADHDRules

class RuleValidator:
    """ADHD规则验证器"""
    
    def __init__(self):
        self.rules = ADHDRules.get_all_rules()
        self.forbidden_keywords = ADHDRules.get_forbidden_keywords()
        self.recommended_keywords = ADHDRules.get_recommended_keywords()
    
    def validate_response(self, response: str) -> Dict:
        """
        验证回复是否符合规则
        
        返回:
            {
                "is_compliant": bool,
                "violations": List[str],
                "suggestions": List[str],
                "score": float
            }
        """
        violations = []
        suggestions = []
        
        # 检查禁用词
        forbidden_found = []
        for keyword in self.forbidden_keywords:
            if keyword in response:
                forbidden_found.append(keyword)
                violations.append(f"使用了禁用词：{keyword}")
        
        # 检查推荐词
        recommended_found = []
        for keyword in self.recommended_keywords:
            if keyword in response:
                recommended_found.append(keyword)
        
        # 检查角色反转语气
        role_reversal_indicators = ["帮我", "你能", "我们一起", "我不知道", "我有点"]
        has_role_reversal = any(indicator in response for indicator in role_reversal_indicators)
        
        if not has_role_reversal:
            violations.append("缺少角色反转语气（未包含请求帮助的表达）")
            suggestions.append("建议增加：'你能帮我吗？' '我们一起试试？'")
        
        # 检查回复长度（应简短）
        if len(response) > 50:
            suggestions.append(f"回复过长（{len(response)}字），建议精简到50字以内")
        
        # 计算合规分数
        score = self._calculate_score(
            len(forbidden_found),
            len(recommended_found),
            has_role_reversal
        )
        
        is_compliant = len(violations) == 0 and score >= 0.7
        
        return {
            "is_compliant": is_compliant,
            "violations": violations,
            "suggestions": suggestions,
            "score": score,
            "forbidden_found": forbidden_found,
            "recommended_found": recommended_found
        }
    
    def _calculate_score(self, forbidden_count: int, recommended_count: int, has_role_reversal: bool) -> float:
        """计算合规分数（0-1）"""
        score = 1.0
        
        # 每个禁用词扣0.2分
        score -= forbidden_count * 0.2
        
        # 没有角色反转扣0.3分
        if not has_role_reversal:
            score -= 0.3
        
        # 每个推荐词加0.1分（最多+0.3）
        score += min(recommended_count * 0.1, 0.3)
        
        return max(0.0, min(1.0, score))
    
    def print_validation_report(self, response: str):
        """打印验证报告"""
        result = self.validate_response(response)
        
        print("\n" + "="*60)
        print("ADHD规则合规性验证报告")
        print("="*60)
        print(f"回复内容: {response}")
        print(f"\n合规状态: {'✅ 通过' if result['is_compliant'] else '❌ 不合规'}")
        print(f"合规分数: {result['score']:.2f}/1.00")
        
        if result['violations']:
            print(f"\n❌ 违规项 ({len(result['violations'])}个):")
            for v in result['violations']:
                print(f"   - {v}")
        
        if result['suggestions']:
            print(f"\n💡 改进建议 ({len(result['suggestions'])}个):")
            for s in result['suggestions']:
                print(f"   - {s}")
        
        if result['recommended_found']:
            print(f"\n✅ 符合推荐模式 ({len(result['recommended_found'])}个):")
            for r in result['recommended_found']:
                print(f"   - {r}")
        
        print("="*60 + "\n")
