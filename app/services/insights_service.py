"""Service layer for AI business intelligence synthesis, data quality scoring, and automated insights."""

from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd

from app.core.config import Settings
from app.schemas.insights import (
    DataQualityScore,
    DatasetInsightsResponse,
    InsightItem,
)
from app.services.analytics_service import AnalyticsService
from app.services.dataset_service import DatasetNotFoundError, DatasetService


class InsightsService:
    """Generates automated business intelligence takeaways, anomaly alerts, and executive briefings."""

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
        # 1. Data Quality & Completeness Analysis
        # -------------------------------------------------------------
        total_null_cells = int(df.isna().sum().sum())
        completeness_pct = round((1.0 - (total_null_cells / total_cells)) * 100, 2)

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
                )
            )
            quality_notes.append(f"High missingness in columns: {', '.join(c for c, _, _ in high_null_cols)}")
        else:
            quality_notes.append("Excellent data completeness across all columns.")

        # -------------------------------------------------------------
        # 2. Outlier & Anomaly Analysis on Numeric Attributes
        # -------------------------------------------------------------
        numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
        total_outliers_found = 0
        total_numeric_values = 0

        for col in numeric_cols:
            clean_s = df[col].dropna()
            total_numeric_values += len(clean_s)
            if len(clean_s) >= 4:
                # Track key summary metrics
                col_sum = float(clean_s.sum())
                col_mean = round(float(clean_s.mean()), 2)
                col_max = round(float(clean_s.max()), 2)
                key_metrics[f"{col}_total"] = round(col_sum, 2)
                key_metrics[f"{col}_average"] = col_mean

                # Outlier detection via IQR
                q25 = float(clean_s.quantile(0.25))
                q75 = float(clean_s.quantile(0.75))
                iqr = q75 - q25
                if iqr > 0:
                    upper_bound = q75 + (2.0 * iqr)
                    lower_bound = q25 - (2.0 * iqr)
                    outlier_mask = (clean_s > upper_bound) | (clean_s < lower_bound)
                    count = int(outlier_mask.sum())
                    if count > 0:
                        total_outliers_found += count
                        max_val = float(clean_s.max())
                        insights.append(
                            InsightItem(
                                title=f"Statistical Anomalies in {col.title()}",
                                category="anomaly",
                                severity="warning" if count > 2 else "info",
                                summary=f"Detected {count} extreme data point(s) in '{col}' deviating substantially from the interquartile baseline.",
                                evidence=f"Values exceed upper bound {upper_bound:.2f} or lower bound {lower_bound:.2f}. Extreme value observed: {max_val:.2f}.",
                                recommendation="Investigate anomalous records to verify whether they represent true business outliers or logging errors.",
                            )
                        )

        anomaly_score = 100.0
        if total_numeric_values > 0:
            outlier_rate = (total_outliers_found / total_numeric_values) * 100
            anomaly_score = max(0.0, round(100.0 - (outlier_rate * 5), 2))

        # Overall quality score: 60% completeness + 40% stability
        overall_quality = round((0.6 * completeness_pct) + (0.4 * anomaly_score), 2)
        data_quality = DataQualityScore(
            overall_score=overall_quality,
            completeness_score=completeness_pct,
            anomaly_score=anomaly_score,
            notes=quality_notes,
        )

        # -------------------------------------------------------------
        # 3. Correlation & Driver Identification
        # -------------------------------------------------------------
        if len(numeric_cols) >= 2:
            try:
                corr_res = AnalyticsService.compute_correlation(
                    dataset_id=dataset_id,
                    settings=settings,
                    method="pearson",
                )
                for pair in corr_res.top_correlations[:3]:
                    coeff = pair.coefficient
                    if abs(coeff) >= 0.6:
                        relationship = "positive co-movement" if coeff > 0 else "inverse trade-off"
                        severity = "positive" if coeff > 0 else "info"
                        insights.append(
                            InsightItem(
                                title=f"Strong Relationship: {pair.feature_x} & {pair.feature_y}",
                                category="correlation",
                                severity=severity,
                                summary=f"A {pair.strength.replace('_', ' ')} correlation was detected, indicating significant {relationship}.",
                                evidence=f"Pearson correlation coefficient r = {coeff:.3f}.",
                                recommendation=f"Incorporate '{pair.feature_x}' when forecasting or optimizing '{pair.feature_y}'.",
                            )
                        )
            except Exception:
                pass

        # -------------------------------------------------------------
        # 4. Categorical Distribution & Concentration Risks
        # -------------------------------------------------------------
        cat_cols = list(df.select_dtypes(include=["object", "category", "string"]).columns)
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
                            title=f"Category Concentration in {cat.title()}",
                            category="risk",
                            severity="warning" if top_pct >= 80.0 else "info",
                            summary=f"Dominant concentration observed in '{cat}', where '{top_mode}' accounts for {top_pct}% of total records.",
                            evidence=f"{top_freq:,} of {len(non_null_cat):,} records classified as '{top_mode}'.",
                            recommendation=f"Evaluate whether segmenting '{top_mode}' into subcategories or diversifying coverage is warranted.",
                        )
                    )

        # -------------------------------------------------------------
        # 5. Executive Strategic Summary
        # -------------------------------------------------------------
        summary_sentences = [
            f"Dataset '{profile.filename}' contains {total_rows:,} records across {total_cols} attributes with an overall data health score of {overall_quality:.1f}/100.",
        ]
        if high_null_cols:
            summary_sentences.append(
                f"Data completeness is impacted by missing values in {len(high_null_cols)} field(s)."
            )
        else:
            summary_sentences.append("The dataset exhibits robust completeness with minimal missingness.")

        if total_outliers_found > 0:
            summary_sentences.append(
                f"{total_outliers_found} statistical outlier(s) were flagged for executive review."
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
