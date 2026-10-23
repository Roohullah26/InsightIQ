"""Service layer for deterministic analytics, correlation analysis, aggregations, and anomaly detection."""

from typing import Any
import numpy as np
import pandas as pd

from app.core.config import Settings
from app.schemas.analytics import (
    AggregationRequest,
    AggregationResponse,
    AnomalyDetectionResponse,
    CorrelationMethod,
    CorrelationPair,
    CorrelationResponse,
    OutlierRecord,
)
from app.services.dataset_service import DatasetNotFoundError, DatasetService


class AnalyticsError(ValueError):
    """Raised when an analytical operation fails validation or dataset requirements."""


class AnalyticsService:
    """Provides statistical calculations, feature correlations, group aggregations, and outlier detection."""

    @staticmethod
    def _classify_correlation_strength(coeff: float) -> str:
        """Classify correlation coefficient into descriptive strength tier."""
        abs_val = abs(coeff)
        sign = "positive" if coeff > 0 else "negative"

        if abs_val >= 0.7:
            return f"strong_{sign}"
        if abs_val >= 0.4:
            return f"moderate_{sign}"
        if abs_val >= 0.15:
            return f"weak_{sign}"
        return "none"

    @classmethod
    def compute_correlation(
        cls,
        dataset_id: str,
        settings: Settings,
        method: CorrelationMethod = "pearson",
    ) -> CorrelationResponse:
        """Calculate pairwise correlation matrix and rank significant feature relationships."""
        df = DatasetService.get_dataframe(dataset_id=dataset_id, settings=settings)

        # Filter strictly to numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) < 2:
            raise AnalyticsError(
                f"Dataset contains {len(numeric_df.columns)} numeric column(s). At least 2 numeric columns are required for correlation analysis."
            )

        corr_matrix = numeric_df.corr(method=method)

        features = list(numeric_df.columns)
        matrix_dict: dict[str, dict[str, float | None]] = {}
        pairwise_list: list[CorrelationPair] = []

        for f1 in features:
            matrix_dict[f1] = {}
            for f2 in features:
                val = corr_matrix.loc[f1, f2]
                if pd.isna(val) or np.isnan(val):
                    matrix_dict[f1][f2] = None
                else:
                    matrix_dict[f1][f2] = round(float(val), 4)

        # Extract unique non-identity pairs
        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                f1, f2 = features[i], features[j]
                val = matrix_dict[f1][f2]
                if val is not None:
                    pairwise_list.append(
                        CorrelationPair(
                            feature_x=f1,
                            feature_y=f2,
                            coefficient=val,
                            strength=cls._classify_correlation_strength(val),
                        )
                    )

        # Rank by absolute correlation strength descending
        pairwise_list.sort(key=lambda p: abs(p.coefficient), reverse=True)

        return CorrelationResponse(
            dataset_id=dataset_id,
            method=method,
            features=features,
            matrix=matrix_dict,
            top_correlations=pairwise_list,
        )

    @classmethod
    def compute_aggregations(
        cls,
        dataset_id: str,
        request: AggregationRequest,
        settings: Settings,
    ) -> AggregationResponse:
        """Execute multi-dimensional grouping and metric aggregation."""
        df = DatasetService.get_dataframe(dataset_id=dataset_id, settings=settings)

        # Validate group_by columns
        missing_group_cols = [c for c in request.group_by if c not in df.columns]
        if missing_group_cols:
            raise AnalyticsError(f"Group-by column(s) not found in dataset: {missing_group_cols}")

        # Validate metric columns
        missing_metric_cols = [c for c in request.metrics.keys() if c not in df.columns]
        if missing_metric_cols:
            raise AnalyticsError(f"Metric column(s) not found in dataset: {missing_metric_cols}")

        # Check metrics are numeric
        for col in request.metrics.keys():
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise AnalyticsError(f"Metric column '{col}' is not numeric and cannot be aggregated.")

        # Build aggregation dictionary
        agg_spec = {col: funcs for col, funcs in request.metrics.items()}

        try:
            grouped = df.groupby(request.group_by, as_index=False).agg(agg_spec)
        except Exception as exc:
            raise AnalyticsError(f"Failed to execute aggregation: {exc}") from exc

        # Flatten multi-level columns if pandas generated a MultiIndex
        if isinstance(grouped.columns, pd.MultiIndex):
            new_cols: list[str] = []
            for col, stat in grouped.columns:
                if not stat or col in request.group_by:
                    new_cols.append(col)
                else:
                    new_cols.append(f"{col}_{stat}")
            grouped.columns = new_cols

        # Optional sorting
        if request.sort_by:
            if request.sort_by not in grouped.columns:
                raise AnalyticsError(
                    f"Sort column '{request.sort_by}' is not present in aggregated results. Available: {list(grouped.columns)}"
                )
            grouped = grouped.sort_values(by=request.sort_by, ascending=request.ascending)

        # Apply limit
        grouped = grouped.head(request.limit)

        # Convert to records with NaN as None
        records = (
            grouped.astype(object)
            .where(pd.notna(grouped), None)
            .to_dict(orient="records")
        )

        return AggregationResponse(
            dataset_id=dataset_id,
            group_by=request.group_by,
            row_count=len(records),
            data=records,
        )

    @classmethod
    def detect_outliers(
        cls,
        dataset_id: str,
        column: str,
        settings: Settings,
        method: str = "iqr",
        threshold: float = 1.5,
    ) -> AnomalyDetectionResponse:
        """Identify statistical anomalies using Interquartile Range (IQR) or Z-Score."""
        df = DatasetService.get_dataframe(dataset_id=dataset_id, settings=settings)

        if column not in df.columns:
            raise AnalyticsError(f"Column '{column}' does not exist in dataset.")

        if not pd.api.types.is_numeric_dtype(df[column]):
            raise AnalyticsError(f"Column '{column}' is not numeric. Anomaly detection requires numeric data.")

        series = df[column].dropna()
        total_rows = len(series)
        if total_rows == 0:
            raise AnalyticsError(f"Column '{column}' contains no non-null numeric values.")

        outliers: list[OutlierRecord] = []
        lower_bound: float = 0.0
        upper_bound: float = 0.0

        if method == "iqr":
            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr = q75 - q25
            lower_bound = round(q25 - (threshold * iqr), 4)
            upper_bound = round(q75 + (threshold * iqr), 4)

            # Identify rows exceeding bounds
            mask = (series < lower_bound) | (series > upper_bound)
            outlier_series = series[mask]

            for idx, val in outlier_series.items():
                distance = (lower_bound - val) if val < lower_bound else (val - upper_bound)
                score = round(distance / (iqr if iqr > 0 else 1.0), 3)
                outliers.append(
                    OutlierRecord(
                        row_index=int(idx),
                        value=round(float(val), 4),
                        score=float(score),
                    )
                )

        elif method == "zscore":
            mean_val = float(series.mean())
            std_val = float(series.std())

            if std_val == 0.0 or pd.isna(std_val):
                lower_bound = round(mean_val, 4)
                upper_bound = round(mean_val, 4)
            else:
                lower_bound = round(mean_val - (threshold * std_val), 4)
                upper_bound = round(mean_val + (threshold * std_val), 4)
                z_scores = (series - mean_val) / std_val
                mask = z_scores.abs() > threshold
                outlier_series = series[mask]

                for idx, val in outlier_series.items():
                    outliers.append(
                        OutlierRecord(
                            row_index=int(idx),
                            value=round(float(val), 4),
                            score=round(float(abs(z_scores.loc[idx])), 3),
                        )
                    )
        else:
            raise AnalyticsError(f"Unsupported outlier detection method '{method}'. Use 'iqr' or 'zscore'.")

        # Sort outliers by extremity score descending
        outliers.sort(key=lambda o: o.score, reverse=True)
        outlier_pct = round((len(outliers) / total_rows) * 100, 2) if total_rows > 0 else 0.0

        return AnomalyDetectionResponse(
            dataset_id=dataset_id,
            column=column,
            method=method,  # type: ignore[arg-type]
            total_rows=total_rows,
            outlier_count=len(outliers),
            outlier_percentage=outlier_pct,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            outliers=outliers[:100],  # Cap output at top 100 outliers for performance
        )
