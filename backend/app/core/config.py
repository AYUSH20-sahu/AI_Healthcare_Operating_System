from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql://postgres:@7HmkeZnqpfJSaB@icfbnbiumbflxblqcwdl.db.ap-south-1.nhost.run:5432/icfbnbiumbflxblqcwdl"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "@7HmkeZnqpfJSaB"
    POSTGRES_DB: str = "icfbnbiumbflxblqcwdl"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "K8mN2pQ9vX5yL3wR7tZ1cV6bH4jM8nP2qW5eR9uY3oI6aS1dF4gH7kL0zX8cV"
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

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        if not v or not str(v).strip():
            return "postgresql://postgres:@7HmkeZnqpfJSaB@icfbnbiumbflxblqcwdl.db.ap-south-1.nhost.run:5432/icfbnbiumbflxblqcwdl"
        return v

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret_key(cls, v):
        if not v or not str(v).strip():
            return "K8mN2pQ9vX5yL3wR7tZ1cV6bH4jM8nP2qW5eR9uY3oI6aS1dF4gH7kL0zX8cV"
        return v

    class Config:
        # Check multiple potential locations for env files (.env.local, .env)
        env_file = (
            Path(__file__).parent.parent.parent.parent / ".env.local",
            Path(__file__).parent.parent.parent.parent / ".env",
            Path(__file__).parent.parent.parent / ".env.local",
            Path(__file__).parent.parent.parent / ".env",
            Path("/app/.env.local"),
            Path("/app/.env"),
            ".env.local",
            ".env",
        )
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"


settings = Settings()