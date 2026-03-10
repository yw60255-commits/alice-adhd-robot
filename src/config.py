import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 智谱AI配置（兼容OpenAI接口格式）
OPENAI_API_KEY = os.getenv("ZHIPU_API_KEY")  # 改为读取ZHIPU_API_KEY
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://open.bigmodel.cn/api/paas/v4/")  # 新增base_url
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "glm-4")  # 改为glm-4
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 500))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))

# 验证API密钥是否存在
if not OPENAI_API_KEY:
    raise ValueError("错误：未找到ZHIPU_API_KEY，请检查.env文件")

print(f"✅ 配置加载成功：模型={OPENAI_MODEL}, API Base={OPENAI_API_BASE}")
