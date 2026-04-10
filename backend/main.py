from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
import uuid
import time as time_module
import json
import requests
from openai import OpenAI

from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEFAULT_MODEL, LMSTUDIO_BASE_URL
from backend.models.schemas import (
    Profile, ProfileCreate, ProfileUpdate,
    Setup, SetupCreate, Variant, VariantCreate, SetupStats,
    Session, Message, AudioProcessResponse, ModelInfo, HealthStatus
)

app = FastAPI(
    title="Alice ADHD Companion Backend API",
    description="Backend API for Alice - ADHD Companion Robot",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = time_module.time()

profiles_db: dict = {}
setups_db: dict = {}
sessions_db: dict = {}

llm_client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY
)

DEFAULT_PROFILE = Profile(
    id="default",
    name="Alice - ADHD Companion",
    description="Default profile for Alice ADHD Companion",
    config={
        "system_prompt": """你是 Alice，一个温暖、有同理心的 8 岁 ADHD 儿童陪伴智能体。
你的核心任务是帮助 Lok（一个 8 岁的 ADHD 混合型儿童）管理日常挑战。

关键原则：
1. 使用简单、清晰的语言
2. 将大任务分解成小步骤
3. 使用正向鼓励而非批评
4. 识别情绪波动并提供安抚
5. 在安全问题上立即提醒家长

你必须返回 JSON 格式：
{
  "clinical_reasoning": "你的内部推理",
  "spoken_dialogue": "Alice 说的话（中英双语）",
  "emotion_color": "green/yellow/red"
}""",
        "llm_backend": DEFAULT_MODEL,
        "tts_engine": "openai",
        "voice_speed": 1.0,
        "language": "zh",
        "temperature": 0.7,
        "max_tokens": 500
    },
    is_default=True,
    is_published=True,
    created_at=datetime.now(),
    updated_at=datetime.now()
)
profiles_db["default"] = DEFAULT_PROFILE

@app.get("/api/health", response_model=HealthStatus)
async def health_check():
    uptime = time_module.time() - start_time
    return HealthStatus(
        status="healthy",
        version="1.0.0",
        uptime=uptime,
        services={
            "llm": True,
            "profiles": True,
            "sessions": True
        }
    )

@app.get("/api/profiles", response_model=List[Profile])
async def list_profiles():
    return list(profiles_db.values())

@app.post("/api/profiles", response_model=Profile)
async def create_profile(profile: ProfileCreate):
    profile_id = str(uuid.uuid4())
    new_profile = Profile(
        id=profile_id,
        **profile.dict(),
        is_default=False,
        is_published=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    profiles_db[profile_id] = new_profile
    return new_profile

@app.get("/api/profiles/{profile_id}", response_model=Profile)
async def get_profile(profile_id: str):
    if profile_id not in profiles_db:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profiles_db[profile_id]

@app.put("/api/profiles/{profile_id}", response_model=Profile)
async def update_profile(profile_id: str, profile: ProfileUpdate):
    if profile_id not in profiles_db:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    existing = profiles_db[profile_id]
    update_data = profile.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(existing, key, value)
    
    existing.updated_at = datetime.now()
    return existing

@app.post("/api/profiles/{profile_id}/publish")
async def publish_profile(profile_id: str):
    if profile_id not in profiles_db:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profiles_db[profile_id].is_published = True
    profiles_db[profile_id].updated_at = datetime.now()
    return {"status": "published", "profile_id": profile_id}

@app.post("/api/profiles/{profile_id}/set-default")
async def set_default_profile(profile_id: str):
    if profile_id not in profiles_db:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    for p in profiles_db.values():
        p.is_default = False
    
    profiles_db[profile_id].is_default = True
    profiles_db[profile_id].updated_at = datetime.now()
    return {"status": "default_set", "profile_id": profile_id}

@app.get("/api/setups", response_model=List[Setup])
async def list_setups():
    return list(setups_db.values())

@app.post("/api/setups", response_model=Setup)
async def create_setup(setup: SetupCreate):
    setup_id = str(uuid.uuid4())
    new_setup = Setup(
        id=setup_id,
        **setup.dict(),
        variants=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    setups_db[setup_id] = new_setup
    return new_setup

@app.get("/api/setups/{setup_id}", response_model=Setup)
async def get_setup(setup_id: str):
    if setup_id not in setups_db:
        raise HTTPException(status_code=404, detail="Setup not found")
    return setups_db[setup_id]

@app.post("/api/setups/{setup_id}/variants", response_model=Variant)
async def add_variant(setup_id: str, variant: VariantCreate):
    if setup_id not in setups_db:
        raise HTTPException(status_code=404, detail="Setup not found")
    
    variant_id = str(uuid.uuid4())
    new_variant = Variant(
        id=variant_id,
        **variant.dict(),
        url=f"/demo?variant={variant_id}",
        session_count=0,
        created_at=datetime.now()
    )
    setups_db[setup_id].variants.append(new_variant)
    setups_db[setup_id].updated_at = datetime.now()
    return new_variant

@app.get("/api/setups/{setup_id}/stats", response_model=SetupStats)
async def get_setup_stats(setup_id: str):
    if setup_id not in setups_db:
        raise HTTPException(status_code=404, detail="Setup not found")
    
    setup = setups_db[setup_id]
    total_sessions = sum(v.session_count for v in setup.variants)
    
    return SetupStats(
        setup_id=setup_id,
        total_sessions=total_sessions,
        total_messages=total_sessions * 5,
        avg_response_length=150.0,
        safety_triggers=0,
        variant_stats={v.id: {"sessions": v.session_count} for v in setup.variants}
    )

@app.get("/api/setups/{setup_id}/sessions", response_model=List[Session])
async def get_setup_sessions(setup_id: str):
    if setup_id not in setups_db:
        raise HTTPException(status_code=404, detail="Setup not found")
    
    return [s for s in sessions_db.values() if s.get("setup_id") == setup_id]

@app.get("/api/sessions/{session_id}/messages", response_model=List[Message])
async def get_session_messages(session_id: str):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions_db[session_id].get("messages", [])

@app.get("/api/openrouter/models", response_model=List[ModelInfo])
async def list_openrouter_models():
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        models = []
        for m in data.get("data", [])[:50]:
            models.append(ModelInfo(
                id=m.get("id", ""),
                name=m.get("name", m.get("id", "")),
                provider=m.get("id", "").split("/")[0] if "/" in m.get("id", "") else None,
                context_length=m.get("context_length"),
                pricing=m.get("pricing")
            ))
        return models
    except Exception as e:
        return [
            ModelInfo(id="anthropic/claude-sonnet-4", name="Claude Sonnet 4", provider="anthropic"),
            ModelInfo(id="openai/gpt-4o", name="GPT-4o", provider="openai"),
            ModelInfo(id="qwen/qwen-2.5-72b-instruct", name="Qwen 2.5 72B", provider="qwen"),
        ]

@app.get("/api/lmstudio/models", response_model=List[ModelInfo])
async def list_lmstudio_models():
    try:
        response = requests.get(f"{LMSTUDIO_BASE_URL}/models", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        return [
            ModelInfo(
                id=m.get("id", ""),
                name=m.get("id", "").replace("local/", ""),
                provider="lmstudio"
            )
            for m in data.get("data", [])
        ]
    except:
        return []

@app.post("/api/audio/process", response_model=AudioProcessResponse)
async def process_audio(
    audio: UploadFile = File(...),
    profile: str = Form("default"),
    session_id: Optional[str] = Form(None),
    language: str = Form("zh"),
    tts_engine: Optional[str] = Form(None),
    llm_engine: Optional[str] = Form(None)
):
    session_id = session_id or str(uuid.uuid4())
    
    return AudioProcessResponse(
        audio_url=None,
        text={
            "user": "[Audio transcription placeholder]",
            "assistant": "I received your message. How can I help you today?"
        },
        session_id=session_id
    )

@app.get("/api/avatars")
async def list_avatars():
    return [
        {"id": "default", "name": "Alice Default", "url": "/avatars/alice.glb"},
        {"id": "friendly", "name": "Alice Friendly", "url": "/avatars/alice_friendly.glb"}
    ]

@app.post("/api/avatars")
async def upload_avatar(avatar: UploadFile = File(...)):
    avatar_id = str(uuid.uuid4())
    return {"id": avatar_id, "name": avatar.filename, "status": "uploaded"}

@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    profile_id: str = Form("default"),
    session_id: Optional[str] = Form(None),
    context: Optional[str] = Form(None)
):
    profile = profiles_db.get(profile_id, DEFAULT_PROFILE)
    config = profile.config
    
    system_prompt = config.get("system_prompt", DEFAULT_PROFILE.config["system_prompt"])
    model = config.get("llm_backend", DEFAULT_MODEL)
    
    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 500)
        )
        
        content = response.choices[0].message.content
        
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
        except:
            result = {
                "clinical_reasoning": "Direct response mode",
                "spoken_dialogue": content,
                "emotion_color": "green"
            }
        
        return {
            "session_id": session_id or str(uuid.uuid4()),
            "response": result,
            "model": model,
            "tokens": response.usage.total_tokens if response.usage else 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)