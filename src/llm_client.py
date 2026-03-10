from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE

class LLMClient:
    """智谱AI客户端封装（兼容OpenAI接口）"""
    
    def __init__(self):
        # 关键改动：增加 base_url 参数指向智谱API
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE  # 新增：指定智谱API地址
        )
        self.model = OPENAI_MODEL
        print(f"✅ LLM客户端初始化成功，使用模型: {self.model}")
    
    def chat(self, system_prompt: str, user_message: str) -> str:
        """
        单轮对话接口
        
        参数:
            system_prompt: 系统提示词（定义机器人的角色和行为）
            user_message: 用户输入的消息
        
        返回:
            机器人的回复文本
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            return response.choices[0].message.content
        
        except Exception as e:
            return f"[错误] API调用失败: {str(e)}"
