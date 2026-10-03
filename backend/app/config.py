import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_region: str = os.getenv("GOOGLE_CLOUD_REGION", "")
    vertex_gemini_model: str = os.getenv("VERTEX_GEMINI_MODEL", "gemini-2.5-flash")

    class Config:
        env_file = ".env"

settings = Settings()
