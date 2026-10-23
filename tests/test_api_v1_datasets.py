"""API integration tests for /api/v1/datasets endpoints."""

import io
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def app_with_temp_data(tmp_path):
    """Create an isolated FastAPI application instance pointing to a temporary data directory."""
    test_settings = Settings(
        app_name="Test InsightIQ",
        environment="development",
        data_dir=tmp_path / "api_test_data",
        max_upload_size_bytes=500_000,
        max_rows_limit=1000,
        max_columns_limit=20,
        _env_file=None,
    )
    return create_app(custom_settings=test_settings)


def test_upload_and_profile_csv_endpoint(app_with_temp_data):
    """Verify POST /api/v1/datasets/upload ingests and profiles CSV file."""
    client = TestClient(app_with_temp_data)

    csv_content = (
        "department,budget,headcount\n"
        "Engineering,500000,25\n"
        "Marketing,200000,10\n"
        "Sales,350000,18\n"
    ).encode("utf-8")

    files = {"file": ("dept_budget.csv", io.BytesIO(csv_content), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Dataset successfully uploaded and profiled."
    summary = data["summary"]
    assert summary["filename"] == "dept_budget.csv"
    assert summary["row_count"] == 3
    assert summary["column_count"] == 3
    dataset_id = summary["dataset_id"]

    # Verify GET /api/v1/datasets/{dataset_id}
    detail_res = client.get(f"/api/v1/datasets/{dataset_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["dataset_id"] == dataset_id
    assert len(detail["columns"]) == 3
    assert len(detail["preview"]) == 3

    # Verify GET /api/v1/datasets
    list_res = client.get("/api/v1/datasets")
    assert list_res.status_code == 200
    all_datasets = list_res.json()
    assert len(all_datasets) == 1
    assert all_datasets[0]["dataset_id"] == dataset_id


def test_upload_empty_csv_returns_400(app_with_temp_data):
    """Verify uploading an empty CSV returns 400 Bad Request."""
    client = TestClient(app_with_temp_data)
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_non_csv_returns_400(app_with_temp_data):
    """Verify uploading a non-CSV file returns 400 Bad Request."""
    client = TestClient(app_with_temp_data)
    files = {"file": ("data.json", io.BytesIO(b'{"key": "value"}'), "application/json")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code == 400
    assert "only csv" in response.json()["detail"].lower()


def test_get_unknown_dataset_returns_404(app_with_temp_data):
    """Verify querying non-existent dataset ID returns 404 Not Found."""
    client = TestClient(app_with_temp_data)
    response = client.get("/api/v1/datasets/unknown_id_12345")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_openapi_includes_dataset_routes(app_with_temp_data):
    """Verify OpenAPI documentation registers /api/v1/datasets endpoints."""
    client = TestClient(app_with_temp_data)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/datasets/upload" in paths
    assert "/api/v1/datasets" in paths
    assert "/api/v1/datasets/{dataset_id}" in paths
