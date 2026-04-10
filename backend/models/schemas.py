from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EmotionColor(str, Enum):
    green = "green"
    yellow = "yellow"
    red = "red"

class ProfileConfig(BaseModel):
    system_prompt: str
    llm_backend: str = "anthropic/claude-sonnet-4"
    tts_engine: Optional[str] = "openai"
    voice_id: Optional[str] = None
    voice_speed: float = 1.0
    language: str = "zh"
    temperature: float = 0.7
    max_tokens: int = 500
    safety_rules: Optional[Dict[str, Any]] = None

class ProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    config: ProfileConfig

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[ProfileConfig] = None
    is_default: Optional[bool] = None

class Profile(ProfileCreate):
    id: str
    is_default: bool = False
    is_published: bool = False
    created_at: datetime
    updated_at: datetime

class VariantCreate(BaseModel):
    name: str
    profile_id: str
    description: Optional[str] = None

class Variant(VariantCreate):
    id: str
    url: str
    session_count: int = 0
    created_at: datetime

class SetupCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Setup(SetupCreate):
    id: str
    variants: List[Variant] = []
    created_at: datetime
    updated_at: datetime

class SetupStats(BaseModel):
    setup_id: str
    total_sessions: int
    total_messages: int
    avg_response_length: float
    safety_triggers: int
    variant_stats: Dict[str, Any]

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime

class Session(BaseModel):
    id: str
    profile_id: Optional[str] = None
    variant_id: Optional[str] = None
    messages: List[Message] = []
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class AudioProcessResponse(BaseModel):
    audio_url: Optional[str] = None
    text: Dict[str, str]
    session_id: str
    emotion_color: EmotionColor = EmotionColor.green

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: Optional[str] = None
    context_length: Optional[int] = None
    pricing: Optional[Dict[str, float]] = None

class HealthStatus(BaseModel):
    status: str
    version: str
    uptime: float
    services: Dict[str, bool]
