"""API integration tests for /api/v1/analytics endpoints."""

import io
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def analytics_client_setup(tmp_path):
    """Provide isolated application with pre-seeded dataset for HTTP analytics testing."""
    test_settings = Settings(
        app_name="Analytics Test App",
        environment="development",
        data_dir=tmp_path / "api_analytics_data",
        _env_file=None,
    )
    test_app = create_app(custom_settings=test_settings)
    client = TestClient(test_app)

    csv_content = (
        "region,sales,marketing_spend\n"
        "North,1000,200\n"
        "North,1500,250\n"
        "South,2000,400\n"
        "South,3000,500\n"
        "East,800,150\n"
        "East,900,160\n"
        "West,50000,9000\n"  # West has outlier
    ).encode("utf-8")

    files = {"file": ("business_metrics.csv", io.BytesIO(csv_content), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    dataset_id = upload_res.json()["summary"]["dataset_id"]

    return client, dataset_id


def test_correlations_api(analytics_client_setup):
    """Verify GET /api/v1/analytics/correlations/{dataset_id}."""
    client, dataset_id = analytics_client_setup

    res = client.get(f"/api/v1/analytics/correlations/{dataset_id}?method=pearson")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert "sales" in data["matrix"]
    assert "marketing_spend" in data["matrix"]["sales"]
    assert len(data["top_correlations"]) > 0


def test_correlations_api_not_found(analytics_client_setup):
    """Verify 404 returned for non-existent dataset in correlation endpoint."""
    client, _ = analytics_client_setup
    res = client.get("/api/v1/analytics/correlations/unknown_dataset_id")
    assert res.status_code == 404


def test_aggregation_api(analytics_client_setup):
    """Verify POST /api/v1/analytics/aggregate/{dataset_id}."""
    client, dataset_id = analytics_client_setup

    payload = {
        "group_by": ["region"],
        "metrics": {"sales": ["sum", "mean"]},
        "sort_by": "sales_sum",
        "ascending": False,
        "limit": 10,
    }
    res = client.post(f"/api/v1/analytics/aggregate/{dataset_id}", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert data["row_count"] == 4
    assert data["data"][0]["region"] == "West"


def test_aggregation_api_invalid_metric(analytics_client_setup):
    """Verify 400 returned when attempting to aggregate non-numeric column."""
    client, dataset_id = analytics_client_setup
    payload = {
        "group_by": ["sales"],
        "metrics": {"region": ["sum"]},
    }
    res = client.post(f"/api/v1/analytics/aggregate/{dataset_id}", json=payload)
    assert res.status_code == 400
    assert "not numeric" in res.json()["detail"].lower()


def test_outlier_detection_api(analytics_client_setup):
    """Verify GET /api/v1/analytics/outliers/{dataset_id}."""
    client, dataset_id = analytics_client_setup

    res = client.get(f"/api/v1/analytics/outliers/{dataset_id}?column=sales&method=iqr&threshold=1.5")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert data["column"] == "sales"
    assert data["outlier_count"] >= 1
    assert any(o["value"] == 50000.0 for o in data["outliers"])


def test_outlier_detection_api_invalid_column(analytics_client_setup):
    """Verify 400 returned for unknown column in outlier detection."""
    client, dataset_id = analytics_client_setup
    res = client.get(f"/api/v1/analytics/outliers/{dataset_id}?column=non_existent")
    assert res.status_code == 400
    assert "does not exist" in res.json()["detail"].lower()


def test_openapi_includes_analytics_routes(analytics_client_setup):
    """Verify OpenAPI documentation registers all analytics endpoints."""
    client, _ = analytics_client_setup
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    assert "/api/v1/analytics/correlations/{dataset_id}" in paths
    assert "/api/v1/analytics/aggregate/{dataset_id}" in paths
    assert "/api/v1/analytics/outliers/{dataset_id}" in paths
