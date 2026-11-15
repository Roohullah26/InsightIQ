"""Unit and integration tests for InsightIQ TruthLens — Evidence-Based Intelligence Engine."""

import pathlib
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app
from app.services.dataset_service import DatasetService
from app.services.truthlens_service import TruthLensService


@pytest.fixture
def truthlens_settings(tmp_path):
    """Provide isolated Settings for TruthLens testing."""
    return Settings(data_dir=tmp_path / "truthlens_data", _env_file=None)


def test_scenario_a_revenue_growth_without_profit_growth(truthlens_settings):
    """Verify Scenario A detects +40% revenue, +133.3% marketing spend, and -20% gross profit contradiction."""
    dataset_id = TruthLensService.load_scenario_dataset("scenario_a", truthlens_settings)
    report = TruthLensService.analyze_dataset(dataset_id, truthlens_settings)

    assert report.summary_counts.total_findings >= 2
    assert report.summary_counts.critical_count >= 1
    assert report.summary_counts.kpi_contradictions_count >= 2

    rev_profit_finding = next(
        f for f in report.findings if f.id == "tl_kpi_rev_profit_contradiction"
    )
    assert rev_profit_finding.severity == "Critical"
    assert rev_profit_finding.category == "kpi_contradiction"
    assert "40.0%" in rev_profit_finding.supporting_evidence
    assert "133.3%" in rev_profit_finding.supporting_evidence
    assert "-20.0%" in rev_profit_finding.supporting_evidence

    # Must recommend investigating acquisition costs, discounting, and product margins
    rec_text = " ".join(rev_profit_finding.recommended_investigation).lower()
    assert "discounting" in rec_text
    assert "margin" in rec_text
    assert "acquisition cost" in rec_text

    # Must include corrected accounting Hypothesis 3 (COGS Inflation / Contra-Revenue) and suppress CLT warning on 2-period rollup
    hyp_text = " ".join(rev_profit_finding.hypotheses)
    assert "Hypothesis" in hyp_text
    assert "COGS Inflation or Promotional Contra-Revenue Misclassification" in hyp_text
    assert any("Short time horizon (2 aggregated periods)" in w for w in report.data_quality_warnings)


def test_scenario_b_improving_satisfaction_with_increasing_churn(truthlens_settings):
    """Verify Scenario B detects satisfaction 3.8->4.6, -82% survey responses, doubled churn (4%->8%), and potential bias."""
    dataset_id = TruthLensService.load_scenario_dataset("scenario_b", truthlens_settings)
    report = TruthLensService.analyze_dataset(dataset_id, truthlens_settings)

    assert report.summary_counts.critical_count >= 2

    # 1. Satisfaction vs Churn Contradiction
    contradiction = next(
        f for f in report.findings if f.id == "tl_kpi_satisfaction_churn_contradiction"
    )
    assert contradiction.severity == "Critical"
    assert "3.8" in contradiction.supporting_evidence
    assert "4.6" in contradiction.supporting_evidence
    assert "4.0%" in contradiction.supporting_evidence
    assert "8.0%" in contradiction.supporting_evidence
    assert "100" in contradiction.what_happened or "doubling" in contradiction.what_happened

    # 2. Survey Participation Collapse (-82%) & Potential Non-Response Bias (not claimed as proven)
    bias_finding = next(
        f for f in report.findings if f.id == "tl_sampling_survey_participation_drop"
    )
    assert bias_finding.severity == "Critical"
    assert bias_finding.category == "sampling_and_response_bias"
    assert "82.0%" in bias_finding.what_happened
    assert "1,000" in bias_finding.supporting_evidence
    assert "180" in bias_finding.supporting_evidence
    assert "not proven" in bias_finding.why_it_matters.lower()
    assert any("Unproven" in h for h in bias_finding.hypotheses)


def test_scenario_c_aggregate_revenue_hiding_category_declines(truthlens_settings):
    """Verify Scenario C detects +10% total revenue hiding -18.75% Clothing and -31.25% Furniture declines."""
    dataset_id = TruthLensService.load_scenario_dataset("scenario_c", truthlens_settings)
    report = TruthLensService.analyze_dataset(dataset_id, truthlens_settings)

    assert report.summary_counts.critical_count >= 1
    assert report.summary_counts.segment_warnings_count >= 1

    seg_finding = next(
        f for f in report.findings if f.id == "tl_hidden_segment_decline_temporal"
    )
    assert seg_finding.severity == "Critical"
    assert seg_finding.category == "hidden_segment_decline"
    assert "10.0%" in seg_finding.what_happened
    assert "150.0%" in seg_finding.what_happened
    assert "18.75%" in seg_finding.what_happened
    assert "31.25%" in seg_finding.what_happened
    assert "2 out of 3" in seg_finding.what_happened
    assert "concentrated in 'Electronics'" in seg_finding.what_happened


def test_truthlens_on_enterprise_45_row_dataset_and_insufficient_evidence(truthlens_settings):
    """Verify TruthLens runs on general cross-sectional datasets and reports insufficient evidence when appropriate."""
    csv_file = pathlib.Path("d:/InsightIQ/data/executive_q3_performance_45.csv")
    upload_res = DatasetService.ingest_csv(
        file_bytes=csv_file.read_bytes(),
        filename="executive_q3_performance.csv",
        settings=truthlens_settings,
    )
    report = TruthLensService.analyze_dataset(upload_res.summary.dataset_id, truthlens_settings)

    categories_found = {f.category for f in report.findings}
    assert "kpi_contradiction" in categories_found
    assert "hidden_segment_decline" in categories_found
    assert "misleading_averages" in categories_found
    assert "correlation_vs_causation" in categories_found
    assert "statistical_anomalies" in categories_found

    # Every finding must contain all mandatory fields + Section 7 Dataset Traceability fields
    assert report.row_count == 45
    assert report.column_count == 6
    assert len(report.comparison_periods) >= 1
    assert len(report.data_quality_warnings) >= 1

    for finding in report.findings:
        assert finding.title
        assert finding.severity in ("Critical", "High", "Medium", "Low")
        assert finding.what_happened
        assert finding.supporting_evidence
        assert finding.comparison_baseline
        assert finding.why_it_matters
        assert len(finding.hypotheses) >= 1
        assert finding.confidence_level in ("High", "Medium", "Low")
        assert finding.confidence_justification
        assert len(finding.recommended_investigation) >= 1
        assert len(finding.relevant_columns) >= 1
        assert len(finding.calculations) >= 1
        assert len(finding.supporting_row_references) >= 1
        assert len(finding.group_references) >= 1
        assert finding.calculation_methodology
        assert len(finding.comparison_periods) >= 1
        assert len(finding.data_quality_warnings) >= 1
        assert finding.ai_explanation

    # Single-snapshot dataset must report insufficient evidence for temporal comparison
    insuff_cats = {n.category for n in report.insufficient_evidence}
    assert "incomplete_comparisons" in insuff_cats


def test_truthlens_context_preserving_scenario_switcher_and_trace_ui(truthlens_settings):
    """Verify non-destructive scenario preview endpoint preserves workspace datasets and UI renders Section 7 elements."""
    app = create_app(custom_settings=truthlens_settings)
    client = TestClient(app)

    # Initially 0 workspace datasets
    ds_before = client.get("/api/v1/datasets").json()
    assert len(ds_before) == 0

    # Preview Scenarios A, B, and C via GET /scenarios/{key}/report without mutating workspace datasets
    for key in ("scenario_a", "scenario_b", "scenario_c"):
        prev_res = client.get(f"/api/v1/truthlens/scenarios/{key}/report")
        assert prev_res.status_code == 200
        body = prev_res.json()
        assert body["dataset_id"] == f"builtin_{key}"
        assert body["row_count"] >= 2
        assert body["summary_counts"]["critical_count"] >= 1
        for finding in body["findings"]:
            assert len(finding["supporting_row_references"]) >= 1
            assert len(finding["group_references"]) >= 1
            assert finding["calculation_methodology"]
            assert len(finding["comparison_periods"]) >= 1

    # Workspace dataset list must remain untouched after scenario previews
    ds_after = client.get("/api/v1/datasets").json()
    assert len(ds_after) == 0


def test_truthlens_false_positive_prevention_and_missing_data_handling(truthlens_settings):
    """Verify healthy aligned datasets produce 0 false KPI contradictions and dirty datasets surface quality warnings."""
    import pandas as pd

    # 1. Healthy aligned dataset (Revenue +15%, Profit +18%, Marketing +10%)
    healthy_df = pd.DataFrame(
        {
            "period": ["Q1", "Q2"],
            "revenue": [100000.0, 115000.0],
            "gross_profit": [30000.0, 35400.0],
            "marketing_spend": [10000.0, 11000.0],
        }
    )
    healthy_rep = TruthLensService.analyze_dataframe(
        df=healthy_df,
        dataset_id="healthy_test",
        filename="healthy_q1_q2.csv",
    )
    assert healthy_rep.summary_counts.kpi_contradictions_count == 0

    # 2. Dataset with missing values and duplicate rows
    dirty_df = pd.DataFrame(
        {
            "category": ["A", "A", "B", "C"],
            "revenue": [100.0, 100.0, None, 250.0],
        }
    )
    dirty_rep = TruthLensService.analyze_dataframe(
        df=dirty_df,
        dataset_id="dirty_test",
        filename="dirty_sample.csv",
    )
    dq_findings = [f for f in dirty_rep.findings if f.category == "data_quality_problems"]
    assert len(dq_findings) == 1
    assert "missing" in dq_findings[0].what_happened.lower()
    assert "duplicate" in dq_findings[0].what_happened.lower()


def test_statistical_anomaly_clamps_non_negative_bounds_and_reports_z_only_breach(truthlens_settings):
    """Z-score-only breaches must not claim an IQR violation, and non-negative lower fences clamp to 0."""
    import numpy as np
    import pandas as pd
    from scipy import stats as sp_stats

    base = sp_stats.norm.ppf(np.linspace(0.02, 0.98, 60)) * 6.0 + 15.0
    values = np.append(base, 30.6)
    df = pd.DataFrame(
        {
            "region": [["North", "South", "East", "West"][i % 4] for i in range(len(values))],
            "days_since_last_purchase": np.round(values, 2),
        }
    )
    assert float(df["days_since_last_purchase"].min()) >= 0.0

    report = TruthLensService.analyze_dataframe(df=df, dataset_id="clamp_test", filename="clamp.csv")
    anomaly = next(f for f in report.findings if f.id == "tl_stat_anomaly_days_since_last_purchase")

    assert "within the wide non-parametric IQR fence" in anomaly.what_happened
    assert "outside the normal IQR bounds" not in anomaly.what_happened
    assert "[-" not in anomaly.supporting_evidence
    assert "clamped" in anomaly.supporting_evidence
    row = anomaly.evidence_table[0]
    assert row["Lower Bound (IQR)"].startswith("0.00")


def test_truthlens_api_endpoints_and_ui(truthlens_settings):
    """Verify REST endpoints for TruthLens scenarios, dataset reports, and dashboard HTML elements."""
    app = create_app(custom_settings=truthlens_settings)
    client = TestClient(app)

    # 1. List scenarios
    scen_res = client.get("/api/v1/truthlens/scenarios")
    assert scen_res.status_code == 200
    scenarios = scen_res.json()
    assert len(scenarios) == 3
    assert {s["scenario_key"] for s in scenarios} == {"scenario_a", "scenario_b", "scenario_c"}

    # 2. Load & analyze Scenario A via POST
    post_res = client.post("/api/v1/truthlens/scenarios/scenario_a")
    assert post_res.status_code == 200
    rep_a = post_res.json()
    assert rep_a["filename"] == "truthlens_scenario_a_revenue_profit.csv"
    assert rep_a["summary_counts"]["critical_count"] >= 1

    # 3. Fetch report via GET /{dataset_id}
    get_res = client.get(f"/api/v1/truthlens/{rep_a['dataset_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["dataset_id"] == rep_a["dataset_id"]

    # 4. Verify Dashboard UI includes TruthLens tab, Severity Filters, Dataset Trace View, and Modal
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    html = dash_res.text
    assert 'data-tab="tab-truthlens"' in html
    assert "truthlens-scenario-bar" in html
    assert "truthlens-severity-bar" in html
    assert "truthlens-trace-panel" in html
    assert "truthlens-trace-table" in html
    assert "tl-toggle-all-cards-btn" in html
    assert "truthlens-detail-dialog" in html


def test_truthlens_analytical_copy_lineage_and_chart_specs(truthlens_settings):
    """Verify anomaly direction copy, correlation causal direction, outlier row lineage, full-scan lineage, and chart_spec/source_rows."""
    import pandas as pd

    rows = [
        {"store": f"Store {i}", "region": ["West", "East", "South", "North"][i % 4], "revenue": 110000.0 + i * 1500.0, "marketing_spend": 18000.0 + i * 250.0, "customers": 1100 + i * 15, "satisfaction": 4.25 + (i % 3) * 0.05}
        for i in range(43)
    ]
    # Add upper-bound spike on marketing_spend (row #43) and lower-bound drop on satisfaction (row #44)
    rows.append({"store": "Los Angeles Century", "region": "West", "revenue": 185900.0, "marketing_spend": 49500.0, "customers": 1892, "satisfaction": 4.42})
    rows.append({"store": "Detroit Central", "region": "North", "revenue": 106700.0, "marketing_spend": 16900.0, "customers": 1073, "satisfaction": 3.10})
    df = pd.DataFrame(rows)

    report = TruthLensService.analyze_dataframe(df=df, dataset_id="exec_q3", filename="executive_q3_performance.csv")

    # 1. Anomaly direction copy & explicit outlier row lineage
    mkt_anom = next(f for f in report.findings if f.id == "tl_stat_anomaly_marketing_spend")
    assert "flagship campaign surge, bulk enterprise order, or duplicate ledger entry" in mkt_anom.why_it_matters
    assert "localized service disruption" not in mkt_anom.why_it_matters
    assert any("Row #43 • Los Angeles Century (Outlier)" in r for r in mkt_anom.supporting_row_references)
    assert len(mkt_anom.source_rows) >= 2
    assert mkt_anom.chart_spec is not None
    assert mkt_anom.chart_spec.reference_value is not None

    sat_anom = next(f for f in report.findings if f.id == "tl_stat_anomaly_satisfaction")
    assert "localized service disruption, fulfillment bottleneck, or partial-period telemetry truncation" in sat_anom.why_it_matters
    assert "flagship campaign surge" not in sat_anom.why_it_matters
    assert any("Row #44 • Detroit Central (Outlier)" in r for r in sat_anom.supporting_row_references)

    # 2. Correlation vs. Causation direction (customers/marketing_spend as driver -> revenue as outcome)
    corr_findings = [f for f in report.findings if f.category == "correlation_vs_causation"]
    assert len(corr_findings) >= 1
    cf = corr_findings[0]
    assert "scale jointly with store footprint size or local market tier" in cf.why_it_matters
    assert cf.chart_spec is not None
    assert cf.chart_spec.chart_type == "scatter"
    assert len(cf.chart_spec.datasets) == 2

    # 3. Full dataset scan lineage string (not truncated) & 2nd hypothesis for small sub-segment counts
    bias_finding = next(f for f in report.findings if f.id == "tl_sampling_small_subsegment_counts")
    assert bias_finding.supporting_row_references == ["Rows #0..#44 (Full Dataset Scan, n = 45)"]
    assert len(bias_finding.hypotheses) >= 2
    assert "Cross-Tabulation Sparsity Risk" in bias_finding.hypotheses[1]
    assert "additional categorical dimensions will further fracture cell counts" in bias_finding.hypotheses[1]


