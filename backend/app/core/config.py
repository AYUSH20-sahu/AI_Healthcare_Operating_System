from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ai_hos"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_hos"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "dev_jwt_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = None
    LLM_MODEL: str | None = None

    # Voice
    WHISPER_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str | None = None

    # ABDM/FHIR
    ABDM_CLIENT_ID: str | None = None
    ABDM_CLIENT_SECRET: str | None = None
    FHIR_BASE_URL: str = "https://hapi.fhir.org/baseR4"

    # Monitoring
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"

    # Frontend
    NEXT_PUBLIC_API_URL: str | None = None
    NEXT_PUBLIC_APP_URL: str | None = None

    class Config:
        # Find .env.local in project root (parent of backend/)
        env_file = Path(__file__).parent.parent.parent.parent / ".env.local"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"


settings = Settings()