"""Tests for InsightIQ configuration and Pydantic Settings behavior."""

import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_default_settings(monkeypatch):
    """Verify default configuration values when no env overrides exist."""
    # Ensure no environment variables interfere
    for var in [
        "INSIGHTIQ_APP_NAME",
        "INSIGHTIQ_ENVIRONMENT",
        "INSIGHTIQ_DEBUG",
        "INSIGHTIQ_API_V1_PREFIX",
    ]:
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)
    assert settings.app_name == "InsightIQ API"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.api_v1_prefix == "/api/v1"


def test_environment_variable_overrides(monkeypatch):
    """Verify all four settings can be overridden via INSIGHTIQ_ prefixed environment variables."""
    monkeypatch.setenv("INSIGHTIQ_APP_NAME", "Custom Platform")
    monkeypatch.setenv("INSIGHTIQ_ENVIRONMENT", "staging")
    monkeypatch.setenv("INSIGHTIQ_DEBUG", "true")
    monkeypatch.setenv("INSIGHTIQ_API_V1_PREFIX", "/api/v2")

    settings = Settings(_env_file=None)
    assert settings.app_name == "Custom Platform"
    assert settings.environment == "staging"
    assert settings.debug is True
    assert settings.api_v1_prefix == "/api/v2"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("True", True),
        ("1", True),
        ("false", False),
        ("0", False),
    ],
)
def test_boolean_debug_parsing(monkeypatch, value, expected):
    """Verify flexible boolean parsing for INSIGHTIQ_DEBUG."""
    monkeypatch.setenv("INSIGHTIQ_DEBUG", value)
    settings = Settings(_env_file=None)
    assert settings.debug is expected


def test_invalid_boolean_debug_rejected(monkeypatch):
    """Verify invalid boolean values trigger a Pydantic ValidationError."""
    monkeypatch.setenv("INSIGHTIQ_DEBUG", "not-a-boolean")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_unknown_env_keys_ignored(monkeypatch):
    """Verify unknown environment variables are ignored without errors."""
    monkeypatch.setenv("INSIGHTIQ_UNKNOWN_FIELD", "some_value")
    monkeypatch.setenv("UNRELATED_SECRET", "xyz")

    settings = Settings(_env_file=None)
    assert settings.app_name == "InsightIQ API"


def test_env_file_loading(tmp_path):
    """Verify settings can be loaded from an external .env file with UTF-8 encoding."""
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "INSIGHTIQ_APP_NAME=InsightIQ UTF8 Test \u2014 \u2714\n"
        "INSIGHTIQ_ENVIRONMENT=production\n"
        "INSIGHTIQ_DEBUG=false\n"
        "INSIGHTIQ_API_V1_PREFIX=/api/v1\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)
    assert settings.app_name == "InsightIQ UTF8 Test \u2014 \u2714"
    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.api_v1_prefix == "/api/v1"
