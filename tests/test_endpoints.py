"""Characterization tests for InsightIQ API endpoints."""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify GET / returns welcome message and running status."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to InsightIQ!",
        "status": "running",
    }


def test_health_endpoint():
    """Verify GET /health returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_openapi_schema():
    """Verify OpenAPI documentation metadata and registered routes."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "InsightIQ API"
    assert "/" in data["paths"]
    assert "/health" in data["paths"]
