import requests
from typing import Optional, Dict, List, Any
import streamlit as st

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Any]:
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.HTTPError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}
    
    def health_check(self) -> bool:
        result = self._request("GET", "/api/health")
        return result is not None and "error" not in result
    
    def process_audio(self, audio_file, profile: str, session_id: Optional[str] = None, 
                      language: str = "zh", tts_engine: Optional[str] = None, 
                      llm_engine: Optional[str] = None) -> Optional[Dict]:
        files = {"audio": audio_file}
        data = {"profile": profile, "language": language}
        if session_id:
            data["session_id"] = session_id
        if tts_engine:
            data["tts_engine"] = tts_engine
        if llm_engine:
            data["llm_engine"] = llm_engine
        return self._request("POST", "/api/audio/process", files=files, data=data)
    
    def list_profiles(self) -> List[Dict]:
        result = self._request("GET", "/api/profiles")
        return result if isinstance(result, list) else []
    
    def create_profile(self, profile_data: Dict) -> Optional[Dict]:
        return self._request("POST", "/api/profiles", json=profile_data)
    
    def get_profile(self, profile_id: str) -> Optional[Dict]:
        return self._request("GET", f"/api/profiles/{profile_id}")
    
    def update_profile(self, profile_id: str, profile_data: Dict) -> Optional[Dict]:
        return self._request("PUT", f"/api/profiles/{profile_id}", json=profile_data)
    
    def set_default_profile(self, profile_id: str) -> Optional[Dict]:
        return self._request("POST", f"/api/profiles/{profile_id}/set-default")
    
    def publish_profile(self, profile_id: str) -> Optional[Dict]:
        return self._request("POST", f"/api/profiles/{profile_id}/publish")
    
    def list_setups(self) -> List[Dict]:
        result = self._request("GET", "/api/setups")
        return result if isinstance(result, list) else []
    
    def create_setup(self, name: str, description: Optional[str] = None) -> Optional[Dict]:
        data = {"name": name}
        if description:
            data["description"] = description
        return self._request("POST", "/api/setups", json=data)
    
    def get_setup(self, setup_id: str) -> Optional[Dict]:
        return self._request("GET", f"/api/setups/{setup_id}")
    
    def add_variant(self, setup_id: str, variant_data: Dict) -> Optional[Dict]:
        return self._request("POST", f"/api/setups/{setup_id}/variants", json=variant_data)
    
    def get_setup_stats(self, setup_id: str) -> Optional[Dict]:
        return self._request("GET", f"/api/setups/{setup_id}/stats")
    
    def get_setup_sessions(self, setup_id: str) -> List[Dict]:
        result = self._request("GET", f"/api/setups/{setup_id}/sessions")
        return result if isinstance(result, list) else []
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        result = self._request("GET", f"/api/sessions/{session_id}/messages")
        return result if isinstance(result, list) else []
    
    def list_openrouter_models(self) -> List[Dict]:
        result = self._request("GET", "/api/openrouter/models")
        return result if isinstance(result, list) else []
    
    def list_lmstudio_models(self) -> List[Dict]:
        result = self._request("GET", "/api/lmstudio/models")
        return result if isinstance(result, list) else []
    
    def list_avatars(self) -> List[Dict]:
        result = self._request("GET", "/api/avatars")
        return result if isinstance(result, list) else []
    
    def upload_avatar(self, avatar_file) -> Optional[Dict]:
        files = {"avatar": avatar_file}
        return self._request("POST", "/api/avatars", files=files)
