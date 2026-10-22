"""Application configuration for InsightIQ.

Settings are read from environment variables prefixed with ``INSIGHTIQ_`` and,
optionally, from a local ``.env`` file. Real environment variables take
precedence over values in ``.env``. Import the shared ``settings`` instance
rather than constructing ``Settings`` directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed InsightIQ settings with safe local-development defaults."""

    model_config = SettingsConfigDict(
        env_prefix="INSIGHTIQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "InsightIQ API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"


settings = Settings()
