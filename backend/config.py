"""
Central application configuration.

All settings are read from environment variables (or a local `.env` file) and
validated once at import time. Import the singleton `settings` everywhere else:

    from config import settings
    settings.OPENAI_API_KEY
"""
from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- OpenAI ----
    OPENAI_API_KEY: str
    OPENAI_INTENT_MODEL: str = "gpt-4o-mini"
    OPENAI_VISION_MODEL: str = "gpt-4o"

    # ---- Supabase ----
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_PRESCRIPTION_BUCKET: str = "prescriptions"

    # ---- Razorpay ----
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ---- Supabase order-status webhook ----
    # Optional shared secret; if set, the Supabase DB webhook must send it in the
    # `x-webhook-secret` header (configured as a custom header in the dashboard).
    SUPABASE_WEBHOOK_SECRET: str = ""

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379"

    # ---- Google Maps (optional) ----
    GOOGLE_MAPS_KEY: str = ""

    # ---- App / server ----
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    # NoDecode stops pydantic-settings from JSON-decoding the env value; the
    # validator below splits a plain comma-separated string into a list.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # ---- Business rules ----
    DELIVERY_MIN_ORDER: float = 1000.0
    DELIVERY_CHARGE_COD: float = 40.0
    DELIVERY_CHARGE_ONLINE: float = 20.0

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        """Accept a comma-separated string from the env and split into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def razorpay_enabled(self) -> bool:
        return bool(self.RAZORPAY_KEY_ID and self.RAZORPAY_KEY_SECRET)


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()
