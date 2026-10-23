"""Tests for the InsightIQ application factory."""

from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import app as app_main_instance, create_app
from main import app as root_app_instance


def test_root_app_is_app_main_instance():
    """Verify root main.py exposes the exact instance from app.main."""
    assert root_app_instance is app_main_instance


def test_create_app_default_settings():
    """Verify create_app produces a configured FastAPI instance with default title."""
    app = create_app()
    assert app.title == "InsightIQ API"
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_app_custom_settings():
    """Verify create_app respects custom Settings overrides."""
    custom = Settings(
        app_name="Custom BI Engine",
        environment="staging",
        debug=True,
        _env_file=None,
    )
    app = create_app(custom_settings=custom)
    assert app.title == "Custom BI Engine"
    assert app.debug is True


def test_cors_middleware_headers():
    """Verify CORS middleware is active and attaches appropriate headers."""
    client = TestClient(app_main_instance)
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"

