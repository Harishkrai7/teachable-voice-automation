import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "teachable-voice-automation")
    google_cloud_region: str = os.getenv("GOOGLE_CLOUD_REGION", "global")
    vertex_gemini_model: str = os.getenv("VERTEX_GEMINI_MODEL", "gemini-1.5-flash-002")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
