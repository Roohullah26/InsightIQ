"""Tests for InsightIQ API v1 health endpoint and routing."""

from fastapi.testclient import TestClient

from app import __version__
from app.core.config import Settings
from app.main import app, create_app


def test_api_v1_health_endpoint():
    """Verify GET /api/v1/health returns rich health metrics matching HealthResponse schema."""
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "InsightIQ API"
    assert data["environment"] == "development"
    assert data["version"] == __version__
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0.0


def test_api_v1_health_custom_configuration():
    """Verify /api/v1/health reflects runtime custom configuration."""
    custom = Settings(
        app_name="Production BI",
        environment="production",
        _env_file=None,
    )
    custom_app = create_app(custom_settings=custom)
    client = TestClient(custom_app)

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "Production BI"
    assert data["environment"] == "production"


def test_openapi_includes_v1_health():
    """Verify OpenAPI documentation registers /api/v1/health route."""
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "get" in paths["/api/v1/health"]
