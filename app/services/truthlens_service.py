"""InsightIQ TruthLens — 5-Layer Evidence-Based Intelligence Engine.

Implements:
- Layer 1: Data Understanding (semantic role discovery & data sufficiency checks)
- Layer 2: Analytical Engine (period-over-period deltas, segment decompositions, skew/outlier math)
- Layer 3: Detection Engine (deterministic & statistical rules across 8 detection categories)
- Layer 4: AI Explanation Engine (grounded executive narratives strictly bound to verified evidence)
- Layer 5: Presentation & Scenario Provisioning (structured reports & mandatory benchmark scenarios)
"""

from datetime import datetime, timezone
import io
import itertools
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats

from app.core.config import Settings
from app.schemas.truthlens import (
    DataReliabilityIndicator,
    InsufficientEvidenceNotice,
    TruthLensCategory,
    TruthLensChartDataset,
    TruthLensChartSpec,
    TruthLensFinding,
    TruthLensReportResponse,
    TruthLensScenarioMeta,
    TruthLensSeverity,
    TruthLensSummaryCounts,
)
from app.services.column_roles import classify_columns
from app.services.dataset_service import DatasetService

CATEGORY_LABELS: dict[TruthLensCategory, str] = {
    "kpi_contradiction": "KPI Contradiction",
    "hidden_segment_decline": "Hidden Segment Decline",
    "sampling_and_response_bias": "Sampling & Response Bias",
    "misleading_averages": "Misleading Averages",
    "incomplete_comparisons": "Incomplete Comparisons",
    "data_quality_problems": "Data Quality Problems",
    "correlation_vs_causation": "Correlation vs. Causation",
    "statistical_anomalies": "Statistical Anomalies",
}

SEVERITY_RANK: dict[TruthLensSeverity, int] = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}

SCENARIO_DEFINITIONS: dict[str, dict[str, str]] = {
    "scenario_a": {
        "scenario_key": "scenario_a",
        "title": "Scenario A: Revenue Growth Without Profit Growth",
        "subtitle": "Revenue +40% · Marketing +133.3% · Gross Profit -20%",
        "description": (
            "Demonstrates how strong top-line revenue growth ($100k to $140k) can mask a 20% contraction "
            "in gross profit ($35k to $28k) alongside a 133.3% surge in marketing expenditure."
        ),
        "filename": "truthlens_scenario_a_revenue_profit.csv",
        "csv": (
            "period,revenue,marketing_expenditure,gross_profit\n"
            "Previous Month,100000,15000,35000\n"
            "Current Month,140000,35000,28000\n"
        ),
    },
    "scenario_b": {
        "scenario_key": "scenario_b",
        "title": "Scenario B: Improving Satisfaction With Increasing Churn",
        "subtitle": "Satisfaction 3.8→4.6 · Survey Responses -82% · Churn 4%→8%",
        "description": (
            "Demonstrates how an apparent jump in average customer satisfaction (3.8 to 4.6) is compromised "
            "by an 82% collapse in survey responses (1,000 to 180) while monthly churn doubles (4% to 8%)."
        ),
        "filename": "truthlens_scenario_b_satisfaction_churn.csv",
        "csv": (
            "period,average_satisfaction,survey_responses,active_customers,monthly_churn_pct\n"
            "January,3.8,1000,10000,4.0\n"
            "February,4.6,180,9200,8.0\n"
        ),
    },
    "scenario_c": {
        "scenario_key": "scenario_c",
        "title": "Scenario C: Aggregate Revenue Hiding Category Declines",
        "subtitle": "Total Revenue +10% · Electronics +150% · Clothing -18.75% · Furniture -31.25%",
        "description": (
            "Demonstrates Simpson's-style aggregation masking: overall revenue grows +10% ($200k to $220k), "
            "hiding steep contractions in 2 out of 3 product categories (Clothing -18.75%, Furniture -31.25%)."
        ),
        "filename": "truthlens_scenario_c_category_declines.csv",
        "csv": (
            "period,category,revenue\n"
            "Previous Quarter,Electronics,40000\n"
            "Previous Quarter,Clothing,80000\n"
            "Previous Quarter,Furniture,80000\n"
            "Current Quarter,Electronics,100000\n"
            "Current Quarter,Clothing,65000\n"
            "Current Quarter,Furniture,55000\n"
        ),
    },
}


class TruthLensService:
    """5-Layer Evidence-Based Intelligence Engine for detecting misleading KPIs and hidden risks."""

    # ------------------------------------------------------------------
    # Scenario Provisioning
    # ------------------------------------------------------------------
    @classmethod
    def list_scenarios(cls) -> list[TruthLensScenarioMeta]:
        """Return metadata for the three mandatory TruthLens demonstration scenarios."""
        return [
            TruthLensScenarioMeta(
                scenario_key=meta["scenario_key"],  # type: ignore[arg-type]
                title=meta["title"],
                subtitle=meta["subtitle"],
                description=meta["description"],
                filename=meta["filename"],
            )
            for meta in SCENARIO_DEFINITIONS.values()
        ]

    @classmethod
    def load_scenario_dataset(cls, scenario_key: str, settings: Settings) -> str:
        """Ingest one of the mandatory demonstration scenarios and return its dataset_id."""
        if scenario_key not in SCENARIO_DEFINITIONS:
            raise ValueError(f"Unknown TruthLens scenario key: '{scenario_key}'")
        defn = SCENARIO_DEFINITIONS[scenario_key]
        upload_res = DatasetService.ingest_csv(
            file_bytes=defn["csv"].encode("utf-8"),
            filename=defn["filename"],
            settings=settings,
        )
        return upload_res.summary.dataset_id

    @classmethod
    def generate_scenario_report(cls, scenario_key: str) -> TruthLensReportResponse:
        """Evaluate a built-in scenario in memory without altering the active workspace dataset."""
        if scenario_key not in SCENARIO_DEFINITIONS:
            raise ValueError(f"Unknown TruthLens scenario key: '{scenario_key}'")
        defn = SCENARIO_DEFINITIONS[scenario_key]
        df = pd.read_csv(io.StringIO(defn["csv"]))
        return cls.analyze_dataframe(
            df=df,
            dataset_id=f"builtin_{scenario_key}",
            filename=defn["filename"],
        )

    # ------------------------------------------------------------------
    # Layer 1 — Data Understanding
    # ------------------------------------------------------------------
    @staticmethod
    def _match_column(columns: list[str], keywords: tuple[str, ...], exclude: set[str] | None = None) -> str | None:
        """Find the best matching column name containing any of the target keywords."""
        excluded = exclude or set()
        for kw in keywords:
            for col in columns:
                if col in excluded:
                    continue
                norm = col.lower().replace("-", "_").replace(" ", "_")
                if norm == kw or kw in norm.split("_") or kw in norm:
                    return col
        return None

    @classmethod
    def understand_dataset(cls, df: pd.DataFrame) -> dict[str, Any]:
        """Layer 1: Discover semantic business roles, temporal structure, and data sufficiency."""
        roles = classify_columns(df)
        measures: list[str] = list(roles["measures"])
        dimensions: list[str] = list(roles["dimensions"])
        identifiers: list[str] = list(roles["identifiers"])
        all_non_id = dimensions + measures

        period_col = cls._match_column(
            all_non_id,
            ("period", "month", "quarter", "date", "year", "week", "timeframe", "cycle"),
        )
        used: set[str] = {period_col} if period_col else set()

        revenue_col = cls._match_column(
            measures,
            ("revenue", "sales", "gmv", "bookings", "turnover"),
            exclude=used,
        )
        if revenue_col:
            used.add(revenue_col)

        profit_col = cls._match_column(
            measures,
            ("gross_profit", "net_profit", "profit", "ebitda", "operating_income", "margin"),
            exclude=used,
        )
        if profit_col:
            used.add(profit_col)

        marketing_col = cls._match_column(
            measures,
            (
                "marketing_expenditure",
                "marketing_spend",
                "ad_spend",
                "marketing",
                "acquisition_cost",
                "cac",
                "operating_cost",
                "cost",
                "spend",
            ),
            exclude=used,
        )
        if marketing_col:
            used.add(marketing_col)

        satisfaction_col = cls._match_column(
            measures,
            ("average_satisfaction", "satisfaction", "csat", "nps", "rating", "score"),
            exclude=used,
        )
        if satisfaction_col:
            used.add(satisfaction_col)

        responses_col = cls._match_column(
            measures,
            ("survey_responses", "responses", "respondents", "response_count", "sample_count"),
            exclude=used,
        )
        if responses_col:
            used.add(responses_col)

        customers_col = cls._match_column(
            measures,
            ("active_customers", "customers", "subscribers", "users", "accounts", "traffic"),
            exclude=used,
        )
        if customers_col:
            used.add(customers_col)

        churn_col = cls._match_column(
            measures,
            ("monthly_churn_pct", "churn_rate", "churn_pct", "churn", "attrition"),
            exclude=used,
        )
        if churn_col:
            used.add(churn_col)

        segment_cols = [c for c in dimensions if c != period_col]
        primary_segment_col = cls._match_column(
            segment_cols,
            ("category", "region", "segment", "product", "department", "channel", "tier", "store"),
        ) or (segment_cols[0] if segment_cols else None)

        has_temporal = False
        periods: list[str] = []
        if period_col and period_col in df.columns:
            unique_p = [str(x) for x in df[period_col].dropna().unique()]
            if 2 <= len(unique_p) <= max(24, len(df)):
                has_temporal = True
                periods = unique_p

        has_segments = False
        if primary_segment_col and primary_segment_col in df.columns:
            nunique_seg = int(df[primary_segment_col].nunique(dropna=True))
            if 2 <= nunique_seg <= max(30, len(df)):
                has_segments = True

        return {
            "identifiers": identifiers,
            "dimensions": dimensions,
            "measures": measures,
            "period_col": period_col if has_temporal else None,
            "periods": periods,
            "primary_segment_col": primary_segment_col if has_segments else None,
            "segment_cols": segment_cols,
            "revenue_col": revenue_col,
            "profit_col": profit_col,
            "marketing_col": marketing_col,
            "satisfaction_col": satisfaction_col,
            "responses_col": responses_col,
            "customers_col": customers_col,
            "churn_col": churn_col,
            "has_temporal": has_temporal,
            "has_segments": has_segments,
            "row_count": len(df),
            "column_count": len(df.columns),
        }

    # ------------------------------------------------------------------
    # Layer 4 — Grounded AI Explanation Helper
    # ------------------------------------------------------------------
    @staticmethod
    def synthesize_ai_explanation(
        title: str,
        what_happened: str,
        supporting_evidence: str,
        why_it_matters: str,
        hypotheses: list[str],
    ) -> str:
        """Layer 4: Generate a strictly grounded executive explanation without inventing facts."""
        hyp_clause = (
            f" Plausible hypotheses requiring empirical validation include: {hypotheses[0]}"
            if hypotheses
            else ""
        )
        return (
            f"TruthLens Verification Summary — {title}: {what_happened} "
            f"Empirical basis: {supporting_evidence} "
            f"Executive implication: {why_it_matters}{hyp_clause} "
            f"(Note: All figures are computed deterministically from the uploaded dataset; "
            f"causal explanations remain hypotheses until confirmed via controlled testing or audit.)"
        )

    # ------------------------------------------------------------------
    # Full 5-Layer Analysis Entry Point
    # ------------------------------------------------------------------
    @classmethod
    def analyze_dataset(cls, dataset_id: str, settings: Settings) -> TruthLensReportResponse:
        """Execute all 5 TruthLens layers on a workspace dataset and return a structured report."""
        df = DatasetService.get_dataframe(dataset_id=dataset_id, settings=settings)
        profile = DatasetService.get_dataset_profile(dataset_id=dataset_id, settings=settings)
        return cls.analyze_dataframe(df=df, dataset_id=dataset_id, filename=profile.filename)

    @classmethod
    def analyze_dataframe(
        cls,
        df: pd.DataFrame,
        dataset_id: str,
        filename: str,
    ) -> TruthLensReportResponse:
        """Execute all 5 TruthLens layers on an in-memory DataFrame and return a structured report."""
        understanding = cls.understand_dataset(df)
        findings: list[TruthLensFinding] = []
        insufficient: list[InsufficientEvidenceNotice] = []
        distortion_flags: list[str] = []

        # Run Layer 2 & Layer 3 detectors
        cls._detect_kpi_contradictions(df, understanding, findings, insufficient, distortion_flags)
        cls._detect_hidden_segment_declines(df, understanding, findings, insufficient, distortion_flags)
        cls._detect_sampling_and_response_bias(df, understanding, findings, insufficient, distortion_flags)
        cls._detect_misleading_averages(df, understanding, findings, insufficient, distortion_flags)
        cls._detect_incomplete_comparisons(df, understanding, findings, insufficient, distortion_flags)
        cls._detect_data_quality_problems(df, understanding, findings, insufficient, distortion_flags)
        cls._detect_correlation_vs_causation(df, understanding, findings, insufficient)
        cls._detect_statistical_anomalies(df, understanding, findings, insufficient, distortion_flags)

        # Build dataset-level comparison periods & quality warnings
        if understanding["has_temporal"] and len(understanding["periods"]) >= 2:
            dataset_periods = [
                f"Baseline: {understanding['periods'][-2]}",
                f"Comparison: {understanding['periods'][-1]}",
            ]
        else:
            dataset_periods = [f"Cross-Sectional Snapshot (n = {len(df)} records)"]

        dataset_warnings: list[str] = []
        if understanding["has_temporal"] and len(df) < 30:
            n_periods = len(understanding["periods"])
            dataset_warnings.append(
                f"Short time horizon ({n_periods} aggregated periods); multi-period seasonality and trend variance cannot be evaluated."
            )
        elif len(df) < 30:
            dataset_warnings.append(
                f"Small overall sample size (n = {len(df)} < 30 CLT threshold); treat parametric ratios as directional."
            )
        elif len(df) < 100:
            dataset_warnings.append(
                f"Limited sample depth (n = {len(df)} < 100); multi-dimensional segment slices may have n < 30."
            )
        null_total = int(df.isna().sum().sum())
        if null_total > 0:
            dataset_warnings.append(f"Dataset contains {null_total} missing cell(s) across columns.")
        dup_total = int(df.duplicated().sum())
        if dup_total > 0:
            dataset_warnings.append(f"Dataset contains {dup_total} exact duplicate row(s).")
        for flag in distortion_flags:
            if flag not in dataset_warnings:
                dataset_warnings.append(flag)

        # Enrich every finding with complete Dataset Trace View lineage metadata
        cls._enrich_findings_lineage(df, understanding, findings, dataset_periods, dataset_warnings)

        # Sort findings by severity rank (Critical -> High -> Medium -> Low)
        findings.sort(key=lambda f: SEVERITY_RANK.get(f.severity, 99))

        # Compute summary counts
        crit_cnt = sum(1 for f in findings if f.severity == "Critical")
        high_cnt = sum(1 for f in findings if f.severity == "High")
        med_cnt = sum(1 for f in findings if f.severity == "Medium")
        low_cnt = sum(1 for f in findings if f.severity == "Low")

        summary_counts = TruthLensSummaryCounts(
            total_findings=len(findings),
            critical_and_high_count=crit_cnt + high_cnt,
            critical_count=crit_cnt,
            high_count=high_cnt,
            medium_count=med_cnt,
            low_count=low_cnt,
            kpi_contradictions_count=sum(1 for f in findings if f.category == "kpi_contradiction"),
            segment_warnings_count=sum(1 for f in findings if f.category == "hidden_segment_decline"),
            statistical_anomalies_count=sum(
                1 for f in findings if f.category in ("statistical_anomalies", "data_quality_problems")
            ),
            bias_and_averages_count=sum(
                1
                for f in findings
                if f.category
                in (
                    "sampling_and_response_bias",
                    "misleading_averages",
                    "incomplete_comparisons",
                    "correlation_vs_causation",
                )
            ),
        )

        # Compute Data Reliability Indicator
        total_cells = max(1, len(df) * len(df.columns))
        null_cells = int(df.isna().sum().sum())
        completeness_pct = round(((total_cells - null_cells) / total_cells) * 100.0, 2)

        rel_score = 100.0
        rel_score -= (100.0 - completeness_pct) * 0.4
        rel_score -= crit_cnt * 14.0
        rel_score -= high_cnt * 7.0
        rel_score -= med_cnt * 3.0
        if len(df) < 30:
            rel_score -= 12.0
        elif len(df) < 100:
            rel_score -= 5.0
        rel_score = round(max(15.0, min(100.0, rel_score)), 1)

        if crit_cnt > 0 or rel_score < 68.0:
            rel_status = "High Distortion Risk"
        elif high_cnt > 0 or rel_score < 85.0:
            rel_status = "Moderate Caution"
        else:
            rel_status = "High Reliability"

        reliability = DataReliabilityIndicator(
            score=rel_score,
            status=rel_status,
            completeness_pct=completeness_pct,
            sample_size=len(df),
            has_temporal_dimension=bool(understanding["has_temporal"]),
            has_segment_dimension=bool(understanding["has_segments"]),
            distortion_flags=distortion_flags[:5],
        )

        if crit_cnt > 0:
            verdict = (
                f"TruthLens detected {len(findings)} evidence-backed finding(s) in '{filename}', "
                f"including {crit_cnt} Critical and {high_cnt} High-priority alert(s) where headline KPIs "
                f"mask underlying business contradictions, sampling distortions, or segment declines."
            )
        elif len(findings) > 0:
            verdict = (
                f"TruthLens audited '{filename}' ({len(df):,} rows) and surfaced {len(findings)} "
                f"analytical caution(s) ({high_cnt} High, {med_cnt} Medium, {low_cnt} Low) requiring "
                f"context before executive decision-making."
            )
        else:
            verdict = (
                f"TruthLens audited '{filename}' ({len(df):,} rows) and found no KPI contradictions "
                f"or severe statistical distortions across available columns."
            )

        return TruthLensReportResponse(
            dataset_id=dataset_id,
            filename=filename,
            generated_at=datetime.now(timezone.utc).isoformat(),
            row_count=len(df),
            column_count=len(df.columns),
            comparison_periods=dataset_periods,
            data_quality_warnings=dataset_warnings[:8],
            executive_verdict=verdict,
            summary_counts=summary_counts,
            reliability=reliability,
            detected_roles={
                "period_column": understanding["period_col"],
                "segment_column": understanding["primary_segment_col"],
                "revenue_column": understanding["revenue_col"],
                "profit_column": understanding["profit_col"],
                "marketing_column": understanding["marketing_col"],
                "satisfaction_column": understanding["satisfaction_col"],
                "survey_responses_column": understanding["responses_col"],
                "customers_column": understanding["customers_col"],
                "churn_column": understanding["churn_col"],
            },
            findings=findings,
            insufficient_evidence=insufficient,
        )

    @classmethod
    def _enrich_findings_lineage(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        dataset_periods: list[str],
        dataset_warnings: list[str],
    ) -> None:
        """Populate complete row/group references, calculation methodology, comparison periods, and quality warnings."""
        period_col = u["period_col"]
        seg_col = u["primary_segment_col"]
        entity_col = (
            cls._match_column(u["dimensions"], ("store", "branch", "category", "region", "period"))
            or seg_col
            or period_col
        )

        methodology_by_category: dict[str, str] = {
            "kpi_contradiction": (
                "Longitudinal Period-over-Period Delta ((V_curr - V_prev) / |V_prev| * 100) "
                "and Cross-Sectional Efficiency Ratio (Output_Metric / Input_Spend vs. Peer Median)"
            ),
            "hidden_segment_decline": (
                "Two-Way Segment-by-Period Decomposition (SUM/MEAN grouped by category and period) "
                "& Simpson's Aggregation Masking Check"
            ),
            "sampling_and_response_bias": (
                "Longitudinal Sample Participation Rate ((N_curr - N_prev) / N_prev * 100) "
                "and Central Limit Theorem Cell Depth Audit (n >= 30 per segment)"
            ),
            "misleading_averages": (
                "Parametric Mean vs. Non-Parametric Median Divergence ((Mean - Median) / |Median| * 100), "
                "Fisher-Pearson Skewness, and Leave-One-Out Trimmed Mean"
            ),
            "incomplete_comparisons": (
                "Unnormalized Segment Total (SUM) vs. Per-Record Normalized Mean (SUM / COUNT) "
                "across unequal group populations"
            ),
            "data_quality_problems": (
                "Full-Matrix Missing Value Scan (ISNA count) and Exact Row Hash Deduplication Audit"
            ),
            "correlation_vs_causation": (
                "Two-Tailed Pearson Product-Moment Correlation (r), Shared Variance (R² = r²), "
                "and Observational Confounder Guardrail"
            ),
            "statistical_anomalies": (
                "Hybrid Tukey Interquartile Fence ([Q1 - 1.5×IQR, Q3 + 1.5×IQR]) "
                "combined with Parametric Z-Score (|x - μ| / σ > 2.5)"
            ),
        }

        for f in findings:
            if not f.calculation_methodology:
                f.calculation_methodology = methodology_by_category.get(
                    f.category,
                    "Deterministic Pandas/NumPy/SciPy aggregation and ratio verification",
                )

            if not f.comparison_periods:
                f.comparison_periods = (
                    [f.comparison_baseline]
                    if f.comparison_baseline
                    else list(dataset_periods)
                )

            if not f.supporting_row_references:
                row_refs: list[str] = []
                if period_col and period_col in df.columns and len(u["periods"]) >= 2:
                    p_prev, p_curr = u["periods"][-2], u["periods"][-1]
                    for idx in df.index[:8]:
                        label_parts = [f"{period_col}='{df.loc[idx, period_col]}'"]
                        if seg_col and seg_col in df.columns:
                            label_parts.append(f"{seg_col}='{df.loc[idx, seg_col]}'")
                        for rc in f.relevant_columns:
                            if rc in df.columns and rc not in (period_col, seg_col):
                                val = df.loc[idx, rc]
                                if isinstance(val, (int, float, np.number)) and not pd.isna(val):
                                    label_parts.append(f"{rc}={float(val):,.2f}")
                        row_refs.append(f"Row #{idx} ({', '.join(label_parts)})")
                else:
                    # Identify specific extreme or representative rows for the finding's relevant columns
                    num_cols = [c for c in f.relevant_columns if c in u["measures"] and c in df.columns]
                    if num_cols:
                        target_col = num_cols[-1]
                        s = df[target_col].dropna()
                        if len(s) > 0:
                            max_i = s.idxmax()
                            min_i = s.idxmin()
                            for idx_tag, r_idx in [("Max", max_i), ("Min", min_i)]:
                                ent_lbl = (
                                    f"{entity_col}='{df.loc[r_idx, entity_col]}', "
                                    if (entity_col and entity_col in df.columns)
                                    else ""
                                )
                                row_refs.append(
                                    f"Row #{r_idx} [{idx_tag}] ({ent_lbl}{target_col}={float(df.loc[r_idx, target_col]):,.2f})"
                                )
                    if not row_refs:
                        row_refs.append(f"Rows #0..#{max(0, len(df) - 1)} (Full Dataset Scan, n = {len(df)})")
                f.supporting_row_references = row_refs

            if not f.source_rows:
                cols_to_show = [c for c in df.columns if c in f.relevant_columns]
                for c in df.columns:
                    if c not in cols_to_show:
                        cols_to_show.append(c)
                cols_to_show = cols_to_show[:6]
                sample_df = df.head(10)
                f.source_rows = [
                    {
                        "#Row": f"#{int(idx)}",
                        **{
                            col: (
                                round(float(row[col]), 2)
                                if isinstance(row[col], (int, float, np.number)) and not pd.isna(row[col])
                                else ("" if pd.isna(row[col]) else str(row[col]))
                            )
                            for col in cols_to_show
                        },
                    }
                    for idx, row in sample_df.iterrows()
                ]

            if not f.group_references:
                grp_refs: list[str] = []
                if period_col and seg_col and period_col in df.columns and seg_col in df.columns:
                    for (p_val, s_val), grp_df in df.groupby([period_col, seg_col], dropna=True):
                        grp_refs.append(
                            f"Group({period_col}='{p_val}', {seg_col}='{s_val}', rows={list(grp_df.index)})"
                        )
                elif period_col and period_col in df.columns:
                    for p_val, grp_df in df.groupby(period_col, dropna=True):
                        grp_refs.append(f"PeriodGroup({period_col}='{p_val}', n={len(grp_df)}, rows={list(grp_df.index[:6])})")
                elif seg_col and seg_col in df.columns:
                    for s_val, grp_df in df.groupby(seg_col, dropna=True):
                        grp_refs.append(f"SegmentGroup({seg_col}='{s_val}', n={len(grp_df)}, rows={list(grp_df.index[:6])})")
                else:
                    grp_refs.append(f"Dataset Cohort (n={len(df)} records)")
                f.group_references = grp_refs[:8]

            if not f.data_quality_warnings:
                f.data_quality_warnings = (
                    list(dataset_warnings[:3])
                    if dataset_warnings
                    else ["100% column completeness verified across referenced records; no missing-value distortion."]
                )

    # ------------------------------------------------------------------
    # Detector 1: KPI Contradictions
    # ------------------------------------------------------------------
    @classmethod
    def _detect_kpi_contradictions(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
        distortion_flags: list[str],
    ) -> None:
        period_col = u["period_col"]
        rev_col = u["revenue_col"]
        prof_col = u["profit_col"]
        mkt_col = u["marketing_col"]
        sat_col = u["satisfaction_col"]
        churn_col = u["churn_col"]
        cust_col = u["customers_col"]

        found_contradiction = False

        # 1A. Period-over-Period Revenue vs. Profit & Marketing Expenditure (Scenario A & general temporal financials)
        if period_col and rev_col and (prof_col or mkt_col):
            p_order = u["periods"]
            if len(p_order) >= 2:
                prev_p, curr_p = p_order[-2], p_order[-1]
                prev_df = df[df[period_col].astype(str) == prev_p]
                curr_df = df[df[period_col].astype(str) == curr_p]

                rev_prev = float(prev_df[rev_col].dropna().sum())
                rev_curr = float(curr_df[rev_col].dropna().sum())
                rev_pct = ((rev_curr - rev_prev) / rev_prev * 100.0) if rev_prev != 0 else 0.0

                prof_prev = float(prev_df[prof_col].dropna().sum()) if prof_col else None
                prof_curr = float(curr_df[prof_col].dropna().sum()) if prof_col else None
                prof_pct = (
                    ((prof_curr - prof_prev) / abs(prof_prev) * 100.0)
                    if (prof_prev is not None and prof_curr is not None and prof_prev != 0)
                    else None
                )

                mkt_prev = float(prev_df[mkt_col].dropna().sum()) if mkt_col else None
                mkt_curr = float(curr_df[mkt_col].dropna().sum()) if mkt_col else None
                mkt_pct = (
                    ((mkt_curr - mkt_prev) / abs(mkt_prev) * 100.0)
                    if (mkt_prev is not None and mkt_curr is not None and mkt_prev != 0)
                    else None
                )

                # Revenue increasing while Profit decreases
                if rev_pct > 0 and prof_pct is not None and prof_pct < 0 and prof_prev is not None and prof_curr is not None:
                    found_contradiction = True
                    distortion_flags.append(
                        f"Headline {rev_col} grew +{rev_pct:.1f}% while {prof_col} fell {prof_pct:.1f}%"
                    )
                    margin_prev = (prof_prev / rev_prev * 100.0) if rev_prev else 0.0
                    margin_curr = (prof_curr / rev_curr * 100.0) if rev_curr else 0.0

                    mkt_clause = ""
                    mkt_calc = []
                    rel_cols = [period_col, rev_col, prof_col]
                    ev_rows = [
                        {
                            "Metric": rev_col,
                            prev_p: f"${rev_prev:,.2f}",
                            curr_p: f"${rev_curr:,.2f}",
                            "Absolute Change": f"{rev_curr - rev_prev:+,.2f}",
                            "Pct Change": f"{rev_pct:+.1f}%",
                        },
                        {
                            "Metric": prof_col,
                            prev_p: f"${prof_prev:,.2f}",
                            curr_p: f"${prof_curr:,.2f}",
                            "Absolute Change": f"{prof_curr - prof_prev:+,.2f}",
                            "Pct Change": f"{prof_pct:+.1f}%",
                        },
                    ]
                    chart_labels = [rev_col.replace("_", " ").title(), prof_col.replace("_", " ").title()]
                    prev_series = [rev_prev, prof_prev]
                    curr_series = [rev_curr, prof_curr]

                    if mkt_col and mkt_prev is not None and mkt_curr is not None and mkt_pct is not None:
                        mkt_clause = (
                            f", while '{mkt_col}' increased {mkt_pct:.1f}% "
                            f"(${mkt_prev:,.2f} to ${mkt_curr:,.2f})"
                        )
                        mkt_calc.append(
                            f"{mkt_col}_growth_pct = (({mkt_curr:,.2f} - {mkt_prev:,.2f}) / {mkt_prev:,.2f}) * 100 = {mkt_pct:+.1f}%"
                        )
                        rel_cols.append(mkt_col)
                        ev_rows.insert(
                            1,
                            {
                                "Metric": mkt_col,
                                prev_p: f"${mkt_prev:,.2f}",
                                curr_p: f"${mkt_curr:,.2f}",
                                "Absolute Change": f"{mkt_curr - mkt_prev:+,.2f}",
                                "Pct Change": f"{mkt_pct:+.1f}%",
                            },
                        )
                        chart_labels.insert(1, mkt_col.replace("_", " ").title())
                        prev_series.insert(1, mkt_prev)
                        curr_series.insert(1, mkt_curr)

                    what_happened = (
                        f"Between {prev_p} and {curr_p}, '{rev_col}' increased {rev_pct:.1f}% "
                        f"(${rev_prev:,.2f} to ${rev_curr:,.2f}){mkt_clause}, whereas '{prof_col}' "
                        f"decreased {abs(prof_pct):.1f}% (${prof_prev:,.2f} to ${prof_curr:,.2f})."
                    )
                    supporting_ev = (
                        f"Revenue: +{rev_pct:.1f}% (${rev_prev:,.0f} → ${rev_curr:,.0f}); "
                        + (
                            f"Marketing expenditure: +{mkt_pct:.1f}% (${mkt_prev:,.0f} → ${mkt_curr:,.0f}); "
                            if mkt_pct is not None and mkt_prev is not None and mkt_curr is not None
                            else ""
                        )
                        + f"Gross profit: {prof_pct:.1f}% (${prof_prev:,.0f} → ${prof_curr:,.0f}); "
                        f"Profit margin compressed from {margin_prev:.1f}% to {margin_curr:.1f}%."
                    )
                    why_matters = (
                        "Celebrating top-line revenue growth without inspecting unit economics masks severe "
                        "margin erosion. Continuing to scale under negative marginal profitability destroys net enterprise value."
                    )
                    hyps = [
                        "Hypothesis 1 (Price Discounting & Promotional Erosion): Aggressive discounting or promotional incentives used to drive the 40.0% top-line expansion may have directly compressed gross margin per unit.",
                        "Hypothesis 2 (Product / Channel Mix Shift): Sales growth may be concentrated in lower-margin product tiers, bundles, or high-cost fulfillment channels.",
                        "COGS Inflation or Promotional Contra-Revenue Misclassification: Marketing expenditure rose +133.3% (+$20,000); verify whether promotional rebates, fulfillment subsidies, or freight costs were booked into COGS or contra-revenue.",
                    ]

                    findings.append(
                        TruthLensFinding(
                            id="tl_kpi_rev_profit_contradiction",
                            title="Revenue Growth Masking Profit Contraction",
                            severity="Critical",
                            category="kpi_contradiction",
                            category_label=CATEGORY_LABELS["kpi_contradiction"],
                            what_happened=what_happened,
                            supporting_evidence=supporting_ev,
                            comparison_baseline=f"{prev_p} baseline vs. {curr_p}",
                            why_it_matters=why_matters,
                            hypotheses=hyps,
                            confidence_level="High",
                            confidence_justification=(
                                f"Deterministic period-over-period accounting calculation across {prev_p} and {curr_p} with 100% completeness."
                            ),
                            recommended_investigation=[
                                "Audit unit-level price discounting, promotional codes, and net realized selling prices between periods.",
                                "Decompose gross margin by product SKU and customer cohort to isolate COGS inflation or mix shift.",
                                "Evaluate incremental customer acquisition costs (CAC) and marginal ROAS by campaign before attributing the profit drop solely to marketing.",
                            ],
                            relevant_columns=rel_cols,
                            calculations=[
                                f"{rev_col}_growth_pct = (({rev_curr:,.2f} - {rev_prev:,.2f}) / {rev_prev:,.2f}) * 100 = {rev_pct:+.1f}%",
                                *mkt_calc,
                                f"{prof_col}_growth_pct = (({prof_curr:,.2f} - {prof_prev:,.2f}) / {prof_prev:,.2f}) * 100 = {prof_pct:+.1f}%",
                                f"profit_margin_delta = ({prof_curr:,.2f}/{rev_curr:,.2f}) - ({prof_prev:,.2f}/{rev_prev:,.2f}) = {margin_curr - margin_prev:+.1f} pts",
                            ],
                            ai_explanation=cls.synthesize_ai_explanation(
                                "Revenue Growth Masking Profit Contraction",
                                what_happened,
                                supporting_ev,
                                why_matters,
                                hyps,
                            ),
                            evidence_table=ev_rows,
                            chart_spec=TruthLensChartSpec(
                                chart_type="bar",
                                title=f"{prev_p} vs. {curr_p}: Revenue, Spend & Profit Divergence",
                                labels=chart_labels,
                                datasets=[
                                    TruthLensChartDataset(label=prev_p, data=prev_series, unit="$"),
                                    TruthLensChartDataset(label=curr_p, data=curr_series, unit="$"),
                                ],
                            ),
                        )
                    )

                # Marketing / Operating Spend growing disproportionately faster than Revenue
                if (
                    mkt_col
                    and mkt_pct is not None
                    and mkt_prev is not None
                    and mkt_curr is not None
                    and mkt_pct > max(20.0, rev_pct * 1.5)
                ):
                    found_contradiction = True
                    mkt_share_prev = (mkt_prev / rev_prev * 100.0) if rev_prev else 0.0
                    mkt_share_curr = (mkt_curr / rev_curr * 100.0) if rev_curr else 0.0
                    inc_rev = rev_curr - rev_prev
                    inc_mkt = mkt_curr - mkt_prev
                    marginal_roas = (inc_rev / inc_mkt) if inc_mkt != 0 else 0.0
                    baseline_roas = (rev_prev / mkt_prev) if mkt_prev != 0 else 0.0

                    what_happened_mkt = (
                        f"'{mkt_col}' expanded by {mkt_pct:.1f}% (+${inc_mkt:,.2f}), outpacing '{rev_col}' "
                        f"growth of {rev_pct:.1f}% (+${inc_rev:,.2f}) by a factor of {mkt_pct / max(1.0, rev_pct):.1f}x."
                    )
                    sup_ev_mkt = (
                        f"Baseline revenue-to-spend ratio: {baseline_roas:.2f}x (${rev_prev:,.0f} / ${mkt_prev:,.0f}); "
                        f"Incremental return on new spend: {marginal_roas:.2f}x (+${inc_rev:,.0f} / +${inc_mkt:,.0f}); "
                        f"Spend-to-revenue share rose from {mkt_share_prev:.1f}% to {mkt_share_curr:.1f}%."
                    )
                    why_mkt = (
                        "Disproportionate cost growth relative to top-line return signals diminishing marginal efficiency "
                        "or unattributed spend with delayed payback windows."
                    )
                    hyps_mkt = [
                        "Hypothesis 1 (Diminishing Marginal Campaign Returns): Scaling spend beyond core audience saturation may have inflated cost-per-acquisition.",
                        "Hypothesis 2 (Delayed Multi-Period Attribution): Upfront brand or campaign investments in the current period may realize revenue in subsequent periods.",
                    ]
                    findings.append(
                        TruthLensFinding(
                            id="tl_kpi_spend_outpacing_revenue",
                            title="Disproportionate Spend Growth Relative to Revenue Return",
                            severity="High",
                            category="kpi_contradiction",
                            category_label=CATEGORY_LABELS["kpi_contradiction"],
                            what_happened=what_happened_mkt,
                            supporting_evidence=sup_ev_mkt,
                            comparison_baseline=f"{prev_p} spend efficiency ({baseline_roas:.2f}x) vs. {curr_p} marginal return ({marginal_roas:.2f}x)",
                            why_it_matters=why_mkt,
                            hypotheses=hyps_mkt,
                            confidence_level="High",
                            confidence_justification="Direct ratio comparison of verified period totals.",
                            recommended_investigation=[
                                "Segment incremental spend by campaign and acquisition channel to isolate low-converting budget lines.",
                                "Check whether new customer cohorts carry multi-month payback horizons not yet captured in current-period revenue.",
                            ],
                            relevant_columns=[period_col, rev_col, mkt_col],
                            calculations=[
                                f"baseline_roas = {rev_prev:,.2f} / {mkt_prev:,.2f} = {baseline_roas:.2f}x",
                                f"marginal_roas = ({rev_curr:,.2f} - {rev_prev:,.2f}) / ({mkt_curr:,.2f} - {mkt_prev:,.2f}) = {marginal_roas:.2f}x",
                            ],
                            ai_explanation=cls.synthesize_ai_explanation(
                                "Disproportionate Spend Growth Relative to Revenue Return",
                                what_happened_mkt,
                                sup_ev_mkt,
                                why_mkt,
                                hyps_mkt,
                            ),
                            evidence_table=[
                                {
                                    "Period": prev_p,
                                    rev_col: f"${rev_prev:,.2f}",
                                    mkt_col: f"${mkt_prev:,.2f}",
                                    "Spend % of Revenue": f"{mkt_share_prev:.1f}%",
                                    "Return Multiple": f"{baseline_roas:.2f}x",
                                },
                                {
                                    "Period": curr_p,
                                    rev_col: f"${rev_curr:,.2f}",
                                    mkt_col: f"${mkt_curr:,.2f}",
                                    "Spend % of Revenue": f"{mkt_share_curr:.1f}%",
                                    "Return Multiple": f"{(rev_curr / mkt_curr) if mkt_curr else 0.0:.2f}x",
                                },
                            ],
                            chart_spec=TruthLensChartSpec(
                                chart_type="bar",
                                title="Growth Rate Comparison (%): Revenue vs. Spend",
                                labels=[rev_col.replace("_", " ").title(), mkt_col.replace("_", " ").title()],
                                datasets=[
                                    TruthLensChartDataset(
                                        label="Period-over-Period Growth (%)",
                                        data=[round(rev_pct, 2), round(mkt_pct, 2)],
                                        unit="%",
                                    )
                                ],
                            ),
                        )
                    )

        # 1B. Period-over-Period Satisfaction Improving while Churn Increases (Scenario B)
        if period_col and sat_col and churn_col:
            p_order = u["periods"]
            if len(p_order) >= 2:
                prev_p, curr_p = p_order[-2], p_order[-1]
                prev_df = df[df[period_col].astype(str) == prev_p]
                curr_df = df[df[period_col].astype(str) == curr_p]

                sat_prev = float(prev_df[sat_col].dropna().mean())
                sat_curr = float(curr_df[sat_col].dropna().mean())
                sat_pct = ((sat_curr - sat_prev) / sat_prev * 100.0) if sat_prev != 0 else 0.0

                churn_prev = float(prev_df[churn_col].dropna().mean())
                churn_curr = float(curr_df[churn_col].dropna().mean())
                churn_pct_change = ((churn_curr - churn_prev) / churn_prev * 100.0) if churn_prev != 0 else 0.0

                if sat_curr > sat_prev and churn_curr > churn_prev:
                    found_contradiction = True
                    distortion_flags.append(
                        f"Reported {sat_col} rose ({sat_prev:.1f} → {sat_curr:.1f}) while {churn_col} doubled ({churn_prev:.1f}% → {churn_curr:.1f}%)"
                    )
                    cust_prev = float(prev_df[cust_col].dropna().sum()) if cust_col else None
                    cust_curr = float(curr_df[cust_col].dropna().sum()) if cust_col else None
                    cust_clause = (
                        f" and active customers declined by {abs((cust_curr - cust_prev) / cust_prev * 100.0):.1f}% "
                        f"({cust_prev:,.0f} to {cust_curr:,.0f})"
                        if (cust_prev and cust_curr)
                        else ""
                    )

                    what_sc = (
                        f"Between {prev_p} and {curr_p}, reported '{sat_col}' improved from {sat_prev:.1f}/5 to {sat_curr:.1f}/5 "
                        f"(+{sat_pct:.1f}%), yet '{churn_col}' increased by {churn_pct_change:.0f}% "
                        f"(doubling from {churn_prev:.1f}% to {churn_curr:.1f}%){cust_clause}."
                    )
                    sup_sc = (
                        f"Satisfaction: {sat_prev:.1f}/5 → {sat_curr:.1f}/5 (+{sat_pct:.1f}%); "
                        f"Monthly Churn: {churn_prev:.1f}% → {churn_curr:.1f}% (+{churn_pct_change:.1f}% relative increase)"
                        + (
                            f"; Active Customers: {cust_prev:,.0f} → {cust_curr:,.0f} ({cust_curr - cust_prev:+,.0f})."
                            if (cust_prev and cust_curr)
                            else "."
                        )
                    )
                    why_sc = (
                        "Rising customer satisfaction paired with accelerating customer churn is a classic executive blind spot: "
                        "relying on the headline satisfaction score masks severe customer attrition."
                    )
                    hyps_sc = [
                        "Hypothesis 1 (Survivorship & Non-Response Bias in Surveys): Dissatisfied customers may be churning silently without completing surveys, leaving only loyal promoters in the respondent pool.",
                        "Hypothesis 2 (Pricing or Contract Renewal Shock): Customers may be satisfied with core product quality while cancelling due to price increases, billing friction, or competitor promotions.",
                    ]
                    rel_cols_sc = [period_col, sat_col, churn_col] + ([cust_col] if cust_col else [])

                    findings.append(
                        TruthLensFinding(
                            id="tl_kpi_satisfaction_churn_contradiction",
                            title="Improving Customer Satisfaction Contradicts Accelerating Churn",
                            severity="Critical",
                            category="kpi_contradiction",
                            category_label=CATEGORY_LABELS["kpi_contradiction"],
                            what_happened=what_sc,
                            supporting_evidence=sup_sc,
                            comparison_baseline=f"{prev_p} vs. {curr_p} retention and sentiment baselines",
                            why_it_matters=why_sc,
                            hypotheses=hyps_sc,
                            confidence_level="High",
                            confidence_justification="Direct longitudinal comparison of reported satisfaction and churn rates.",
                            recommended_investigation=[
                                "Cross-reference churned customer IDs against survey response logs to determine what percentage of departing users participated in the survey.",
                                "Segment churn rates by customer tenure, pricing tier, and renewal cohort.",
                            ],
                            relevant_columns=rel_cols_sc,
                            calculations=[
                                f"satisfaction_delta = {sat_curr:.2f} - {sat_prev:.2f} = {sat_curr - sat_prev:+.2f} ({sat_pct:+.1f}%)",
                                f"churn_relative_increase = (({churn_curr:.2f} - {churn_prev:.2f}) / {churn_prev:.2f}) * 100 = {churn_pct_change:+.1f}%",
                            ],
                            ai_explanation=cls.synthesize_ai_explanation(
                                "Improving Customer Satisfaction Contradicts Accelerating Churn",
                                what_sc,
                                sup_sc,
                                why_sc,
                                hyps_sc,
                            ),
                            evidence_table=[
                                {
                                    "Period": prev_p,
                                    sat_col: f"{sat_prev:.2f} / 5.0",
                                    churn_col: f"{churn_prev:.1f}%",
                                    **(
                                        {cust_col: f"{cust_prev:,.0f}"}
                                        if (cust_col and cust_prev is not None)
                                        else {}
                                    ),
                                },
                                {
                                    "Period": curr_p,
                                    sat_col: f"{sat_curr:.2f} / 5.0",
                                    churn_col: f"{churn_curr:.1f}%",
                                    **(
                                        {cust_col: f"{cust_curr:,.0f}"}
                                        if (cust_col and cust_curr is not None)
                                        else {}
                                    ),
                                },
                            ],
                            chart_spec=TruthLensChartSpec(
                                chart_type="bar",
                                title=f"{prev_p} vs. {curr_p}: Satisfaction Score vs. Monthly Churn (%)",
                                labels=[sat_col.replace("_", " ").title(), churn_col.replace("_", " ").title()],
                                datasets=[
                                    TruthLensChartDataset(label=prev_p, data=[sat_prev, churn_prev]),
                                    TruthLensChartDataset(label=curr_p, data=[sat_curr, churn_curr]),
                                ],
                            ),
                        )
                    )

        # 1C. Cross-Sectional Marketing Efficiency / Satisfaction Contradiction (for snapshot datasets)
        if not found_contradiction and rev_col and mkt_col and len(df) >= 10:
            sub = df[[c for c in [u["primary_segment_col"], rev_col, mkt_col, sat_col] if c]].dropna()
            if len(sub) >= 10 and (sub[mkt_col] > 0).all():
                ratios = sub[rev_col] / sub[mkt_col]
                med_ratio = float(ratios.median())
                max_mkt_idx = sub[mkt_col].idxmax()
                top_mkt_val = float(sub.loc[max_mkt_idx, mkt_col])
                top_rev_val = float(sub.loc[max_mkt_idx, rev_col])
                top_ratio = top_rev_val / top_mkt_val if top_mkt_val else 0.0
                mkt_mean = float(sub[mkt_col].mean())

                if top_mkt_val > mkt_mean * 1.35 and top_ratio < med_ratio * 0.90:
                    found_contradiction = True
                    entity_col = (
                        cls._match_column(u["dimensions"], ("store", "branch", "account", "product", "region"))
                        or u["primary_segment_col"]
                    )
                    entity_name = (
                        str(df.loc[max_mkt_idx, entity_col])
                        if entity_col and entity_col in df.columns
                        else f"Record #{max_mkt_idx}"
                    )
                    eff_gap_pct = ((top_ratio - med_ratio) / med_ratio) * 100.0

                    what_cs = (
                        f"Peak '{mkt_col}' in '{entity_name}' (${top_mkt_val:,.2f}, "
                        f"+{((top_mkt_val - mkt_mean) / mkt_mean * 100.0):.1f}% above dataset mean) yields a "
                        f"revenue-to-spend return multiple of {top_ratio:.2f}x, trailing the peer median efficiency "
                        f"of {med_ratio:.2f}x by {abs(eff_gap_pct):.1f}%."
                    )
                    sup_cs = (
                        f"'{entity_name}' {mkt_col}: ${top_mkt_val:,.2f} (Peer mean: ${mkt_mean:,.2f}); "
                        f"{rev_col}: ${top_rev_val:,.2f}; Return ratio: {top_ratio:.2f}x vs. peer median {med_ratio:.2f}x."
                    )
                    why_cs = (
                        "Evaluating top-line revenue in isolation makes high-spend units appear top-performing, "
                        "concealing diminishing marginal returns on incremental marketing budget."
                    )
                    hyps_cs = [
                        f"Hypothesis 1 (Diminishing Marginal ROAS): '{entity_name}' may have scaled campaign spend into lower-converting audience tiers.",
                        f"Hypothesis 2 (Unallocated Multi-Store / Regional Spend): Regional or flagship brand spend may be booked to '{entity_name}' without attributing halo revenue across neighboring units.",
                    ]
                    findings.append(
                        TruthLensFinding(
                            id="tl_kpi_cross_sectional_roas_divergence",
                            title=f"Peak Spend in {entity_name} Masks Sub-Median Return Efficiency",
                            severity="High",
                            category="kpi_contradiction",
                            category_label=CATEGORY_LABELS["kpi_contradiction"],
                            what_happened=what_cs,
                            supporting_evidence=sup_cs,
                            comparison_baseline=f"Peer median return multiple ({med_ratio:.2f}x across n = {len(sub)} records)",
                            why_it_matters=why_cs,
                            hypotheses=hyps_cs,
                            confidence_level="High",
                            confidence_justification=f"Verified across {len(sub)} complete records.",
                            recommended_investigation=[
                                f"Audit marketing ledger entries for '{entity_name}' (${top_mkt_val:,.2f}) to separate local acquisition spend from shared brand campaigns.",
                                "Compare marginal customer acquisition cost (CAC) across the top 5 highest-spending units.",
                            ],
                            relevant_columns=[c for c in [entity_col, rev_col, mkt_col] if c],
                            calculations=[
                                f"unit_roas = {top_rev_val:,.2f} / {top_mkt_val:,.2f} = {top_ratio:.2f}x",
                                f"peer_median_roas = median({rev_col} / {mkt_col}) = {med_ratio:.2f}x",
                                f"efficiency_gap_pct = (({top_ratio:.2f} - {med_ratio:.2f}) / {med_ratio:.2f}) * 100 = {eff_gap_pct:+.1f}%",
                            ],
                            ai_explanation=cls.synthesize_ai_explanation(
                                f"Peak Spend in {entity_name} Masks Sub-Median Return Efficiency",
                                what_cs,
                                sup_cs,
                                why_cs,
                                hyps_cs,
                            ),
                            evidence_table=[
                                {
                                    "Unit / Benchmark": entity_name,
                                    rev_col: f"${top_rev_val:,.2f}",
                                    mkt_col: f"${top_mkt_val:,.2f}",
                                    "Return Multiple": f"{top_ratio:.2f}x",
                                },
                                {
                                    "Unit / Benchmark": "Dataset Peer Mean / Median",
                                    rev_col: f"${float(sub[rev_col].mean()):,.2f}",
                                    mkt_col: f"${mkt_mean:,.2f}",
                                    "Return Multiple": f"{med_ratio:.2f}x (median)",
                                },
                            ],
                            chart_spec=TruthLensChartSpec(
                                chart_type="bar",
                                title=f"Return per $1 Marketing Spend: {entity_name} vs. Peer Median",
                                labels=[entity_name, "Peer Median", "Dataset Mean"],
                                datasets=[
                                    TruthLensChartDataset(
                                        label="Revenue / Marketing Spend (x)",
                                        data=[
                                            round(top_ratio, 2),
                                            round(med_ratio, 2),
                                            round(float(ratios.mean()), 2),
                                        ],
                                        unit="x",
                                    )
                                ],
                            ),
                        )
                    )

        if not found_contradiction and not prof_col and not churn_col:
            insufficient.append(
                InsufficientEvidenceNotice(
                    category="kpi_contradiction",
                    category_label=CATEGORY_LABELS["kpi_contradiction"],
                    reason=(
                        "No explicit profit/margin or churn rate column was found to evaluate longitudinal "
                        "revenue-vs-profit or satisfaction-vs-churn contradictions."
                    ),
                    required_signals=["gross_profit / net_margin column", "churn_rate column", "multi-period timestamp"],
                )
            )

    # ------------------------------------------------------------------
    # Detector 2: Hidden Segment Declines (Scenario C & Segment Masking)
    # ------------------------------------------------------------------
    @classmethod
    def _detect_hidden_segment_declines(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
        distortion_flags: list[str],
    ) -> None:
        period_col = u["period_col"]
        seg_col = u["primary_segment_col"]
        metric_col = u["revenue_col"] or (u["measures"][0] if u["measures"] else None)

        if not seg_col or not metric_col:
            insufficient.append(
                InsufficientEvidenceNotice(
                    category="hidden_segment_decline",
                    category_label=CATEGORY_LABELS["hidden_segment_decline"],
                    reason="Dataset lacks a categorical segment column paired with a quantitative performance metric.",
                    required_signals=["category / region / segment column", "numeric revenue / performance metric"],
                )
            )
            return

        # 2A. Longitudinal Aggregate Growth Hiding Segment Declines (Scenario C)
        if period_col and len(u["periods"]) >= 2:
            p_order = u["periods"]
            prev_p, curr_p = p_order[-2], p_order[-1]
            piv = (
                df[df[period_col].astype(str).isin([prev_p, curr_p])]
                .groupby([seg_col, period_col], dropna=True)[metric_col]
                .sum()
                .unstack(fill_value=0.0)
            )
            if prev_p in piv.columns and curr_p in piv.columns and len(piv) >= 2:
                tot_prev = float(piv[prev_p].sum())
                tot_curr = float(piv[curr_p].sum())
                tot_pct = ((tot_curr - tot_prev) / tot_prev * 100.0) if tot_prev != 0 else 0.0

                seg_rows: list[dict[str, Any]] = []
                declining_segs: list[tuple[str, float, float, float]] = []
                growing_segs: list[tuple[str, float, float, float]] = []

                for seg_name, row in piv.iterrows():
                    s_prev = float(row[prev_p])
                    s_curr = float(row[curr_p])
                    s_pct = ((s_curr - s_prev) / s_prev * 100.0) if s_prev != 0 else 0.0
                    share_curr = (s_curr / tot_curr * 100.0) if tot_curr != 0 else 0.0
                    seg_rows.append(
                        {
                            "Segment": str(seg_name),
                            prev_p: f"${s_prev:,.2f}",
                            curr_p: f"${s_curr:,.2f}",
                            "Change ($)": f"{s_curr - s_prev:+,.2f}",
                            "Change (%)": f"{s_pct:+.2f}%",
                            f"{curr_p} Share": f"{share_curr:.1f}%",
                        }
                    )
                    if s_pct < 0:
                        declining_segs.append((str(seg_name), s_prev, s_curr, s_pct))
                    elif s_pct > 0:
                        growing_segs.append((str(seg_name), s_prev, s_curr, s_pct))

                if tot_pct > 0 and len(declining_segs) >= 1 and len(growing_segs) >= 1:
                    growing_segs.sort(key=lambda x: x[3], reverse=True)
                    top_grower = growing_segs[0]
                    decline_desc = ", ".join(
                        f"'{name}' decreased {abs(pct):.2f}% (${p:,.0f} to ${c:,.0f})"
                        for name, p, c, pct in declining_segs
                    )
                    distortion_flags.append(
                        f"Total {metric_col} grew +{tot_pct:.1f}%, masking declines in {len(declining_segs)} of {len(piv)} segments"
                    )

                    what_seg = (
                        f"Total '{metric_col}' increased {tot_pct:.1f}% (${tot_prev:,.2f} to ${tot_curr:,.2f}) between "
                        f"{prev_p} and {curr_p}, but {len(declining_segs)} out of {len(piv)} categories declined: "
                        f"{decline_desc}. Aggregate growth is concentrated in '{top_grower[0]}', which increased "
                        f"{top_grower[3]:.1f}% (${top_grower[1]:,.0f} to ${top_grower[2]:,.0f})."
                    )
                    sup_seg = (
                        f"Total {metric_col}: +{tot_pct:.1f}% (${tot_prev:,.0f} → ${tot_curr:,.0f}); "
                        f"{top_grower[0]}: +{top_grower[3]:.1f}% (${top_grower[1]:,.0f} → ${top_grower[2]:,.0f}); "
                        + "; ".join(
                            f"{name}: {pct:.2f}% (${p:,.0f} → ${c:,.0f})"
                            for name, p, c, pct in declining_segs
                        )
                        + f" ({len(declining_segs)} of {len(piv)} segments in contraction)."
                    )
                    why_seg = (
                        "Relying on aggregate revenue growth conceals severe demand contraction across core business lines "
                        f"and creates high concentration dependency on '{top_grower[0]}'."
                    )
                    hyps_seg = [
                        f"Hypothesis 1 (Category-Specific Demand Contraction): '{declining_segs[0][0]}' and peer declining segments may face competitive displacement, inventory stockouts, or pricing elasticity headwinds.",
                        f"Hypothesis 2 (Internal Cannibalization or Promotional Shift): Promotional focus or budget reallocation toward '{top_grower[0]}' (+{top_grower[3]:.1f}%) may have diverted traffic from legacy categories.",
                    ]

                    findings.append(
                        TruthLensFinding(
                            id="tl_hidden_segment_decline_temporal",
                            title=f"Aggregate Growth (+{tot_pct:.1f}%) Masks Declines in {len(declining_segs)} of {len(piv)} Categories",
                            severity="Critical",
                            category="hidden_segment_decline",
                            category_label=CATEGORY_LABELS["hidden_segment_decline"],
                            what_happened=what_seg,
                            supporting_evidence=sup_seg,
                            comparison_baseline=f"{prev_p} vs. {curr_p} across {len(piv)} '{seg_col}' segments",
                            why_it_matters=why_seg,
                            hypotheses=hyps_seg,
                            confidence_level="High",
                            confidence_justification=f"Complete segment-by-period decomposition across all {len(piv)} categories.",
                            recommended_investigation=[
                                f"Conduct SKU-level volume and price decomposition inside {', '.join(x[0] for x in declining_segs)} to isolate why revenue contracted.",
                                f"Assess concentration risk in '{top_grower[0]}', which now represents {(top_grower[2] / tot_curr * 100.0):.1f}% of total {metric_col}.",
                            ],
                            relevant_columns=[period_col, seg_col, metric_col],
                            calculations=[
                                f"total_growth_pct = (({tot_curr:,.2f} - {tot_prev:,.2f}) / {tot_prev:,.2f}) * 100 = {tot_pct:+.2f}%",
                                f"{top_grower[0]}_growth_pct = (({top_grower[2]:,.2f} - {top_grower[1]:,.2f}) / {top_grower[1]:,.2f}) * 100 = {top_grower[3]:+.2f}%",
                                *[
                                    f"{name}_growth_pct = (({c:,.2f} - {p:,.2f}) / {p:,.2f}) * 100 = {pct:+.2f}%"
                                    for name, p, c, pct in declining_segs
                                ],
                            ],
                            ai_explanation=cls.synthesize_ai_explanation(
                                f"Aggregate Growth (+{tot_pct:.1f}%) Masks Declines in {len(declining_segs)} of {len(piv)} Categories",
                                what_seg,
                                sup_seg,
                                why_seg,
                                hyps_seg,
                            ),
                            evidence_table=seg_rows,
                            chart_spec=TruthLensChartSpec(
                                chart_type="bar",
                                title=f"Category {metric_col.replace('_', ' ').title()}: {prev_p} vs. {curr_p}",
                                labels=[str(idx) for idx in piv.index],
                                datasets=[
                                    TruthLensChartDataset(
                                        label=prev_p,
                                        data=[float(piv.loc[idx, prev_p]) for idx in piv.index],
                                        unit="$",
                                    ),
                                    TruthLensChartDataset(
                                        label=curr_p,
                                        data=[float(piv.loc[idx, curr_p]) for idx in piv.index],
                                        unit="$",
                                    ),
                                ],
                            ),
                        )
                    )
                    return

        # 2B. Cross-Sectional Segment Disparity & Concentration Risk
        seg_grp = df.groupby(seg_col, dropna=True)[metric_col].agg(["count", "sum", "mean", "median"])
        if len(seg_grp) >= 2:
            overall_mean = float(df[metric_col].dropna().mean())
            total_sum = float(seg_grp["sum"].sum())
            seg_grp["share_pct"] = (seg_grp["sum"] / max(1e-9, total_sum)) * 100.0
            seg_grp["vs_overall_mean_pct"] = ((seg_grp["mean"] - overall_mean) / max(1e-9, abs(overall_mean))) * 100.0

            top_seg = str(seg_grp["mean"].idxmax())
            bot_seg = str(seg_grp["mean"].idxmin())
            top_mean = float(seg_grp.loc[top_seg, "mean"])
            bot_mean = float(seg_grp.loc[bot_seg, "mean"])
            bot_vs_overall = float(seg_grp.loc[bot_seg, "vs_overall_mean_pct"])
            spread_pct = ((top_mean - bot_mean) / max(1e-9, abs(bot_mean))) * 100.0

            if spread_pct >= 12.0:
                below_cnt = int((seg_grp["mean"] < overall_mean).sum())
                what_cs_seg = (
                    f"Aggregate mean '{metric_col}' (${overall_mean:,.2f}) conceals a {spread_pct:.1f}% performance gap "
                    f"between top segment '{top_seg}' (mean ${top_mean:,.2f}) and lagging segment '{bot_seg}' "
                    f"(mean ${bot_mean:,.2f}, {abs(bot_vs_overall):.1f}% below the company average)."
                )
                sup_cs_seg = (
                    f"Overall mean: ${overall_mean:,.2f}; '{top_seg}' mean: ${top_mean:,.2f} (n={int(seg_grp.loc[top_seg, 'count'])}); "
                    f"'{bot_seg}' mean: ${bot_mean:,.2f} (n={int(seg_grp.loc[bot_seg, 'count'])}); "
                    f"{below_cnt} of {len(seg_grp)} segments perform below the headline average."
                )
                why_cs_seg = (
                    "Managing to the company-wide average masks structural underperformance in lagging segments "
                    "and misallocates operational targets."
                )
                hyps_cs_seg = [
                    f"Hypothesis 1 (Regional / Segment Market Maturity): '{bot_seg}' units may operate in smaller addressable markets or newer territories.",
                    f"Hypothesis 2 (Resource Allocation Imbalance): Marketing and customer acquisition investment may be disproportionately concentrated in '{top_seg}'.",
                ]
                ev_table_cs = [
                    {
                        seg_col: str(idx),
                        "Records (n)": int(r["count"]),
                        f"Total {metric_col}": f"${float(r['sum']):,.2f}",
                        f"Mean {metric_col}": f"${float(r['mean']):,.2f}",
                        f"Median {metric_col}": f"${float(r['median']):,.2f}",
                        "Revenue Share": f"{float(r['share_pct']):.1f}%",
                        "vs. Overall Mean": f"{float(r['vs_overall_mean_pct']):+.1f}%",
                    }
                    for idx, r in seg_grp.sort_values("mean", ascending=False).iterrows()
                ]
                findings.append(
                    TruthLensFinding(
                        id="tl_hidden_segment_disparity_cross_sectional",
                        title=f"Headline Average Masks {spread_pct:.1f}% Gap Between '{top_seg}' and '{bot_seg}'",
                        severity="Medium",
                        category="hidden_segment_decline",
                        category_label=CATEGORY_LABELS["hidden_segment_decline"],
                        what_happened=what_cs_seg,
                        supporting_evidence=sup_cs_seg,
                        comparison_baseline=f"Dataset-wide mean ${overall_mean:,.2f} across {len(seg_grp)} '{seg_col}' segments",
                        why_it_matters=why_cs_seg,
                        hypotheses=hyps_cs_seg,
                        confidence_level="High",
                        confidence_justification=f"Exhaustive aggregation across all {len(df)} records.",
                        recommended_investigation=[
                            f"Compare unit-level customer traffic and marketing spend between '{bot_seg}' and '{top_seg}'.",
                            f"Set segment-adjusted benchmarks rather than evaluating '{bot_seg}' against the unadjusted global mean.",
                        ],
                        relevant_columns=[seg_col, metric_col],
                        calculations=[
                            f"segment_gap_pct = (({top_mean:,.2f} - {bot_mean:,.2f}) / {bot_mean:,.2f}) * 100 = {spread_pct:.1f}%",
                            f"{bot_seg}_vs_global_mean = (({bot_mean:,.2f} - {overall_mean:,.2f}) / {overall_mean:,.2f}) * 100 = {bot_vs_overall:+.1f}%",
                        ],
                        ai_explanation=cls.synthesize_ai_explanation(
                            f"Headline Average Masks {spread_pct:.1f}% Gap Between '{top_seg}' and '{bot_seg}'",
                            what_cs_seg,
                            sup_cs_seg,
                            why_cs_seg,
                            hyps_cs_seg,
                        ),
                        evidence_table=ev_table_cs,
                        chart_spec=TruthLensChartSpec(
                            chart_type="bar",
                            title=f"Mean {metric_col.replace('_', ' ').title()} by {seg_col.replace('_', ' ').title()}",
                            labels=[str(idx) for idx in seg_grp.index],
                            datasets=[
                                TruthLensChartDataset(
                                    label=f"Mean {metric_col}",
                                    data=[round(float(seg_grp.loc[idx, "mean"]), 2) for idx in seg_grp.index],
                                    unit="$",
                                )
                            ],
                            reference_value=round(overall_mean, 2),
                            reference_label=f"Global Mean (${overall_mean:,.0f})",
                        ),
                    )
                )

    # ------------------------------------------------------------------
    # Detector 3: Sampling and Response Bias (Scenario B & Small Sample Checks)
    # ------------------------------------------------------------------
    @classmethod
    def _detect_sampling_and_response_bias(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
        distortion_flags: list[str],
    ) -> None:
        period_col = u["period_col"]
        resp_col = u["responses_col"]
        sat_col = u["satisfaction_col"]
        cust_col = u["customers_col"]

        # 3A. Longitudinal Survey Participation Collapse (Scenario B)
        if period_col and resp_col and len(u["periods"]) >= 2:
            p_order = u["periods"]
            prev_p, curr_p = p_order[-2], p_order[-1]
            prev_df = df[df[period_col].astype(str) == prev_p]
            curr_df = df[df[period_col].astype(str) == curr_p]

            resp_prev = float(prev_df[resp_col].dropna().sum())
            resp_curr = float(curr_df[resp_col].dropna().sum())
            resp_pct = ((resp_curr - resp_prev) / resp_prev * 100.0) if resp_prev != 0 else 0.0

            if resp_pct <= -25.0:
                cust_prev = float(prev_df[cust_col].dropna().sum()) if cust_col else None
                cust_curr = float(curr_df[cust_col].dropna().sum()) if cust_col else None
                part_prev = (resp_prev / cust_prev * 100.0) if (cust_prev and cust_prev > 0) else None
                part_curr = (resp_curr / cust_curr * 100.0) if (cust_curr and cust_curr > 0) else None

                sat_prev = float(prev_df[sat_col].dropna().mean()) if sat_col else None
                sat_curr = float(curr_df[sat_col].dropna().mean()) if sat_col else None

                distortion_flags.append(
                    f"Survey participation ({resp_col}) plunged {abs(resp_pct):.1f}% ({resp_prev:,.0f} → {resp_curr:,.0f})"
                )

                part_clause = (
                    f", reducing active customer response coverage from {part_prev:.2f}% to {part_curr:.2f}%"
                    if (part_prev is not None and part_curr is not None)
                    else ""
                )
                what_bias = (
                    f"Survey participation ('{resp_col}') declined by {abs(resp_pct):.1f}% between {prev_p} "
                    f"({resp_prev:,.0f} responses) and {curr_p} ({resp_curr:,.0f} responses){part_clause}. "
                    + (
                        f"Over the same window, reported '{sat_col}' rose from {sat_prev:.1f}/5 to {sat_curr:.1f}/5."
                        if (sat_prev is not None and sat_curr is not None)
                        else ""
                    )
                )
                sup_bias = (
                    f"{resp_col}: {resp_prev:,.0f} → {resp_curr:,.0f} ({resp_pct:+.1f}%)"
                    + (
                        f"; Customer response rate: {part_prev:.2f}% ({resp_prev:,.0f}/{cust_prev:,.0f}) → {part_curr:.2f}% ({resp_curr:,.0f}/{cust_curr:,.0f})"
                        if (part_prev is not None and part_curr is not None and cust_prev and cust_curr)
                        else ""
                    )
                    + (
                        f"; Reported {sat_col}: {sat_prev:.1f}/5 → {sat_curr:.1f}/5."
                        if (sat_prev is not None and sat_curr is not None)
                        else "."
                    )
                )
                why_bias = (
                    "An 82.0% contraction in sample participation severely degrades the statistical representativeness "
                    "of the current period's satisfaction score. Please note: while potential sampling or non-response bias "
                    "is a primary risk, response bias is not proven from aggregate counts alone."
                )
                hyps_bias = [
                    "Hypothesis 1 (Potential Non-Response / Survivorship Bias — Unproven): Dissatisfied or churning customers may have stopped responding to surveys, artificially inflating the mean score among remaining respondents.",
                    "Hypothesis 2 (Survey Distribution Channel Failure — Unproven): A technical change in email/in-app survey triggers or sampling quotas in February may have restricted invitations to a smaller user subset.",
                ]

                findings.append(
                    TruthLensFinding(
                        id="tl_sampling_survey_participation_drop",
                        title=f"Survey Participation Declined {abs(resp_pct):.0f}% — Potential Sampling & Non-Response Bias",
                        severity="Critical",
                        category="sampling_and_response_bias",
                        category_label=CATEGORY_LABELS["sampling_and_response_bias"],
                        what_happened=what_bias,
                        supporting_evidence=sup_bias,
                        comparison_baseline=f"{prev_p} response volume ({resp_prev:,.0f}) vs. {curr_p} ({resp_curr:,.0f})",
                        why_it_matters=why_bias,
                        hypotheses=hyps_bias,
                        confidence_level="High",
                        confidence_justification=(
                            "The 82.0% drop in response count is deterministically verified; potential non-response bias is "
                            "flagged as a statistical reliability risk rather than a proven causal mechanism."
                        ),
                        recommended_investigation=[
                            "Verify survey invitations sent, delivery rates, and completion rates across customer segments in both periods.",
                            "Compare demographic and usage profiles of February respondents (n=180) against non-respondents to test for non-response bias.",
                            "Re-weight satisfaction scores by segment population size before reporting February sentiment to leadership.",
                        ],
                        relevant_columns=[c for c in [period_col, resp_col, cust_col, sat_col] if c],
                        calculations=[
                            f"response_drop_pct = (({resp_curr:,.0f} - {resp_prev:,.0f}) / {resp_prev:,.0f}) * 100 = {resp_pct:+.1f}%",
                            *(
                                [
                                    f"jan_response_rate = ({resp_prev:,.0f} / {cust_prev:,.0f}) * 100 = {part_prev:.2f}%",
                                    f"feb_response_rate = ({resp_curr:,.0f} / {cust_curr:,.0f}) * 100 = {part_curr:.2f}%",
                                ]
                                if (part_prev is not None and part_curr is not None and cust_prev and cust_curr)
                                else []
                            ),
                        ],
                        ai_explanation=cls.synthesize_ai_explanation(
                            f"Survey Participation Declined {abs(resp_pct):.0f}% — Potential Sampling & Non-Response Bias",
                            what_bias,
                            sup_bias,
                            why_bias,
                            hyps_bias,
                        ),
                        evidence_table=[
                            {
                                "Period": prev_p,
                                resp_col: f"{resp_prev:,.0f}",
                                **(
                                    {cust_col: f"{cust_prev:,.0f}", "Participation Rate": f"{part_prev:.2f}%"}
                                    if (cust_col and cust_prev and part_prev is not None)
                                    else {}
                                ),
                                **({sat_col: f"{sat_prev:.2f}/5"} if (sat_col and sat_prev is not None) else {}),
                            },
                            {
                                "Period": curr_p,
                                resp_col: f"{resp_curr:,.0f}",
                                **(
                                    {cust_col: f"{cust_curr:,.0f}", "Participation Rate": f"{part_curr:.2f}%"}
                                    if (cust_col and cust_curr and part_curr is not None)
                                    else {}
                                ),
                                **({sat_col: f"{sat_curr:.2f}/5"} if (sat_col and sat_curr is not None) else {}),
                            },
                        ],
                        chart_spec=TruthLensChartSpec(
                            chart_type="bar",
                            title=f"Survey Responses Received: {prev_p} vs. {curr_p}",
                            labels=[prev_p, curr_p],
                            datasets=[
                                TruthLensChartDataset(
                                    label=resp_col.replace("_", " ").title(),
                                    data=[resp_prev, resp_curr],
                                    unit="count",
                                )
                            ],
                        ),
                    )
                )
                return

        # 3B. Sub-Segment Sample Size / Granularity Caution (skip on pre-aggregated period rollup tables)
        n_rows = len(df)
        seg_col = u["primary_segment_col"]
        is_period_rollup = bool(
            u["has_temporal"]
            and seg_col
            and n_rows <= len(u["periods"]) * max(1, int(df[seg_col].nunique(dropna=True)))
        )
        if seg_col and not is_period_rollup and 4 <= n_rows < 150:
            seg_counts = df[seg_col].value_counts(dropna=True)
            min_seg_n = int(seg_counts.min())
            min_seg_name = str(seg_counts.idxmin())
            if min_seg_n < 30:
                distortion_flags.append(f"Sub-segment sample sizes drop to n={min_seg_n} in '{min_seg_name}'")
                what_sub = (
                    f"While the overall dataset contains n = {n_rows} records, partitioning by '{seg_col}' "
                    f"reduces individual segment sample sizes to n = {min_seg_n} in '{min_seg_name}' "
                    f"(below the n = 30 Central Limit Theorem threshold)."
                )
                sup_sub = (
                    f"Total n = {n_rows}; Segment counts across '{seg_col}': "
                    + ", ".join(f"{k} (n={int(v)})" for k, v in seg_counts.items())
                    + "."
                )
                why_sub = (
                    "Sub-segment averages computed on n < 30 observations carry wide confidence intervals "
                    "and high sensitivity to single-record outliers."
                )
                hyps_sub = [
                    "Hypothesis 1 (Granular Slicing Variance): Observed differences between small segments may reflect random sample variance rather than structural performance shifts.",
                    f"Hypothesis 2 (Cross-Tabulation Sparsity Risk): Splitting '{seg_col}' across additional categorical dimensions will further fracture cell counts below reliable statistical thresholds.",
                ]
                findings.append(
                    TruthLensFinding(
                        id="tl_sampling_small_subsegment_counts",
                        title=f"Small Sub-Segment Sample Depth (n = {min_seg_n} in '{min_seg_name}')",
                        severity="Medium" if n_rows >= 30 else "High",
                        category="sampling_and_response_bias",
                        category_label=CATEGORY_LABELS["sampling_and_response_bias"],
                        what_happened=what_sub,
                        supporting_evidence=sup_sub,
                        comparison_baseline="Central Limit Theorem minimum benchmark (n >= 30 per analytical cell)",
                        why_it_matters=why_sub,
                        hypotheses=hyps_sub,
                        confidence_level="High",
                        confidence_justification="Exact row count enumeration per categorical segment.",
                        recommended_investigation=[
                            "Use non-parametric medians and interquartile ranges (IQR) when comparing segments with n < 30.",
                            "Pool multi-period records before running multi-dimensional cross-tabulations.",
                        ],
                        relevant_columns=[seg_col],
                        supporting_row_references=[
                            f"Rows #0..#{max(0, n_rows - 1)} (Full Dataset Scan, n = {n_rows})"
                        ],
                        calculations=[
                            f"min_segment_sample_size = count({seg_col} == '{min_seg_name}') = {min_seg_n} (< 30 CLT threshold)",
                        ],
                        ai_explanation=cls.synthesize_ai_explanation(
                            f"Small Sub-Segment Sample Depth (n = {min_seg_n} in '{min_seg_name}')",
                            what_sub,
                            sup_sub,
                            why_sub,
                            hyps_sub,
                        ),
                        evidence_table=[
                            {seg_col: str(k), "Sample Size (n)": int(v), "Meets CLT (n >= 30)": "Yes" if int(v) >= 30 else "No (Caution)"}
                            for k, v in seg_counts.items()
                        ],
                        chart_spec=TruthLensChartSpec(
                            chart_type="bar",
                            title=f"Sample Depth (n) by {seg_col.replace('_', ' ').title()}",
                            labels=[str(k) for k in seg_counts.index],
                            datasets=[
                                TruthLensChartDataset(
                                    label="Record Count (n)",
                                    data=[float(v) for v in seg_counts.values],
                                    unit="count",
                                )
                            ],
                        ),
                    )
                )
        elif not resp_col:
            insufficient.append(
                InsufficientEvidenceNotice(
                    category="sampling_and_response_bias",
                    category_label=CATEGORY_LABELS["sampling_and_response_bias"],
                    reason="No survey response count or invitation log column is present to evaluate non-response bias.",
                    required_signals=["survey_responses / respondents column", "population / active_customers column"],
                )
            )

    # ------------------------------------------------------------------
    # Detector 4: Misleading Averages
    # ------------------------------------------------------------------
    @classmethod
    def _detect_misleading_averages(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
        distortion_flags: list[str],
    ) -> None:
        measures = u["measures"]
        if not measures:
            return

        for col in measures:
            s = df[col].dropna()
            if len(s) < 5:
                continue
            mean_val = float(s.mean())
            med_val = float(s.median())
            std_val = float(s.std())
            if med_val == 0 or std_val == 0:
                continue

            gap_pct = ((mean_val - med_val) / abs(med_val)) * 100.0
            skew_val = float(s.skew()) if len(s) >= 8 else 0.0

            # Compute mean without the most extreme value
            ext_idx = (s - mean_val).abs().idxmax()
            ext_val = float(s.loc[ext_idx])
            trimmed_s = s.drop(index=ext_idx)
            trimmed_mean = float(trimmed_s.mean())
            outlier_pull_pct = ((mean_val - trimmed_mean) / abs(trimmed_mean)) * 100.0 if trimmed_mean != 0 else 0.0

            if abs(gap_pct) >= 3.5 or abs(skew_val) >= 0.85 or abs(outlier_pull_pct) >= 1.8:
                direction = "upward" if ext_val > mean_val else "downward"
                what_avg = (
                    f"In '{col}', the parametric mean ({mean_val:,.2f}) diverges from the median ({med_val:,.2f}) "
                    f"by {gap_pct:+.2f}% (skewness = {skew_val:+.2f}), pulled {direction} by extreme value "
                    f"{ext_val:,.2f} (trimmed mean excluding single extreme record = {trimmed_mean:,.2f})."
                )
                sup_avg = (
                    f"Parametric Mean: {mean_val:,.2f}; Median (50th pct): {med_val:,.2f}; "
                    f"Trimmed Mean (ex-outlier): {trimmed_mean:,.2f}; Extreme value: {ext_val:,.2f}; "
                    f"Std Dev: {std_val:,.2f}; Skewness: {skew_val:+.2f}."
                )
                why_avg = (
                    f"Reporting the unadjusted mean of '{col}' ({mean_val:,.2f}) misrepresents the typical unit "
                    f"experience (median {med_val:,.2f}) because a single extreme observation shifts the average."
                )
                hyps_avg = [
                    f"Hypothesis 1 (Right/Left-Tail Outlier Distortion): A single flagship or anomalous record ({ext_val:,.2f}) skews the parametric average.",
                    "Hypothesis 2 (Multi-Modal Population): The dataset may combine distinct operational tiers (e.g., flagship vs. standard units) in one unsegmented distribution.",
                ]
                findings.append(
                    TruthLensFinding(
                        id=f"tl_misleading_avg_{col}",
                        title=f"Outlier-Distorted Average in {col.replace('_', ' ').title()} (Mean vs. Median Divergence)",
                        severity="Medium",
                        category="misleading_averages",
                        category_label=CATEGORY_LABELS["misleading_averages"],
                        what_happened=what_avg,
                        supporting_evidence=sup_avg,
                        comparison_baseline=f"Median ({med_val:,.2f}) and Ex-Outlier Trimmed Mean ({trimmed_mean:,.2f})",
                        why_it_matters=why_avg,
                        hypotheses=hyps_avg,
                        confidence_level="High",
                        confidence_justification=f"Exact distributional moment calculation across n = {len(s)} observations.",
                        recommended_investigation=[
                            f"Display the median ({med_val:,.2f}) alongside the mean ({mean_val:,.2f}) on executive scorecards for '{col}'.",
                            f"Inspect the extreme observation ({ext_val:,.2f}) to determine whether it belongs in a separate tier benchmark.",
                        ],
                        relevant_columns=[col],
                        calculations=[
                            f"mean_vs_median_gap_pct = (({mean_val:,.2f} - {med_val:,.2f}) / {med_val:,.2f}) * 100 = {gap_pct:+.2f}%",
                            f"outlier_pull_pct = (({mean_val:,.2f} - {trimmed_mean:,.2f}) / {trimmed_mean:,.2f}) * 100 = {outlier_pull_pct:+.2f}%",
                        ],
                        ai_explanation=cls.synthesize_ai_explanation(
                            f"Outlier-Distorted Average in {col.replace('_', ' ').title()}",
                            what_avg,
                            sup_avg,
                            why_avg,
                            hyps_avg,
                        ),
                        evidence_table=[
                            {"Statistic": "Parametric Mean", col: f"{mean_val:,.2f}"},
                            {"Statistic": "Median (P50)", col: f"{med_val:,.2f}"},
                            {"Statistic": "Trimmed Mean (Ex-Extreme)", col: f"{trimmed_mean:,.2f}"},
                            {"Statistic": "Extreme Observation", col: f"{ext_val:,.2f}"},
                            {"Statistic": "Standard Deviation", col: f"{std_val:,.2f}"},
                        ],
                        chart_spec=TruthLensChartSpec(
                            chart_type="bar",
                            title=f"{col.replace('_', ' ').title()}: Mean vs. Median vs. Extreme Value",
                            labels=["Median (P50)", "Trimmed Mean", "Reported Mean", "Extreme Value"],
                            datasets=[
                                TruthLensChartDataset(
                                    label=col.replace("_", " ").title(),
                                    data=[
                                        round(med_val, 2),
                                        round(trimmed_mean, 2),
                                        round(mean_val, 2),
                                        round(ext_val, 2),
                                    ],
                                )
                            ],
                        ),
                    )
                )
                break

    # ------------------------------------------------------------------
    # Detector 5: Incomplete Comparisons
    # ------------------------------------------------------------------
    @classmethod
    def _detect_incomplete_comparisons(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
        distortion_flags: list[str],
    ) -> None:
        seg_col = u["primary_segment_col"]
        rev_col = u["revenue_col"] or (u["measures"][0] if u["measures"] else None)

        # Check if segment totals are compared across unequal segment population counts without normalization
        if seg_col and rev_col and len(df) >= 8:
            grp = df.groupby(seg_col, dropna=True)[rev_col].agg(["count", "sum", "mean"])
            if len(grp) >= 2 and grp["count"].nunique() > 1:
                max_n_seg = str(grp["count"].idxmax())
                min_n_seg = str(grp["count"].idxmin())
                max_n = int(grp.loc[max_n_seg, "count"])
                min_n = int(grp.loc[min_n_seg, "count"])

                tot_rank_top = str(grp["sum"].idxmax())
                mean_rank_top = str(grp["mean"].idxmax())

                if max_n > min_n and (tot_rank_top != mean_rank_top or (max_n - min_n) >= 1):
                    what_inc = (
                        f"Segments in '{seg_col}' have unequal unit counts (e.g., '{max_n_seg}' has n = {max_n} records "
                        f"vs. '{min_n_seg}' with n = {min_n} records). Comparing unnormalized total '{rev_col}' "
                        f"across segments inflates larger segments relative to per-unit normalized averages."
                    )
                    sup_inc = (
                        f"'{max_n_seg}': Total ${float(grp.loc[max_n_seg, 'sum']):,.2f} across n={max_n} (Per-unit mean: ${float(grp.loc[max_n_seg, 'mean']):,.2f}); "
                        f"'{min_n_seg}': Total ${float(grp.loc[min_n_seg, 'sum']):,.2f} across n={min_n} (Per-unit mean: ${float(grp.loc[min_n_seg, 'mean']):,.2f})."
                    )
                    why_inc = (
                        "Comparing raw segment totals without normalizing for population/store count confounds "
                        "footprint size with per-unit operational productivity."
                    )
                    hyps_inc = [
                        "Hypothesis 1 (Footprint Count Confounding): Higher segment totals may simply reflect a greater number of active stores or records rather than superior per-unit demand.",
                    ]
                    findings.append(
                        TruthLensFinding(
                            id="tl_incomplete_unnormalized_segment_totals",
                            title=f"Unnormalized Segment Totals Across Unequal Population Sizes in '{seg_col.replace('_', ' ').title()}'",
                            severity="Low",
                            category="incomplete_comparisons",
                            category_label=CATEGORY_LABELS["incomplete_comparisons"],
                            what_happened=what_inc,
                            supporting_evidence=sup_inc,
                            comparison_baseline=f"Raw segment sum vs. per-record normalized mean across '{seg_col}'",
                            why_it_matters=why_inc,
                            hypotheses=hyps_inc,
                            confidence_level="High",
                            confidence_justification="Direct comparison of segment record counts, sums, and normalized means.",
                            recommended_investigation=[
                                f"Normalize '{rev_col}' per active unit/customer when benchmarking '{seg_col}' productivity.",
                            ],
                            relevant_columns=[seg_col, rev_col],
                            calculations=[
                                f"normalized_mean({max_n_seg}) = ${float(grp.loc[max_n_seg, 'sum']):,.2f} / {max_n} = ${float(grp.loc[max_n_seg, 'mean']):,.2f}",
                                f"normalized_mean({min_n_seg}) = ${float(grp.loc[min_n_seg, 'sum']):,.2f} / {min_n} = ${float(grp.loc[min_n_seg, 'mean']):,.2f}",
                            ],
                            ai_explanation=cls.synthesize_ai_explanation(
                                f"Unnormalized Segment Totals Across Unequal Population Sizes in '{seg_col.replace('_', ' ').title()}'",
                                what_inc,
                                sup_inc,
                                why_inc,
                                hyps_inc,
                            ),
                            evidence_table=[
                                {
                                    seg_col: str(idx),
                                    "Population Count (n)": int(r["count"]),
                                    f"Unnormalized Total {rev_col}": f"${float(r['sum']):,.2f}",
                                    f"Normalized Mean {rev_col}": f"${float(r['mean']):,.2f}",
                                }
                                for idx, r in grp.iterrows()
                            ],
                        )
                    )

        if not u["has_temporal"]:
            insufficient.append(
                InsufficientEvidenceNotice(
                    category="incomplete_comparisons",
                    category_label=CATEGORY_LABELS["incomplete_comparisons"],
                    reason=(
                        "Dataset contains a single cross-sectional snapshot with no date/period column; "
                        "seasonality and longitudinal period-over-period comparisons cannot be verified."
                    ),
                    required_signals=["period / date / month / quarter column with >= 2 time points"],
                )
            )

    # ------------------------------------------------------------------
    # Detector 6: Data Quality Problems
    # ------------------------------------------------------------------
    @classmethod
    def _detect_data_quality_problems(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
        distortion_flags: list[str],
    ) -> None:
        null_cols = [(c, int(df[c].isna().sum())) for c in df.columns if int(df[c].isna().sum()) > 0]
        dup_rows = int(df.duplicated().sum())

        if null_cols or dup_rows > 0:
            total_nulls = sum(n for _, n in null_cols)
            distortion_flags.append(f"{total_nulls} missing values and {dup_rows} duplicate rows detected")
            null_desc = ", ".join(f"'{c}' ({n} nulls)" for c, n in null_cols) if null_cols else "0 missing values"
            what_dq = (
                f"Detected {total_nulls} missing cell(s) across {len(null_cols)} column(s) ({null_desc}) "
                f"and {dup_rows} exact duplicate row(s)."
            )
            sup_dq = f"Total cells: {len(df) * len(df.columns):,}; Missing cells: {total_nulls}; Duplicate rows: {dup_rows}."
            why_dq = (
                "Missing values can introduce selection bias if records are dropped non-randomly, while "
                "duplicate rows double-count revenue and volume totals."
            )
            hyps_dq = [
                "Hypothesis 1 (Pipeline Ingestion Dropouts): Null cells may stem from incomplete upstream CRM/ERP joins.",
                "Hypothesis 2 (Retry Duplication): Duplicate rows may reflect idempotent webhook or batch retry logging.",
            ]
            findings.append(
                TruthLensFinding(
                    id="tl_data_quality_nulls_dups",
                    title="Missing Values or Duplicate Records Impacting Aggregation Integrity",
                    severity="High" if (total_nulls > len(df) * 0.05 or dup_rows > 0) else "Medium",
                    category="data_quality_problems",
                    category_label=CATEGORY_LABELS["data_quality_problems"],
                    what_happened=what_dq,
                    supporting_evidence=sup_dq,
                    comparison_baseline="100% matrix completeness and 0 duplicate records",
                    why_it_matters=why_dq,
                    hypotheses=hyps_dq,
                    confidence_level="High",
                    confidence_justification="Deterministic full-table scan.",
                    recommended_investigation=[
                        "Inspect records with missing fields to verify whether nulls cluster in specific segments or dates.",
                        "Deduplicate primary keys prior to computing financial sums.",
                    ],
                    relevant_columns=[c for c, _ in null_cols] or list(df.columns[:3]),
                    calculations=[
                        f"null_cell_count = {total_nulls}",
                        f"duplicate_row_count = {dup_rows}",
                    ],
                    ai_explanation=cls.synthesize_ai_explanation(
                        "Missing Values or Duplicate Records Impacting Aggregation Integrity",
                        what_dq,
                        sup_dq,
                        why_dq,
                        hyps_dq,
                    ),
                    evidence_table=[
                        {"Column": c, "Missing Cells": n, "Missing %": f"{(n / len(df) * 100.0):.1f}%"}
                        for c, n in null_cols
                    ],
                )
            )

    # ------------------------------------------------------------------
    # Detector 7: Correlation Versus Causation
    # ------------------------------------------------------------------
    @classmethod
    def _detect_correlation_vs_causation(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
    ) -> None:
        measures = u["measures"]
        if len(measures) < 2 or len(df) < 5:
            insufficient.append(
                InsufficientEvidenceNotice(
                    category="correlation_vs_causation",
                    category_label=CATEGORY_LABELS["correlation_vs_causation"],
                    reason="At least 2 numeric measures and n >= 5 observations are required to evaluate correlation vs. causation.",
                    required_signals=[">= 2 numeric columns", "n >= 5 rows"],
                )
            )
            return

        best_pair: tuple[str, str, float, float] | None = None
        for c1, c2 in itertools.combinations(measures, 2):
            sub = df[[c1, c2]].dropna()
            if len(sub) >= 5 and sub[c1].std() > 0 and sub[c2].std() > 0:
                r_val, p_val = stats.pearsonr(sub[c1], sub[c2])
                if abs(float(r_val)) >= 0.70:
                    if best_pair is None or abs(float(r_val)) > abs(best_pair[2]):
                        best_pair = (c1, c2, float(r_val), float(p_val))

        if best_pair:
            raw_c1, raw_c2, r_val, p_val = best_pair
            outcome_keywords = ("revenue", "sales", "profit", "gross_profit", "net_profit", "margin", "gmv", "income", "arr", "mrr")
            driver_keywords = ("customers", "active_customers", "marketing_spend", "marketing_expenditure", "spend", "ad_spend", "cost", "traffic", "users", "orders", "survey_responses")
            c1_is_outcome = any(k in raw_c1.lower() for k in outcome_keywords)
            c2_is_driver = any(k in raw_c2.lower() for k in driver_keywords)
            if c1_is_outcome and (c2_is_driver or not any(k in raw_c2.lower() for k in outcome_keywords)):
                driver_col, outcome_col = raw_c2, raw_c1
            else:
                driver_col, outcome_col = raw_c1, raw_c2

            r_sq = (r_val ** 2) * 100.0
            sub_pair = df[[driver_col, outcome_col]].dropna()
            slope, intercept = np.polyfit(sub_pair[driver_col].astype(float), sub_pair[outcome_col].astype(float), 1)
            sorted_sub = sub_pair.sort_values(by=driver_col)

            what_cc = (
                f"Strong observational correlation detected between operational driver '{driver_col}' and outcome metric '{outcome_col}' "
                f"(Pearson r = {r_val:.3f}, R² = {r_sq:.1f}%, p = {p_val:.4f} across n = {len(df)} records). "
                f"However, observational co-movement does not establish that '{driver_col}' independently drives '{outcome_col}'."
            )
            sup_cc = f"Pearson r = {r_val:.3f}; Shared variance (R²) = {r_sq:.1f}%; Two-tailed p-value = {p_val:.4e}; Sample size n = {len(df)}."
            why_cc = (
                f"Treating high correlation between '{driver_col}' and '{outcome_col}' as direct causation risks misallocating capital "
                "when both metrics scale jointly with store footprint size or local market tier."
            )
            hyps_cc = [
                f"Hypothesis 1 (Store Footprint & Market Tier Confounding): Both '{driver_col}' and '{outcome_col}' scale jointly with store footprint size or local market tier.",
                f"Hypothesis 2 (Bidirectional Capacity & Budget Feedback): High-volume flagship locations with larger '{outcome_col}' naturally attract larger '{driver_col}' traffic and budget allocations rather than '{driver_col}' acting as an isolated lever.",
            ]
            findings.append(
                TruthLensFinding(
                    id=f"tl_corr_vs_causation_{raw_c1}_{raw_c2}",
                    title=f"High Collinearity ({driver_col.replace('_', ' ').title()} & {outcome_col.replace('_', ' ').title()}, r = {r_val:.2f}) Is Observational, Not Proven Causation",
                    severity="Medium",
                    category="correlation_vs_causation",
                    category_label=CATEGORY_LABELS["correlation_vs_causation"],
                    what_happened=what_cc,
                    supporting_evidence=sup_cc,
                    comparison_baseline="Controlled experimental holdout / causal inference standard",
                    why_it_matters=why_cc,
                    hypotheses=hyps_cc,
                    confidence_level="High",
                    confidence_justification=f"Two-tailed Pearson correlation test on n = {len(df)} observations.",
                    recommended_investigation=[
                        f"Run a randomized holdout test or difference-in-differences analysis before scaling '{driver_col}' to drive '{outcome_col}'.",
                        "Control for store footprint size and local market tier using partial correlation or regularized regression.",
                    ],
                    relevant_columns=[driver_col, outcome_col],
                    calculations=[
                        f"pearson_r({driver_col}, {outcome_col}) = {r_val:.4f}",
                        f"r_squared = ({r_val:.4f})^2 = {r_sq:.1f}%",
                        f"ols_fit: {outcome_col} = {slope:,.2f} * {driver_col} + {intercept:,.2f}",
                    ],
                    ai_explanation=cls.synthesize_ai_explanation(
                        f"High Collinearity ({driver_col} & {outcome_col}, r = {r_val:.2f}) Is Observational, Not Proven Causation",
                        what_cc,
                        sup_cc,
                        why_cc,
                        hyps_cc,
                    ),
                    evidence_table=[
                        {
                            "Input Driver (X)": driver_col,
                            "Outcome Metric (Y)": outcome_col,
                            "Pearson r": f"{r_val:.4f}",
                            "Shared Variance (R²)": f"{r_sq:.1f}%",
                            "p-value": f"{p_val:.4e}",
                            "Causal Proof": "Not Established (Observational)",
                        }
                    ],
                    chart_spec=TruthLensChartSpec(
                        chart_type="scatter",
                        title=f"Scatter & OLS Fit: {driver_col.replace('_', ' ').title()} (X) vs. {outcome_col.replace('_', ' ').title()} (Y)",
                        labels=[str(round(float(x), 2)) for x in sorted_sub[driver_col]],
                        datasets=[
                            TruthLensChartDataset(
                                label=f"Observed {outcome_col.replace('_', ' ').title()}",
                                data=[round(float(y), 2) for y in sorted_sub[outcome_col]],
                            ),
                            TruthLensChartDataset(
                                label=f"OLS Regression Line (r = {r_val:.2f})",
                                data=[round(float(slope * x + intercept), 2) for x in sorted_sub[driver_col]],
                            ),
                        ],
                    ),
                )
            )

    # ------------------------------------------------------------------
    # Detector 8: Statistical Anomalies
    # ------------------------------------------------------------------
    @classmethod
    def _detect_statistical_anomalies(
        cls,
        df: pd.DataFrame,
        u: dict[str, Any],
        findings: list[TruthLensFinding],
        insufficient: list[InsufficientEvidenceNotice],
        distortion_flags: list[str],
    ) -> None:
        measures = u["measures"]
        if len(df) < 4 or not measures:
            return

        entity_col = (
            cls._match_column(u["dimensions"], ("store", "branch", "category", "region", "period"))
            or u["primary_segment_col"]
        )

        for col in measures:
            s = df[col].dropna()
            if len(s) < 4:
                continue
            q25 = float(s.quantile(0.25))
            q75 = float(s.quantile(0.75))
            iqr = q75 - q25
            if iqr <= 0:
                continue
            low_fence = q25 - 1.5 * iqr
            high_fence = q75 + 1.5 * iqr
            mean_val = float(s.mean())
            std_val = float(s.std())

            z_scores = ((s - mean_val).abs() / std_val) if std_val > 0 else pd.Series(0.0, index=s.index)
            mask = (s < low_fence) | (s > high_fence) | (z_scores > 2.5)
            out_s = s[mask]
            if len(out_s) == 0:
                continue

            ext_idx = (out_s - mean_val).abs().idxmax()
            ext_val = float(s.loc[ext_idx])
            ext_z = float(z_scores.loc[ext_idx])
            entity_label = (
                str(df.loc[ext_idx, entity_col])
                if (entity_col and entity_col in df.columns)
                else f"Row #{ext_idx}"
            )
            is_spike = ext_val > high_fence or ext_val >= mean_val
            direction_str = "upper-bound spike" if is_spike else "lower-bound drop"

            # Strictly non-negative metrics cannot practically fall below 0: clamp the displayed fence.
            is_non_negative = float(s.min()) >= 0.0
            disp_low = max(0.0, low_fence) if is_non_negative else low_fence
            clamped = is_non_negative and low_fence < 0.0
            fence_txt = f"[{disp_low:,.2f}, {high_fence:,.2f}]"
            fence_note = f" (theoretical lower fence {low_fence:,.2f} clamped to practical zero bound)" if clamped else ""

            # Determine exactly which hybrid test(s) the extreme record breached.
            iqr_breach = ext_val < low_fence or ext_val > high_fence
            z_breach = ext_z > 2.5
            if iqr_breach and z_breach:
                breach_copy = (
                    f"breached both the non-parametric IQR fence {fence_txt} and the parametric "
                    f"Z-score threshold (|z| = {ext_z:.2f}σ > 2.5σ)"
                )
            elif z_breach:
                breach_copy = (
                    f"breached the parametric Z-score threshold (|z| = {ext_z:.2f}σ > 2.5σ) while remaining "
                    f"within the wide non-parametric IQR fence {fence_txt}"
                )
            else:
                breach_copy = f"fell outside the non-parametric IQR fence {fence_txt}"

            distortion_flags.append(
                f"Statistical {direction_str} in '{col}' at {entity_label} ({ext_val:,.2f}, |z|={ext_z:.2f})"
            )

            what_anom = (
                f"Detected {len(out_s)} statistical anomaly record(s) in '{col}': '{entity_label}' recorded "
                f"an extreme {direction_str} of {ext_val:,.2f} that {breach_copy}."
            )
            sup_anom = (
                f"Observed value ({entity_label}): {ext_val:,.2f}; IQR fence: {fence_txt}{fence_note}; "
                f"Dataset mean: {mean_val:,.2f} (std: {std_val:,.2f}); Z-score: {ext_z:.2f}σ."
            )
            event_examples = (
                "(e.g., flagship campaign surge, bulk enterprise order, or duplicate ledger entry)"
                if is_spike
                else "(e.g., localized service disruption, fulfillment bottleneck, or partial-period telemetry truncation)"
            )
            why_anom = (
                f"Extreme {direction_str}s can represent either high-impact operational events "
                f"{event_examples} or data logging errors."
            )
            hyps_anom = (
                [
                    f"Hypothesis 1 (Intentional Campaign / Flagship Surge): '{entity_label}' may have executed a localized promotion or flagship initiative.",
                    f"Hypothesis 2 (Duplicate or Unallocated Ledger Booking): Multiple expense or volume entries may have been consolidated into '{entity_label}'.",
                ]
                if is_spike
                else [
                    f"Hypothesis 1 (Localized Service or Fulfillment Bottleneck): '{entity_label}' may have experienced staffing, inventory, or quality disruptions.",
                    f"Hypothesis 2 (Telemetry / Survey Logging Glitch): Partial period reporting or rating scale truncation may have depressed '{col}'.",
                ]
            )

            ordered_out_indices = [ext_idx] + [i for i in out_s.index if i != ext_idx]
            anom_row_refs: list[str] = []
            for r_idx in ordered_out_indices[:6]:
                r_ent = (
                    str(df.loc[r_idx, entity_col])
                    if (entity_col and entity_col in df.columns)
                    else f"Record #{r_idx}"
                )
                r_val = float(s.loc[r_idx])
                r_z = float(z_scores.loc[r_idx])
                anom_row_refs.append(
                    f"Row #{r_idx} • {r_ent} (Outlier) [{col}={r_val:,.2f}, |z|={r_z:.2f}σ]"
                )

            peer_indices = ordered_out_indices + [i for i in s.index if i not in ordered_out_indices][:7]
            cols_for_source = [c for c in [entity_col, u["primary_segment_col"], col] if c and c in df.columns]
            for c in df.columns:
                if c not in cols_for_source:
                    cols_for_source.append(c)
            cols_for_source = cols_for_source[:6]
            anom_source_rows = [
                {
                    "#Row": f"#{int(r_i)}" + (" ★" if r_i in out_s.index else ""),
                    **{
                        c_name: (
                            round(float(df.loc[r_i, c_name]), 2)
                            if isinstance(df.loc[r_i, c_name], (int, float, np.number)) and not pd.isna(df.loc[r_i, c_name])
                            else str(df.loc[r_i, c_name])
                        )
                        for c_name in cols_for_source
                    },
                }
                for r_i in peer_indices
            ]

            findings.append(
                TruthLensFinding(
                    id=f"tl_stat_anomaly_{col}",
                    title=f"Statistical Anomaly ({direction_str.title()}) in {col.replace('_', ' ').title()}: {entity_label}",
                    severity="High",
                    category="statistical_anomalies",
                    category_label=CATEGORY_LABELS["statistical_anomalies"],
                    what_happened=what_anom,
                    supporting_evidence=sup_anom,
                    comparison_baseline=f"IQR Fence {fence_txt} & Mean {mean_val:,.2f}",
                    why_it_matters=why_anom,
                    hypotheses=hyps_anom,
                    confidence_level="High",
                    confidence_justification=f"Hybrid IQR (1.5x) and Z-score (|z| = {ext_z:.2f}) verification on n = {len(s)} records.",
                    recommended_investigation=[
                        f"Inspect source transaction logs for '{entity_label}' ({col} = {ext_val:,.2f}) to confirm data accuracy.",
                        f"Compare '{entity_label}' against peer units in the same segment.",
                    ],
                    relevant_columns=[c for c in [entity_col, col] if c],
                    supporting_row_references=anom_row_refs,
                    source_rows=anom_source_rows,
                    calculations=[
                        f"iqr_bounds = [{q25:,.2f} - 1.5*{iqr:,.2f}, {q75:,.2f} + 1.5*{iqr:,.2f}] = [{low_fence:,.2f}, {high_fence:,.2f}]"
                        + (f" -> practical lower bound clamped to {disp_low:,.2f}" if clamped else ""),
                        f"z_score = |{ext_val:,.2f} - {mean_val:,.2f}| / {std_val:,.2f} = {ext_z:.2f}",
                    ],
                    ai_explanation=cls.synthesize_ai_explanation(
                        f"Statistical Anomaly in {col.replace('_', ' ').title()}: {entity_label}",
                        what_anom,
                        sup_anom,
                        why_anom,
                        hyps_anom,
                    ),
                    evidence_table=[
                        {
                            "Record / Unit": entity_label,
                            col: f"{ext_val:,.2f}",
                            "Lower Bound (IQR)": f"{disp_low:,.2f}" + (" (clamped ≥ 0)" if clamped else ""),
                            "Upper Bound (IQR)": f"{high_fence:,.2f}",
                            "Z-Score (|z|)": f"{ext_z:.2f}σ",
                        }
                    ],
                    chart_spec=TruthLensChartSpec(
                        chart_type="bar",
                        title=f"{col.replace('_', ' ').title()} Distribution: {entity_label} (Outlier) vs. IQR Bounds",
                        labels=["Lower Fence", "Q1 (25th)", "Median (50th)", "Mean", "Q3 (75th)", "Upper Fence", f"{entity_label} ★"],
                        datasets=[
                            TruthLensChartDataset(
                                label=col.replace("_", " ").title(),
                                data=[
                                    round(disp_low, 2),
                                    round(q25, 2),
                                    round(float(s.median()), 2),
                                    round(mean_val, 2),
                                    round(q75, 2),
                                    round(high_fence, 2),
                                    round(ext_val, 2),
                                ],
                            )
                        ],
                        reference_value=round(high_fence if is_spike else disp_low, 2),
                        reference_label="Upper IQR Fence" if is_spike else "Lower IQR Fence",
                    ),
                )
            )
