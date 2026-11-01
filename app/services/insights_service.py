"""Service layer for AI business intelligence synthesis, data quality scoring, and automated insights."""

from datetime import datetime, timezone
import itertools
from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import linregress

from app.core.config import Settings
from app.schemas.insights import (
    DataQualityScore,
    DatasetInsightsResponse,
    InsightItem,
)
from app.services.analytics_service import AnalyticsService
from app.services.column_roles import classify_columns
from app.services.dataset_service import DatasetNotFoundError, DatasetService


class InsightsService:
    """Generates automated business intelligence takeaways, anomaly alerts, and executive briefings."""

    @staticmethod
    def _get_variable_tier(col_name: str) -> int:
        """Classify a variable into business causal hierarchy:
        Tier 1: Inputs / Levers (spend, budget, cost, headcount, price, hours, etc.)
        Tier 2: Mid-Funnel Metrics (leads, traffic, customers, users, clicks, sessions, orders, units)
        Tier 3: Strategic Outcomes (revenue, profit, sales, mrr, ltv, arr, margin, earnings, satisfaction, churn)
        """
        name = col_name.lower().replace("-", "_")
        levers = (
            "spend", "cost", "budget", "price", "headcount", "fee", "rate", "hours",
            "ad_spend", "marketing_spend", "discount", "bid", "cpc", "investment", "salary"
        )
        if any(k in name for k in levers):
            return 1

        mid_funnel = (
            "leads", "traffic", "customers", "users", "clicks", "impressions",
            "sessions", "orders", "units", "signups", "conversions", "downloads", "subscribers", "visits"
        )
        if any(k in name for k in mid_funnel):
            return 2

        outcomes = (
            "revenue", "profit", "sales", "mrr", "ltv", "arr", "income",
            "margin", "earnings", "roi", "satisfaction", "retention", "nps", "growth", "churn"
        )
        if any(k in name for k in outcomes):
            return 3

        return 2

    @classmethod
    def _format_slope_metric(
        cls,
        clean_x: pd.Series,
        clean_y: pd.Series,
        x_name: str,
        y_name: str,
    ) -> tuple[str, float, float]:
        """Compute linear regression slope, r, and p-value, returning human-quantified text."""
        res = linregress(clean_x, clean_y)
        slope = float(res.slope)
        r_val = float(res.rvalue)
        p_val = float(res.pvalue)

        x_mean = float(clean_x.mean()) if len(clean_x) > 0 else 1.0
        x_std = float(clean_x.std()) if len(clean_x) > 1 else max(1.0, abs(x_mean) * 0.25)
        x_is_money = any(w in x_name.lower() for w in ("spend", "cost", "budget", "price", "revenue", "sales", "profit", "income", "mrr", "arr"))
        y_is_money = any(w in y_name.lower() for w in ("spend", "cost", "budget", "price", "revenue", "sales", "profit", "income", "mrr", "arr"))

        if x_mean >= 250_000:
            base_step = 50_000
        elif x_mean >= 100_000:
            base_step = 25_000
        elif x_mean >= 25_000:
            base_step = 5_000
        elif x_mean >= 5_000:
            base_step = 1_000
        elif x_mean >= 500:
            base_step = 100
        elif x_mean >= 50:
            base_step = 10
        else:
            base_step = 1

        max_allowed = max(x_mean * 2.0, x_std * 4.0, 1.0)
        chosen_step = base_step

        # If impact at base_step is negligible (< 0.05), scale step up
        if abs(slope * chosen_step) < 0.05:
            scale_multipliers = [2, 2.5, 5, 10, 20, 50, 100]
            for mult in scale_multipliers:
                cand = int(base_step * mult)
                if cand <= max_allowed:
                    chosen_step = cand
                    if abs(slope * chosen_step) >= 0.05:
                        break

        impact = slope * chosen_step
        abs_impact = abs(impact)
        impact_sign = "+" if impact >= 0 else "-"
        money_prefix = "$" if y_is_money else ""

        if abs_impact >= 10.0:
            impact_str = f"{impact_sign}{money_prefix}{abs_impact:,.1f}"
        elif abs_impact >= 0.10:
            impact_str = f"{impact_sign}{money_prefix}{abs_impact:,.2f}"
        elif abs_impact >= 0.01:
            impact_str = f"{impact_sign}{money_prefix}{abs_impact:,.3f}"
        else:
            impact_str = f"{impact_sign}{money_prefix}{abs_impact:,.4f}"

        # Additional guard against any zero formatting (+0.00)
        if impact_str in ("+0.00", "-0.00", "+$0.00", "-$0.00"):
            impact_str = f"{impact_sign}{money_prefix}{abs_impact:.4f}"
            if impact_str in ("+0.0000", "-0.0000", "+$0.0000", "-$0.0000"):
                impact_str = f"{impact_sign}{money_prefix}{abs_impact:.2e}"

        if x_is_money:
            step_str = f"+${chosen_step:,}" if chosen_step >= 1 else f"+${chosen_step}"
        else:
            step_str = f"+{chosen_step:,}" if chosen_step >= 100 else (f"+1 unit" if chosen_step == 1 else f"+{chosen_step}")

        p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
        text = f"Each {step_str} in '{x_name}' is associated with {impact_str} in '{y_name}' (r = {r_val:.2f}, {p_str})"
        return text, r_val, p_val

    @classmethod
    def generate_insights(
        cls,
        dataset_id: str,
        settings: Settings,
    ) -> DatasetInsightsResponse:
        """Synthesize comprehensive exploratory data insights and executive briefing."""
        profile = DatasetService.get_dataset_profile(dataset_id=dataset_id, settings=settings)
        df = DatasetService.get_dataframe(dataset_id=dataset_id, settings=settings)

        total_rows = len(df)
        total_cols = len(df.columns)
        total_cells = total_rows * total_cols if total_rows > 0 and total_cols > 0 else 1

        insights: list[InsightItem] = []
        quality_notes: list[str] = []
        key_metrics: dict[str, Any] = {
            "total_rows": total_rows,
            "total_columns": total_cols,
        }

        # -------------------------------------------------------------
        # 1. Multi-Dimensional Data Health Scoring (40 Completeness / 30 Sample / 30 Hygiene)
        # -------------------------------------------------------------
        total_null_cells = int(df.isna().sum().sum())
        valid_cells = total_cells - total_null_cells
        completeness_pct = round((valid_cells / total_cells) * 100, 2)
        completeness_pts = round((completeness_pct / 100.0) * 40.0, 2)

        # Sample size adequacy (30 pts max, tiered scaling up to n = 200)
        if total_rows < 30:
            sample_pts = round((total_rows / 30.0) * 15.0, 1)
        elif total_rows < 60:
            sample_pts = 20.0
        elif total_rows < 100:
            sample_pts = 22.5
        elif total_rows < 200:
            sample_pts = round(25.0 + ((total_rows - 100.0) / 100.0) * 5.0, 1)
        else:
            sample_pts = 30.0
        sample_size_score = round((sample_pts / 30.0) * 100.0, 2)

        # Duplicate row check
        duplicate_count = int(df.duplicated().sum())
        duplicate_score = round(max(0.0, (1.0 - (duplicate_count / max(1, total_rows))) * 100.0), 2)

        # Zero-variance / constant column check
        constant_cols = [str(c) for c in df.columns if df[c].nunique(dropna=True) <= 1]
        variance_score = round(max(0.0, ((total_cols - len(constant_cols)) / max(1, total_cols)) * 100.0), 2)

        high_null_cols: list[tuple[str, float, int]] = []
        for col_name in df.columns:
            nulls = int(df[col_name].isna().sum())
            if nulls > 0:
                pct = round((nulls / total_rows) * 100, 2)
                if pct >= 10.0:
                    high_null_cols.append((col_name, pct, nulls))

        if high_null_cols:
            col_details = ", ".join(f"'{c}' ({pct}%)" for c, pct, _ in high_null_cols)
            insights.append(
                InsightItem(
                    title="Significant Missing Data Detected",
                    category="data_quality",
                    severity="warning",
                    summary=f"Substantial missing values identified in {len(high_null_cols)} attribute(s): {col_details}.",
                    evidence=f"{total_null_cells:,} total null cells across the dataset ({100 - completeness_pct:.1f}% missingness overall).",
                    recommendation="Review source data extraction pipelines or apply domain-appropriate imputation before running downstream modeling.",
                    confidence_badge=f"n = {total_rows} records",
                )
            )
            quality_notes.append(f"High missingness in columns: {', '.join(c for c, _, _ in high_null_cols)}")
        else:
            quality_notes.append("Excellent data completeness across all columns.")

        if total_rows < 30:
            quality_notes.append(f"Sample size warning: dataset has {total_rows} rows (minimum 30 recommended for statistical inference).")
        elif total_rows < 200:
            quality_notes.append(f"Limited sample size: dataset has {total_rows} rows (200+ recommended for multi-dimensional segmentation).")

        # -------------------------------------------------------------
        # 2. Outlier & Anomaly Analysis on Numeric Attributes
        # -------------------------------------------------------------
        roles = classify_columns(df)
        numeric_cols = list(roles["measures"])
        total_outliers_found = 0
        flagged_outlier_cols = 0
        total_numeric_values = 0

        for col in numeric_cols:
            clean_s = df[col].dropna()
            total_numeric_values += len(clean_s)
            if len(clean_s) >= 4:
                col_sum = float(clean_s.sum())
                col_mean = round(float(clean_s.mean()), 2)
                key_metrics[f"{col}_total"] = round(col_sum, 2)
                key_metrics[f"{col}_average"] = col_mean

                q25 = float(clean_s.quantile(0.25))
                q75 = float(clean_s.quantile(0.75))
                iqr = q75 - q25
                iqr_mask = pd.Series(False, index=clean_s.index)
                upper_bound = q75 + (1.5 * iqr)
                lower_bound = q25 - (1.5 * iqr)
                if iqr > 0:
                    iqr_mask = (clean_s > upper_bound) | (clean_s < lower_bound)

                # Z-Score check (|z| > 2.5)
                z_mask = pd.Series(False, index=clean_s.index)
                std_val = float(clean_s.std())
                mean_val = float(clean_s.mean())
                if std_val > 0:
                    z_mask = ((clean_s - mean_val).abs() / std_val) > 2.5

                outlier_mask = iqr_mask | z_mask
                count = int(outlier_mask.sum())
                if count > 0:
                    total_outliers_found += count
                    flagged_outlier_cols += 1
                    outlier_vals = clean_s[outlier_mask]
                    ext_idx = (outlier_vals - mean_val).abs().idxmax()
                    extreme_val = float(clean_s.loc[ext_idx])

                    if extreme_val > upper_bound or extreme_val >= mean_val:
                        anomaly_rec = (
                            f"Audit the high-magnitude spike in '{col}' ({extreme_val:,.2f}) to confirm "
                            f"whether it reflects an intentional campaign surge or a duplicate/unallocated "
                            f"spend entry, and evaluate its marginal ROI."
                        )
                    else:
                        anomaly_rec = (
                            f"Isolate the cohort or period behind the '{col}' drop ({extreme_val:,.2f}) "
                            f"to identify service bottlenecks, fulfillment delays, or localized churn risks."
                        )

                    insights.append(
                        InsightItem(
                            title=f"Statistical Anomalies in {col.replace('_', ' ').title()}",
                            category="anomaly",
                            severity="warning",
                            summary=f"Detected {count} extreme data point(s) in '{col}' deviating substantially from normal distribution (IQR 1.5x / |z| > 2.5).",
                            evidence=f"Bounds: [{lower_bound:,.2f}, {upper_bound:,.2f}]. Extreme value observed: {extreme_val:,.2f}.",
                            recommendation=anomaly_rec,
                            confidence_badge=f"n = {len(clean_s)} | Hybrid Outlier Filter",
                            action_link={
                                "target_tab": "tab-anomalies",
                                "label": "Inspect Anomalies →",
                                "column": col,
                            },
                        )
                    )

        # Segment-level anomalies across top dimensions and metrics
        for dim in roles["dimensions"][:2]:
            nunique_dim = int(df[dim].nunique(dropna=True))
            if 3 <= nunique_dim <= max(3, total_rows // 2) and len(numeric_cols) > 0:
                top_m = numeric_cols[0]
                seg_means = df.groupby(dim, dropna=True)[top_m].mean()
                if len(seg_means) >= 3 and seg_means.std() > 0:
                    seg_z = ((seg_means - seg_means.mean()).abs() / seg_means.std())
                    out_segs = seg_z[seg_z >= 1.5]
                    for seg_name, z_val in out_segs.items():
                        insights.append(
                            InsightItem(
                                title=f"Segment Anomaly in {dim.replace('_', ' ').title()}: {seg_name}",
                                category="anomaly",
                                severity="warning",
                                summary=f"Segment '{seg_name}' in '{dim}' shows an anomalous mean '{top_m}' of {seg_means[seg_name]:,.2f} ({z_val:.2f} standard deviations from peer average).",
                                evidence=f"Peer segment mean: {seg_means.mean():,.2f} (std: {seg_means.std():,.2f}).",
                                recommendation=f"Audit operational drivers specific to '{seg_name}' to account for this segment-level deviation.",
                                confidence_badge=f"n = {len(df)} | Segment Variance",
                                action_link={
                                    "target_tab": "tab-aggregations",
                                    "label": "View Visual Aggregations →",
                                    "dimension": dim,
                                    "metric": top_m,
                                    "function": "mean",
                                },
                            )
                        )

        # Outlier & Variance Hygiene (30 pts max): deduct 3 pts per flagged outlier feature (capped at 15 pts)
        outlier_penalty_pts = min(15.0, flagged_outlier_cols * 3.0)
        dup_penalty_pts = round(((100.0 - duplicate_score) / 100.0) * 7.5, 2)
        var_penalty_pts = round(((100.0 - variance_score) / 100.0) * 7.5, 2)
        hygiene_pts = max(0.0, round(30.0 - outlier_penalty_pts - dup_penalty_pts - var_penalty_pts, 2))
        anomaly_score = round((hygiene_pts / 30.0) * 100.0, 2)

        overall_health = round(completeness_pts + sample_pts + hygiene_pts, 1)

        penalties: list[str] = []
        if total_rows < 30:
            penalties.append(f"Penalized for small sample size (n={total_rows} < 30)")
        elif total_rows < 200:
            penalties.append(f"Limited sample size (n={total_rows} < 200)")
        if flagged_outlier_cols > 0:
            penalties.append(f"{flagged_outlier_cols} outlier feature(s) flagged (-{outlier_penalty_pts:.0f} pts)")
        if duplicate_count > 0:
            penalties.append(f"{duplicate_count} duplicate row(s)")
        if constant_cols:
            penalties.append(f"{len(constant_cols)} constant column(s): {', '.join(constant_cols)}")

        penalty_reason = "; ".join(penalties) if penalties else "All health dimensions optimal"

        data_quality = DataQualityScore(
            overall_score=overall_health,
            completeness_score=completeness_pct,
            sample_size_score=sample_size_score,
            duplicate_score=duplicate_score,
            variance_score=variance_score,
            anomaly_score=anomaly_score,
            penalty_reason=penalty_reason,
            total_cells=total_cells,
            valid_cells=valid_cells,
            null_cells=total_null_cells,
            duplicate_rows=duplicate_count,
            constant_columns=constant_cols,
            notes=quality_notes,
        )

        # -------------------------------------------------------------
        # 3. Causal Driver Identification & Collinear Clustering
        # -------------------------------------------------------------
        if len(numeric_cols) >= 2:
            try:
                # Pairwise correlation & slope computation
                corr_matrix: dict[tuple[str, str], float] = {}
                p_val_matrix: dict[tuple[str, str], float] = {}
                slope_text_matrix: dict[tuple[str, str], str] = {}

                for c1, c2 in itertools.combinations(numeric_cols, 2):
                    sub = df[[c1, c2]].dropna()
                    if len(sub) >= 4:
                        slope_str, r_val, p_val = cls._format_slope_metric(sub[c1], sub[c2], c1, c2)
                        corr_matrix[(c1, c2)] = r_val
                        corr_matrix[(c2, c1)] = r_val
                        p_val_matrix[(c1, c2)] = p_val
                        p_val_matrix[(c2, c1)] = p_val
                        slope_text_matrix[(c1, c2)] = slope_str
                        # Also compute reverse slope
                        rev_slope, _, _ = cls._format_slope_metric(sub[c2], sub[c1], c2, c1)
                        slope_text_matrix[(c2, c1)] = rev_slope

                # Step 3a: Identify Collinear Clusters (|r| >= 0.85 among 3+ variables)
                high_corr_graph: dict[str, set[str]] = {col: set() for col in numeric_cols}
                for (c1, c2), r in corr_matrix.items():
                    if abs(r) >= 0.85:
                        high_corr_graph[c1].add(c2)
                        high_corr_graph[c2].add(c1)

                clustered_features: set[str] = set()
                # Find maximal cliques of size >= 3
                for candidate in numeric_cols:
                    if candidate in clustered_features:
                        continue
                    neighbors = [n for n in high_corr_graph[candidate] if n not in clustered_features]
                    if len(neighbors) >= 2:
                        for pair in itertools.combinations(neighbors, 2):
                            if pair[1] in high_corr_graph[pair[0]]:
                                initial_clique = {candidate, pair[0], pair[1]}
                                # Expand clique greedily with any other candidate connected to all current members
                                for other in numeric_cols:
                                    if other not in initial_clique and other not in clustered_features:
                                        if all(other in high_corr_graph[m] for m in initial_clique):
                                            initial_clique.add(other)

                                cluster = sorted(
                                    initial_clique,
                                    key=lambda x: (cls._get_variable_tier(x), x),
                                )
                                clustered_features.update(cluster)

                                lead_driver = cluster[0]
                                slopes_desc = []
                                for target in cluster[1:]:
                                    if (lead_driver, target) in slope_text_matrix:
                                        slopes_desc.append(slope_text_matrix[(lead_driver, target)])

                                # Evaluate pairwise correlations and p-values across all pairs in the cluster
                                cluster_p_vals = [
                                    p_val_matrix.get((m1, m2), 0.05)
                                    for m1, m2 in itertools.combinations(cluster, 2)
                                ]
                                max_cluster_p = max(cluster_p_vals) if cluster_p_vals else 0.05

                                cluster_r_vals = [
                                    abs(corr_matrix.get((m1, m2), 0.85))
                                    for m1, m2 in itertools.combinations(cluster, 2)
                                ]
                                min_cluster_r = min(cluster_r_vals) if cluster_r_vals else 0.85

                                if len(cluster) >= 3:
                                    cluster_quoted = (
                                        ", ".join(f"'{c}'" for c in cluster[:-1])
                                        + f", and '{cluster[-1]}'"
                                    )
                                else:
                                    cluster_quoted = " and ".join(f"'{c}'" for c in cluster)

                                if total_rows < 30:
                                    conf_badge = f"n = {total_rows} | Low Confidence - Small Sample"
                                elif max_cluster_p < 0.001:
                                    conf_badge = f"n = {total_rows} | High Statistical Significance (p < 0.001)"
                                elif max_cluster_p < 0.05:
                                    conf_badge = f"n = {total_rows} | Statistically Significant (p = {max_cluster_p:.3f})"
                                else:
                                    conf_badge = f"n = {total_rows} | Observational (p = {max_cluster_p:.2f})"

                                cluster_title_labels = " · ".join(
                                    c.replace("_", " ").title() for c in cluster
                                )
                                cluster_single_quoted = ", ".join(f"'{c}'" for c in cluster)
                                insights.append(
                                    InsightItem(
                                        title=f"Multi-Driver Growth Cluster: {cluster_title_labels}",
                                        category="correlation",
                                        severity="positive",
                                        summary=(
                                            f"Identified a highly synchronized growth cluster among {len(cluster)} core metrics: "
                                            f"{cluster_single_quoted}. These metrics demonstrate tight mutual collinearity (|r| ≥ 0.85), "
                                            f"moving in lockstep."
                                        ),
                                        evidence="; ".join(slopes_desc) if slopes_desc else "Strong mutual collinearity across cluster.",
                                        recommendation=(
                                            f"Strong historical co-movement links {cluster_quoted} (r ≥ {min_cluster_r:.2f}). "
                                            f"Validate causal lift via controlled holdout testing or incremental spend attribution "
                                            f"before scaling budget allocations, and avoid combining these collinear features "
                                            f"directly in unregularized linear models."
                                        ),
                                        confidence_badge=conf_badge,
                                        action_link={
                                            "target_tab": "tab-correlations",
                                            "label": "View in Driver Correlations →",
                                            "feature_x": lead_driver,
                                            "feature_y": cluster[-1],
                                        },
                                        cluster_features=cluster,
                                        slope_metric=slopes_desc[0] if slopes_desc else None,
                                    )
                                )
                                break

                # Step 3b: Process remaining bivariate correlations (|r| >= 0.60)
                # Sort by absolute correlation descending
                unique_pairs = []
                seen_pairs = set()
                for (c1, c2), r in corr_matrix.items():
                    pair_key = tuple(sorted([c1, c2]))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        unique_pairs.append((c1, c2, r))

                unique_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

                seen_cluster_external_targets: set[str] = set()

                for c1, c2, r in unique_pairs:
                    # Skip if both variables already grouped in a cluster
                    if c1 in clustered_features and c2 in clustered_features:
                        continue

                    # Deduplicate cross-correlations connecting multi-driver cluster members to the same external target
                    if len(clustered_features) >= 3:
                        if c1 in clustered_features and c2 not in clustered_features:
                            if c2 in seen_cluster_external_targets:
                                continue
                            seen_cluster_external_targets.add(c2)
                        elif c2 in clustered_features and c1 not in clustered_features:
                            if c1 in seen_cluster_external_targets:
                                continue
                            seen_cluster_external_targets.add(c1)

                    if abs(r) >= 0.60:
                        # Order by business causal hierarchy: lower tier is driver, higher tier is outcome
                        tier1 = cls._get_variable_tier(c1)
                        tier2 = cls._get_variable_tier(c2)
                        if tier1 <= tier2:
                            driver, outcome = c1, c2
                        else:
                            driver, outcome = c2, c1

                        slope_text = slope_text_matrix.get((driver, outcome), f"Correlation r = {r:.3f}")
                        p_val = p_val_matrix.get((driver, outcome), 0.05)

                        if total_rows < 30:
                            conf_badge = f"n = {total_rows} | Low Confidence - Small Sample"
                        elif p_val < 0.001:
                            conf_badge = f"n = {total_rows} | High Confidence (p < 0.001)"
                        elif p_val < 0.05:
                            conf_badge = f"n = {total_rows} | Statistically Significant (p = {p_val:.3f})"
                        else:
                            conf_badge = f"n = {total_rows} | Observational (p = {p_val:.2f})"

                        relationship = "positive co-movement" if r > 0 else "inverse trade-off"
                        severity = "positive" if r > 0 else "info"

                        insights.append(
                            InsightItem(
                                title=f"Driver Relationship: {driver.replace('_', ' ').title()} ➔ {outcome.replace('_', ' ').title()}",
                                category="correlation",
                                severity=severity,
                                summary=f"A strong {relationship} was detected between '{driver}' and '{outcome}'.",
                                evidence=slope_text,
                                recommendation=f"Incorporate and optimize '{driver}' when steering '{outcome}'.",
                                confidence_badge=conf_badge,
                                action_link={
                                    "target_tab": "tab-correlations",
                                    "label": "View in Driver Correlations →",
                                    "feature_x": driver,
                                    "feature_y": outcome,
                                },
                                slope_metric=slope_text,
                            )
                        )
                        if len(insights) >= 8:
                            break

            except Exception:
                pass

        # -------------------------------------------------------------
        # 4. Categorical Distribution & Concentration Risks
        # -------------------------------------------------------------
        cat_cols = list(roles["dimensions"])
        for cat in cat_cols[:3]:
            non_null_cat = df[cat].dropna()
            if len(non_null_cat) > 0:
                top_mode = non_null_cat.mode().iloc[0]
                top_freq = int((non_null_cat == top_mode).sum())
                top_pct = round((top_freq / len(non_null_cat)) * 100, 1)
                key_metrics[f"top_{cat}"] = str(top_mode)

                if top_pct >= 60.0 and len(non_null_cat.unique()) > 1:
                    insights.append(
                        InsightItem(
                            title=f"Category Concentration in {cat.replace('_', ' ').title()}",
                            category="risk",
                            severity="warning" if top_pct >= 80.0 else "info",
                            summary=f"Dominant concentration observed in '{cat}', where '{top_mode}' accounts for {top_pct}% of total records.",
                            evidence=f"{top_freq:,} of {len(non_null_cat):,} records classified as '{top_mode}'.",
                            recommendation=f"Evaluate whether segmenting '{top_mode}' into subcategories or diversifying coverage is warranted.",
                            confidence_badge=f"n = {len(non_null_cat)} | Concentration Index",
                        )
                    )

        # -------------------------------------------------------------
        # 5. Executive Strategic Summary
        # -------------------------------------------------------------
        summary_sentences = [
            f"Dataset '{profile.filename}' contains {total_rows:,} records across {total_cols} attributes with an overall data health score of {overall_health:.1f}/100.",
        ]
        missing_pct = round(100.0 - completeness_pct, 2)
        if total_null_cells == 0:
            summary_sentences.append(
                f"The dataset achieves 100% data completeness (zero missing values across all {total_cells:,} cells)."
            )
        elif high_null_cols or missing_pct >= 5.0:
            field_cnt = len(high_null_cols) if high_null_cols else int((df.isna().sum() > 0).sum())
            summary_sentences.append(
                f"Data completeness is impacted by missing values in {field_cnt} field(s)."
            )
        else:
            summary_sentences.append("The dataset exhibits robust completeness with minimal missingness.")

        if total_outliers_found > 0:
            summary_sentences.append(
                f"{total_outliers_found} statistical outlier(s) were flagged for executive review."
            )

        if total_rows < 30:
            summary_sentences.append(
                f"Notice: Low sample size (n={total_rows}) may limit statistical generalizability."
            )

        exec_summary = " ".join(summary_sentences)

        return DatasetInsightsResponse(
            dataset_id=dataset_id,
            filename=profile.filename,
            generated_at=datetime.now(timezone.utc).isoformat(),
            executive_summary=exec_summary,
            data_quality=data_quality,
            key_metrics=key_metrics,
            insights=insights,
        )
