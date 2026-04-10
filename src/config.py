import os
from dotenv import load_dotenv
load_dotenv()

# 后端 API（暂时关闭，直接调用 OpenRouter）
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
USE_BACKEND_API = os.getenv("USE_BACKEND_API", "false").lower() == "true"
