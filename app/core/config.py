"""Application configuration for InsightIQ.

Settings are read from environment variables prefixed with ``INSIGHTIQ_`` and,
optionally, from a local ``.env`` file anchored at the repository root. Real
environment variables take precedence over values in ``.env``. Use
``get_settings()`` (or the shared ``settings`` alias) to access configuration.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Typed InsightIQ settings with safe local-development defaults."""

    model_config = SettingsConfigDict(
        env_prefix="INSIGHTIQ_",
        env_file=_DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "InsightIQ API"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    # Dataset ingestion and resource constraints
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB default
    max_rows_limit: int = 100_000
    max_columns_limit: int = 200
    data_dir: Path = _REPO_ROOT / "data"

    # AI & Intelligence provider settings (optional)
    gemini_api_key: str | None = None
    ai_model: str = "gemini-3.6-flash"
    ai_enabled: bool = False

    @model_validator(mode="after")
    def _resolve_ai_keys(self) -> "Settings":
        import os

        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or None
        if self.gemini_api_key and not self.ai_enabled:
            self.ai_enabled = True
        return self






@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()


settings: Settings = get_settings()

