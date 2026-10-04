import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "AI Nutrition & Energy Balance Coach"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database: SQLite fallback or PostgreSQL+pgvector
    DATABASE_URL: str = "sqlite:///./nutrition_dev.db"

    # Security & Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # AI Coach & LLM Configuration
    LLM_PROVIDER: str = "openrouter"
    LLM_API_KEY: Optional[str] = ""
    LLM_API_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "openai/gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.2

    # Embeddings / Vector search
    EMBEDDING_PROVIDER: str = "cosine_tfidf"  # "gemini", "openai", "sentence_transformers", "cosine_tfidf"
    EMBEDDING_API_KEY: Optional[str] = ""
    EMBEDDING_MODEL: str = "text-embedding-004"

    # Speech-to-Text
    STT_PROVIDER: str = "native_android"  # "native_android", "gemini_audio", "whisper_api"
    STT_API_KEY: Optional[str] = ""

    # Dataset directory
    INDB_DATASET_DIR: str = str(PROJECT_ROOT / "DATASET" / "INDB")

    # Proactive Reminders & Quiet Hours
    DEFAULT_QUIET_HOURS_START: str = "22:00"
    DEFAULT_QUIET_HOURS_END: str = "07:00"
    DEFAULT_BREAKFAST_REMINDER_TIME: str = "09:30"
    DEFAULT_LUNCH_REMINDER_TIME: str = "14:00"
    DEFAULT_DINNER_REMINDER_TIME: str = "21:00"

    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        extra = "ignore"

settings = Settings()
