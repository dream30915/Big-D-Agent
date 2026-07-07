"""Typed application settings, loaded from environment / .env.

Everything the app needs is read here once and shared. Missing-but-required
values (like the Telegram token) fail loudly at startup rather than deep inside
a request.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Telegram ---
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_id: int = Field(default=0, alias="TELEGRAM_ADMIN_ID")

    # --- OpenRouter ---
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model_fast: str = Field(
        default="openai/gpt-4o-mini", alias="OPENROUTER_MODEL_FAST"
    )
    openrouter_model_quality: str = Field(
        default="anthropic/claude-3.5-sonnet", alias="OPENROUTER_MODEL_QUALITY"
    )
    openrouter_app_url: str = Field(
        default="https://github.com/dream30915/big-d-agent",
        alias="OPENROUTER_APP_URL",
    )
    openrouter_app_name: str = Field(default="Big-D-Agent", alias="OPENROUTER_APP_NAME")

    # --- Infra ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:changeme@postgres:5432/big_d_agent",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # --- n8n ---
    n8n_webhook_url: str = Field(default="", alias="N8N_WEBHOOK_URL")
    n8n_api_key: str = Field(default="", alias="N8N_API_KEY")

    # --- Bot ---
    environment: str = Field(default="production", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Feature flags ---
    enable_multi_agent: bool = Field(default=False, alias="ENABLE_MULTI_AGENT")
    enable_marketplace: bool = Field(default=False, alias="ENABLE_MARKETPLACE")
    enable_self_optimization: bool = Field(
        default=False, alias="ENABLE_SELF_OPTIMIZATION"
    )
    enable_ethics_module: bool = Field(default=True, alias="ENABLE_ETHICS_MODULE")

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token) and self.telegram_bot_token != (
            "your_bot_token_here"
        )

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key) and self.openrouter_api_key != (
            "your_openrouter_key_here"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so every module reads the same config."""
    return Settings()
