"""
Ascendra — Application Configuration.

All settings are loaded from environment variables via Pydantic BaseSettings.
Never hardcode secrets. Never import os.getenv directly in business code.
"""

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — single source of truth for all env vars."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "resumes"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── AI Provider ───────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # ── Email (SMTP) ──────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    # ── Google OAuth (Gmail API for sending + login) ────────────
    GOOGLE_CLIENT_ID: str = Field(default="", validation_alias=AliasChoices("GOOGLE_CLIENT_ID", "Client_ID"))
    GOOGLE_CLIENT_SECRET: str = Field(default="", validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET", "Client_secret"))

    # ── Job Providers & Contact Discovery ──────────────────────
    HUNTER_API_KEY: str = ""
    SERPAPI_KEY: str = Field(default="", validation_alias=AliasChoices("SERPAPI_KEY", "SERP_API_KEY", "SerpApi", "SERPAPI"))

    # ── Application ───────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url:
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # Supabase pooler strings often include ?pgbouncer=true, which asyncpg rejects
            if "?pgbouncer=true" in url:
                url = url.replace("?pgbouncer=true", "")
            elif "&pgbouncer=true" in url:
                url = url.replace("&pgbouncer=true", "")
        return url


settings = Settings()
