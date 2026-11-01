"""Unit tests for the InsightsService AI & heuristic synthesis engine."""

import numpy as np
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
    assert "revenue" in corr_insight.title.lower() or "ad spend" in corr_insight.title.lower()
    # Lever (ad_spend) should drive outcome (revenue)
    assert "ad_spend" in corr_insight.recommendation.lower()
    assert corr_insight.confidence_badge is not None
    assert "n = 10" in corr_insight.confidence_badge

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


def test_collinear_growth_cluster_and_causal_directionality(tmp_path):
    """Verify collinear clustering groups mutually correlated variables (|r| >= 0.85) and respects causal hierarchy."""
    settings = Settings(data_dir=tmp_path / "cluster_data", _env_file=None)

    # 40 rows: marketing_spend, customers, revenue mutually collinear
    lines = ["marketing_spend,customers,revenue,category\n"]
    for i in range(1, 41):
        spend = 1000 + (i * 200)
        cust = 50 + (i * 10)
        rev = 5000 + (i * 1000)
        lines.append(f"{spend},{cust},{rev},retail\n")

    res = DatasetService.ingest_csv(
        file_bytes="".join(lines).encode("utf-8"),
        filename="marketing_cluster.csv",
        settings=settings,
    )
    insights_res = InsightsService.generate_insights(res.summary.dataset_id, settings)

    # Health score reflects 100% completeness (40 pts) + 100% hygiene (30 pts) + tiered sample scale (20 pts at n=40)
    assert 65.0 <= insights_res.data_quality.sample_size_score < 100.0
    assert insights_res.data_quality.overall_score >= 88.0

    # Must have Multi-Driver Growth Cluster
    cluster_insights = [
        i for i in insights_res.insights
        if i.category == "correlation" and "growth cluster" in i.title.lower()
    ]
    assert len(cluster_insights) == 1
    cluster = cluster_insights[0]
    assert "Marketing Spend" in cluster.title
    assert "Revenue" in cluster.title
    # Recommendation should reference marketing_spend and caution on holdout testing / collinearity
    assert "marketing_spend" in cluster.recommendation.lower()
    assert "controlled holdout testing" in cluster.recommendation.lower()
    # Confidence badge should reflect n=40
    assert "n = 40" in cluster.confidence_badge


def test_slope_metric_scaling_and_no_zero_formatting():
    """Verify regression slope impacts never format as +0.00 and dynamically scale step size."""
    import pandas as pd
    import numpy as np

    # 40 observations: revenue between $100k and $200k, satisfaction between 4.0 and 4.5
    np.random.seed(42)
    rev = pd.Series([100000 + i * 2500 for i in range(40)])
    # Subtle positive effect: satisfaction increases ~0.000003 per dollar
    sat = pd.Series([4.0 + (r - 100000) * 0.000003 + np.random.normal(0, 0.02) for r in rev])

    slope_text, r_val, p_val = InsightsService._format_slope_metric(
        clean_x=rev,
        clean_y=sat,
        x_name="revenue",
        y_name="satisfaction",
    )

    # Must never produce "+0.00" or "+$0.00" or "-0.00"
    assert "+0.00 in 'satisfaction'" not in slope_text
    assert "+$0.00" not in slope_text
    assert "-0.00" not in slope_text
    # Should scale step size to meaningful magnitude
    assert "Each +$" in slope_text
    assert "in 'revenue' is associated with +" in slope_text


def test_eliminate_redundant_cross_correlations_with_cluster(tmp_path):
    """Verify only 1 consolidated card is generated for satisfaction when connected to a 3-variable cluster."""
    settings = Settings(data_dir=tmp_path / "dedup_cluster_data", _env_file=None)

    # 35 rows: marketing_spend, customers, revenue tightly correlated (r > 0.95), all correlating with satisfaction (r ~ 0.72)
    np.random.seed(42)
    lines = ["marketing_spend,customers,revenue,satisfaction\n"]
    for i in range(1, 36):
        spend = 15000 + (i * 500)
        cust = 800 + (i * 25)
        rev = 80000 + (i * 2500)
        noise = float(np.random.normal(0, 0.12))
        sat = round(4.0 + (i * 0.02) + noise, 2)
        lines.append(f"{spend},{cust},{rev},{sat}\n")

    res = DatasetService.ingest_csv(
        file_bytes="".join(lines).encode("utf-8"),
        filename="cluster_satisfaction.csv",
        settings=settings,
    )
    insights_res = InsightsService.generate_insights(res.summary.dataset_id, settings)

    # Find all correlation cards referencing satisfaction
    sat_cards = [
        i for i in insights_res.insights
        if i.category == "correlation" and "satisfaction" in (i.title + i.summary).lower()
    ]

    # Exactly 1 consolidated card for satisfaction, NOT 3 separate cards
    assert len(sat_cards) == 1
    # Evidence must not contain +0.00
    assert "+0.00" not in sat_cards[0].evidence


def test_realistic_45_row_enterprise_demo_dataset(tmp_path):
    """Verify the 45-row demo dataset achieves n >= 30, Data Health >= 95%, and robust statistical confidence."""
    import pathlib
    csv_file = pathlib.Path("d:/InsightIQ/data/executive_q3_performance_45.csv")
    assert csv_file.exists(), "45-row enterprise dataset file must exist"

    settings = Settings(data_dir=tmp_path / "demo_45_data", _env_file=None)
    res = DatasetService.ingest_csv(
        file_bytes=csv_file.read_bytes(),
        filename="executive_q3_performance.csv",
        settings=settings,
    )

    assert res.summary.row_count == 45
    insights_res = InsightsService.generate_insights(res.summary.dataset_id, settings)

    # Health score reflects 40 pts completeness + 20 pts sample adequacy (n=45) + 24 pts hygiene (-6 pts for 2 outlier cols) = 84.0%
    assert 84.0 <= insights_res.data_quality.overall_score <= 88.0
    assert 65.0 <= insights_res.data_quality.sample_size_score < 100.0
    assert insights_res.data_quality.duplicate_score == 100.0
    assert "84.0/100" in insights_res.executive_summary
    assert (
        "The dataset achieves 100% data completeness (zero missing values across all 270 cells)."
        in insights_res.executive_summary
    )

    # Verify dynamic anomaly recommendations (upper-bound spike vs lower-bound dip) & comma-formatted bounds
    anomaly_cards = {
        i.action_link["column"]: i
        for i in insights_res.insights
        if i.category == "anomaly" and i.action_link and "column" in i.action_link
    }
    assert "marketing_spend" in anomaly_cards
    assert anomaly_cards["marketing_spend"].title == "Statistical Anomalies in Marketing Spend"
    assert anomaly_cards["marketing_spend"].severity == "warning"
    assert "Bounds: [10,150.00, 35,350.00]" in anomaly_cards["marketing_spend"].evidence
    assert (
        anomaly_cards["marketing_spend"].recommendation
        == "Audit the high-magnitude spike in 'marketing_spend' (37,500.00) to confirm whether it reflects an intentional campaign surge or a duplicate/unallocated spend entry, and evaluate its marginal ROI."
    )
    assert "satisfaction" in anomaly_cards
    assert anomaly_cards["satisfaction"].title == "Statistical Anomalies in Satisfaction"
    assert anomaly_cards["satisfaction"].severity == "warning"
    assert (
        anomaly_cards["satisfaction"].recommendation
        == "Isolate the cohort or period behind the 'satisfaction' drop (3.20) to identify service bottlenecks, fulfillment delays, or localized churn risks."
    )

    # Verify collinear cluster title is Title Case, raw names in summary are single-quoted, and recommendation avoids causal overreach
    cluster_card = next(
        i for i in insights_res.insights if i.category == "correlation" and i.cluster_features
    )
    assert cluster_card.title == "Multi-Driver Growth Cluster: Marketing Spend · Customers · Revenue"
    assert "'marketing_spend', 'customers', 'revenue'" in cluster_card.summary
    assert (
        cluster_card.recommendation
        == "Strong historical co-movement links 'marketing_spend', 'customers', and 'revenue' (r ≥ 0.96). Validate causal lift via controlled holdout testing or incremental spend attribution before scaling budget allocations, and avoid combining these collinear features directly in unregularized linear models."
    )

    # No "Low Confidence - Small Sample" warning on any card
    for item in insights_res.insights:
        if item.confidence_badge:
            assert "Low Confidence - Small Sample" not in item.confidence_badge
            assert "n = 45" in item.confidence_badge
        assert "+0.00" not in (item.evidence or "")

