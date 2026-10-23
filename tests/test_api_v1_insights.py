"""API integration tests for /api/v1/insights endpoints."""

import io
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def insights_api_client(tmp_path):
    """Provide isolated application with pre-seeded dataset for insights HTTP testing."""
    test_settings = Settings(
        app_name="Insights Test Platform",
        environment="development",
        data_dir=tmp_path / "api_insights_data",
        _env_file=None,
    )
    test_app = create_app(custom_settings=test_settings)
    client = TestClient(test_app)

    csv_content = (
        "segment,sales,profit\n"
        "SMB,500,50\n"
        "SMB,600,60\n"
        "Enterprise,5000,500\n"
        "Enterprise,6000,600\n"
    ).encode("utf-8")

    files = {"file": ("insights_sample.csv", io.BytesIO(csv_content), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    dataset_id = upload_res.json()["summary"]["dataset_id"]

    return client, dataset_id


def test_get_insights_endpoint(insights_api_client):
    """Verify GET /api/v1/insights/{dataset_id} returns 200 and expected schema."""
    client, dataset_id = insights_api_client

    response = client.get(f"/api/v1/insights/{dataset_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["dataset_id"] == dataset_id
    assert data["filename"] == "insights_sample.csv"
    assert "executive_summary" in data
    assert "data_quality" in data
    assert data["data_quality"]["overall_score"] > 0
    assert "insights" in data
    assert isinstance(data["insights"], list)
    assert "key_metrics" in data


def test_get_insights_unknown_id_returns_404(insights_api_client):
    """Verify 404 is returned when querying unknown dataset ID."""
    client, _ = insights_api_client
    response = client.get("/api/v1/insights/unknown_uuid_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_openapi_includes_insights_route(insights_api_client):
    """Verify OpenAPI documentation registers /api/v1/insights/{dataset_id}."""
    client, _ = insights_api_client
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/insights/{dataset_id}" in paths
