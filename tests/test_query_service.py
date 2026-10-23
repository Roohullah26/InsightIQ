"""Unit tests for the QueryService natural language question-answering engine."""

import pytest
from app.core.config import Settings
from app.services.dataset_service import DatasetNotFoundError, DatasetService
from app.services.query_service import QueryService


@pytest.fixture
def query_test_setup(tmp_path):
    """Provide isolated Settings and pre-seeded dataset for query engine testing."""
    test_settings = Settings(
        data_dir=tmp_path / "query_data",
        _env_file=None,
    )

    csv_data = (
        "region,store,revenue,profit\n"
        "North,Store_A,1000,200\n"
        "North,Store_B,1500,300\n"
        "South,Store_C,2000,400\n"
        "South,Store_D,2500,500\n"
        "East,Store_E,500,100\n"
        "West,Store_F,10000,2000\n"  # West is top and has outlier
    ).encode("utf-8")

    upload_res = DatasetService.ingest_csv(
        file_bytes=csv_data,
        filename="sales_territory.csv",
        settings=test_settings,
    )

    return test_settings, upload_res.summary.dataset_id


def test_query_general_row_count(query_test_setup):
    """Verify 'how many rows' inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "How many rows are in this dataset?", settings)

    assert res.intent == "general_count"
    assert "6 rows" in res.answer
    assert res.data_preview[0]["row_count"] == 6


def test_query_metric_summary_total_and_average(query_test_setup):
    """Verify total and average metric calculations."""
    settings, dataset_id = query_test_setup

    # Total revenue: 1000 + 1500 + 2000 + 2500 + 500 + 10000 = 17500
    res_sum = QueryService.execute_query(dataset_id, "What is the total revenue?", settings)
    assert res_sum.intent == "metric_summary"
    assert "17,500.00" in res_sum.answer

    # Average profit: (200 + 300 + 400 + 500 + 100 + 2000) / 6 = 583.33
    res_avg = QueryService.execute_query(dataset_id, "What is the average profit?", settings)
    assert res_avg.intent == "metric_summary"
    assert "583.33" in res_avg.answer


def test_query_grouped_aggregation(query_test_setup):
    """Verify 'revenue by region' grouped aggregation inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Show me revenue by region", settings)

    assert res.intent == "grouped_aggregation"
    assert res.target_metric == "revenue"
    assert res.group_by_dimension == "region"
    assert "West" in res.answer
    assert len(res.data_preview) == 4


def test_query_ranking_extreme(query_test_setup):
    """Verify 'top store by revenue' ranking inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "What is the top store by revenue?", settings)

    assert res.intent == "ranking_extreme"
    assert "10,000.00" in res.answer
    assert "Store_F" in res.answer


def test_query_filtered_metric(query_test_setup):
    """Verify 'revenue in North' filtered calculation."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "What is the revenue in North?", settings)

    assert res.intent == "filtered_metric"
    assert "2,500.00" in res.answer  # 1000 + 1500
    assert "North" in res.answer


def test_query_correlation_inquiry(query_test_setup):
    """Verify correlation inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Is there a correlation between revenue and profit?", settings)

    assert res.intent == "correlation_inquiry"
    assert "1.000" in res.answer


def test_query_anomaly_inquiry(query_test_setup):
    """Verify outlier/anomaly inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Are there any outliers in revenue?", settings)

    assert res.intent == "anomaly_inquiry"
    assert "10,000.00" in res.answer


def test_query_nonexistent_dataset_raises_not_found(query_test_setup):
    """Verify querying non-existent dataset ID raises DatasetNotFoundError."""
    settings, _ = query_test_setup
    with pytest.raises(DatasetNotFoundError):
        QueryService.execute_query("unknown_uuid", "total revenue", settings)
