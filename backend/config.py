import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "z-ai/glm-5-turbo")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./alice_backend.db")
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")

SECRET_KEY = os.getenv("SECRET_KEY", "alice-adhd-companion-secret-key-2024")
