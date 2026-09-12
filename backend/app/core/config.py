from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database - local standard PostgreSQL default, overridable via DATABASE_URL env var
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_hos"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_hos"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT - Required secret key (override in production via JWT_SECRET_KEY env var)
    JWT_SECRET_KEY: str = "dev_insecure_jwt_secret_change_in_production_min64chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Super Admin Privilege Boundary (SEC-06)
    SUPER_ADMIN_EMAIL: str = "admin@test.com"

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
    ABDM_BASE_URL: str = "https://dev.abdm.gov.in/gateway"
    ABDM_SANDBOX_MODE: bool = True
    HFR_FACILITY_ID: str = "IN-DL-AIHOS-001"
    HFR_FACILITY_NAME: str = "AI-HOS Apex Clinical Center"
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
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_hos"
        # Convert plain postgres:// or postgresql:// to postgresql+asyncpg:// for async engine
        v_str = str(v).strip()
        if v_str.startswith("postgres://"):
            return v_str.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v_str.startswith("postgresql://") and not v_str.startswith("postgresql+asyncpg://"):
            return v_str.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v_str

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret_key(cls, v):
        if not v or not str(v).strip():
            return "dev_insecure_jwt_secret_change_in_production_min64chars"
        return str(v).strip()

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.APP_ENV == "production":
            insecure_defaults = [
                "aihos_dev_jwt_secret_key_change_in_production_min32chars!",
                "dev_insecure_jwt_secret_change_in_production_min32chars",
                "dev_insecure_jwt_secret_change_in_production_min64chars",
                "test_secret_key",
            ]
            if (
                not self.JWT_SECRET_KEY
                or len(self.JWT_SECRET_KEY) < 32
                or any(self.JWT_SECRET_KEY.startswith(d) for d in insecure_defaults)
            ):
                raise ValueError("JWT_SECRET_KEY must be set to a strong secret in production")
        return self

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