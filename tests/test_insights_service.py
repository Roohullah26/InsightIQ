"""Unit tests for the InsightsService AI & heuristic synthesis engine."""

import pytest
from app.core.config import Settings
from app.services.dataset_service import DatasetNotFoundError, DatasetService
from app.services.insights_service import InsightsService


@pytest.fixture
def insights_test_setup(tmp_path):
    """Provide isolated Settings and pre-seeded dataset for insights testing."""
    test_settings = Settings(
        data_dir=tmp_path / "insights_data",
        _env_file=None,
    )

    # 10 rows:
    # - 'region' is 80% 'North' (category concentration)
    # - 'churn_risk' has 2 nulls out of 10 (20% missingness)
    # - 'revenue' and 'ad_spend' have strong positive correlation
    # - row 10 has an extreme spike in revenue (50,000)
    csv_rows = [
        "region,revenue,ad_spend,churn_risk\n",
        "North,1000,200,low\n",
        "North,1100,220,low\n",
        "North,1200,240,low\n",
        "North,1300,260,low\n",
        "North,1400,280,medium\n",
        "North,1500,300,medium\n",
        "North,1600,320,medium\n",
        "North,1700,340,high\n",
        "South,1800,360,\n",  # null churn_risk
        "South,50000,10000,\n",  # null churn_risk + outlier
    ]
    csv_data = "".join(csv_rows).encode("utf-8")

    upload_res = DatasetService.ingest_csv(
        file_bytes=csv_data,
        filename="executive_report.csv",
        settings=test_settings,
    )

    return test_settings, upload_res.summary.dataset_id


def test_generate_insights_comprehensive(insights_test_setup):
    """Verify automated data quality, correlations, anomalies, and executive synthesis."""
    settings, dataset_id = insights_test_setup

    res = InsightsService.generate_insights(dataset_id=dataset_id, settings=settings)

    assert res.dataset_id == dataset_id
    assert res.filename == "executive_report.csv"
    assert len(res.executive_summary) > 20
    assert 0.0 <= res.data_quality.overall_score <= 100.0

    # Completeness check: 2 nulls out of 40 cells = 95% completeness
    assert res.data_quality.completeness_score == 95.0

    # Categorized insights inspection
    categories = [i.category for i in res.insights]

    # Should detect data quality missingness in 'churn_risk'
    assert "data_quality" in categories
    dq_insight = next(i for i in res.insights if i.category == "data_quality")
    assert "churn_risk" in dq_insight.summary

    # Should detect strong correlation between revenue and ad_spend
    assert "correlation" in categories
    corr_insight = next(i for i in res.insights if i.category == "correlation")
    assert "revenue" in corr_insight.title.lower() or "ad_spend" in corr_insight.title.lower()

    # Should detect anomaly in revenue or ad_spend
    assert "anomaly" in categories

    # Should detect category concentration in region (80% North)
    assert "risk" in categories
    risk_insight = next(i for i in res.insights if i.category == "risk")
    assert "North" in risk_insight.summary


def test_generate_insights_nonexistent_dataset_raises_not_found(insights_test_setup):
    """Verify querying non-existent dataset ID raises DatasetNotFoundError."""
    settings, _ = insights_test_setup
    with pytest.raises(DatasetNotFoundError):
        InsightsService.generate_insights("non_existent_uuid", settings)
