"""Unit tests for AnalyticsService (correlations, aggregations, and anomaly detection)."""

import pytest
from app.core.config import Settings
from app.schemas.analytics import AggregationRequest
from app.services.analytics_service import AnalyticsError, AnalyticsService
from app.services.dataset_service import DatasetService


@pytest.fixture
def analytics_test_setup(tmp_path):
    """Provide isolated Settings and pre-seeded dataset for analytics testing."""
    test_settings = Settings(
        data_dir=tmp_path / "analytics_data",
        _env_file=None,
    )

    csv_data = (
        "region,store,sales,profit,units\n"
        "North,Store_A,100,20,5\n"
        "North,Store_B,200,40,10\n"
        "South,Store_C,300,60,15\n"
        "South,Store_D,400,80,20\n"
        "East,Store_E,50,10,2\n"
        "West,Store_F,1000,200,50\n"  # West has high values
    ).encode("utf-8")

    upload_res = DatasetService.ingest_csv(
        file_bytes=csv_data,
        filename="retail_performance.csv",
        settings=test_settings,
    )

    return test_settings, upload_res.summary.dataset_id


def test_compute_correlation_pearson_and_spearman(analytics_test_setup):
    """Verify correlation matrix and top pairwise correlations."""
    settings, dataset_id = analytics_test_setup

    res = AnalyticsService.compute_correlation(dataset_id, settings, method="pearson")
    assert res.dataset_id == dataset_id
    assert res.method == "pearson"
    assert set(res.features) == {"sales", "profit", "units"}

    # Perfect correlation between sales and profit (profit = 0.2 * sales)
    assert res.matrix["sales"]["profit"] == 1.0
    assert res.matrix["sales"]["sales"] == 1.0

    # Top correlations should include sales and profit as strong_positive
    top_pair = res.top_correlations[0]
    assert {top_pair.feature_x, top_pair.feature_y} == {"sales", "profit"}
    assert top_pair.coefficient == 1.0
    assert top_pair.strength == "strong_positive"

    # Test spearman as well
    res_spearman = AnalyticsService.compute_correlation(dataset_id, settings, method="spearman")
    assert res_spearman.method == "spearman"
    assert len(res_spearman.top_correlations) > 0


def test_correlation_requires_at_least_two_numeric_columns(tmp_path):
    """Verify AnalyticsError is raised if dataset has fewer than 2 numeric columns."""
    settings = Settings(data_dir=tmp_path / "single_num_data", _env_file=None)
    csv_data = b"name,city,revenue\nAlice,NYC,100\nBob,LA,200\n"
    res = DatasetService.ingest_csv(csv_data, "single_num.csv", settings)

    with pytest.raises(AnalyticsError, match="At least 2 numeric columns are required"):
        AnalyticsService.compute_correlation(res.summary.dataset_id, settings)


def test_grouped_aggregations(analytics_test_setup):
    """Verify multi-dimensional grouping and metric calculation."""
    settings, dataset_id = analytics_test_setup

    req = AggregationRequest(
        group_by=["region"],
        metrics={"sales": ["sum", "mean"], "units": ["sum"]},
        sort_by="sales_sum",
        ascending=False,
    )

    res = AnalyticsService.compute_aggregations(dataset_id, req, settings)
    assert res.dataset_id == dataset_id
    assert res.row_count == 4  # North, South, East, West

    # West has sales 1000, should be first
    first_row = res.data[0]
    assert first_row["region"] == "West"
    assert first_row["sales_sum"] == 1000
    assert first_row["sales_mean"] == 1000.0

    # North has 2 stores (100 + 200 = 300 sum, 150 mean)
    north_row = next(r for r in res.data if r["region"] == "North")
    assert north_row["sales_sum"] == 300
    assert north_row["sales_mean"] == 150.0
    assert north_row["units_sum"] == 15


def test_aggregation_validation_failures(analytics_test_setup):
    """Verify invalid grouping columns or non-numeric metrics trigger AnalyticsError."""
    settings, dataset_id = analytics_test_setup

    # Non-existent group column
    req_bad_group = AggregationRequest(
        group_by=["non_existent"],
        metrics={"sales": ["sum"]},
    )
    with pytest.raises(AnalyticsError, match="Group-by column.*not found"):
        AnalyticsService.compute_aggregations(dataset_id, req_bad_group, settings)

    # Non-numeric metric column
    req_bad_metric = AggregationRequest(
        group_by=["region"],
        metrics={"store": ["sum"]},
    )
    with pytest.raises(AnalyticsError, match="is not numeric"):
        AnalyticsService.compute_aggregations(dataset_id, req_bad_metric, settings)


def test_outlier_detection_iqr_and_zscore(tmp_path):
    """Verify detection of extreme values via IQR and Z-score algorithms."""
    settings = Settings(data_dir=tmp_path / "outlier_data", _env_file=None)
    # 9 normal numbers around 10, plus 1 extreme outlier (999)
    csv_data = "id,score\n" + "".join(f"{i},10\n" for i in range(1, 10)) + "10,999\n"
    res = DatasetService.ingest_csv(csv_data.encode("utf-8"), "outliers.csv", settings)

    # IQR method
    iqr_res = AnalyticsService.detect_outliers(
        dataset_id=res.summary.dataset_id,
        column="score",
        settings=settings,
        method="iqr",
        threshold=1.5,
    )
    assert iqr_res.column == "score"
    assert iqr_res.outlier_count == 1
    assert iqr_res.outliers[0].value == 999.0
    assert iqr_res.outliers[0].row_index == 9

    # Z-score method
    z_res = AnalyticsService.detect_outliers(
        dataset_id=res.summary.dataset_id,
        column="score",
        settings=settings,
        method="zscore",
        threshold=2.0,
    )
    assert z_res.outlier_count == 1
    assert z_res.outliers[0].value == 999.0
    assert z_res.outliers[0].score > 2.0


def test_outlier_detection_rejects_non_numeric_column(analytics_test_setup):
    """Verify error when attempting outlier detection on categorical/text column."""
    settings, dataset_id = analytics_test_setup
    with pytest.raises(AnalyticsError, match="is not numeric"):
        AnalyticsService.detect_outliers(dataset_id, "region", settings)
