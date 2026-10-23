"""API integration tests for /api/v1/query endpoints."""

import io
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def query_api_client(tmp_path):
    """Provide isolated application with pre-seeded dataset for query HTTP testing."""
    test_settings = Settings(
        app_name="Query Test Platform",
        environment="development",
        data_dir=tmp_path / "api_query_data",
        _env_file=None,
    )
    test_app = create_app(custom_settings=test_settings)
    client = TestClient(test_app)

    csv_content = (
        "department,budget,headcount\n"
        "Engineering,500000,25\n"
        "Marketing,200000,10\n"
        "Sales,350000,18\n"
    ).encode("utf-8")

    files = {"file": ("org_budget.csv", io.BytesIO(csv_content), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    dataset_id = upload_res.json()["summary"]["dataset_id"]

    return client, dataset_id


def test_query_endpoint_successful_inquiry(query_api_client):
    """Verify POST /api/v1/query/{dataset_id} returns 200 and structured response."""
    client, dataset_id = query_api_client

    payload = {"query": "What is the total budget?"}
    response = client.post(f"/api/v1/query/{dataset_id}", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == dataset_id
    assert data["query"] == "What is the total budget?"
    assert data["intent"] == "metric_summary"
    assert "1,050,000.00" in data["answer"]
    assert data["confidence"] > 0.5


def test_query_endpoint_validation_error(query_api_client):
    """Verify 422 is returned when query string is too short or missing."""
    client, dataset_id = query_api_client

    # Query string shorter than min_length=2
    response = client.post(f"/api/v1/query/{dataset_id}", json={"query": "a"})
    assert response.status_code == 422


def test_query_endpoint_unknown_dataset_404(query_api_client):
    """Verify 404 is returned when querying unknown dataset ID."""
    client, _ = query_api_client
    response = client.post("/api/v1/query/unknown_uuid_123", json={"query": "What is total sales?"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_openapi_includes_query_route(query_api_client):
    """Verify OpenAPI documentation registers /api/v1/query/{dataset_id}."""
    client, _ = query_api_client
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/query/{dataset_id}" in paths
    assert "post" in paths["/api/v1/query/{dataset_id}"]
