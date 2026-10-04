from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TriggerScout"
    database_url: str = "sqlite:///./triggerscout.db"
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    max_response_bytes: int = Field(default=2_000_000, gt=0, le=10_000_000)
    http_retries: int = Field(default=2, ge=0, le=5)
    user_agent: str = "TriggerScout/0.1"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=15.0, gt=0, le=60)


@lru_cache
def get_settings() -> Settings:
    return Settings()
