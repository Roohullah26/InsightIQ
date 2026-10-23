"""Service layer for natural language dataset inquiries and deterministic semantic query answering."""

import re
from typing import Any
import numpy as np
import pandas as pd

from app.core.config import Settings
from app.schemas.analytics import AggregationRequest
from app.schemas.query import NaturalLanguageQueryResponse, QueryIntent
from app.services.analytics_service import AnalyticsService
from app.services.dataset_service import DatasetNotFoundError, DatasetService


class QueryInterpretationError(ValueError):
    """Raised when an inquiry cannot be resolved or mapped to dataset attributes."""


class QueryService:
    """Interprets plain-English questions and executes deterministic analytical operations."""

    SYNONYM_MAP: dict[str, list[str]] = {
        "revenue": ["revenue", "sales", "turnover", "income", "billings"],
        "profit": ["profit", "margin", "earnings", "net_income"],
        "cost": ["cost", "spend", "ad_spend", "marketing_spend", "expense", "budget"],
        "units": ["units", "volume", "quantity", "count", "headcount", "customers", "users"],
        "price": ["price", "fee", "rate", "cost_per_unit"],
        "region": ["region", "geography", "location", "territory", "zone", "state", "city"],
        "store": ["store", "branch", "shop", "outlet"],
        "department": ["department", "dept", "division", "team"],
        "product": ["product", "item", "sku", "service", "offering"],
        "category": ["category", "type", "segment", "tier", "class"],
    }

    AGG_KEYWORDS: dict[str, str] = {
        "total": "sum",
        "sum": "sum",
        "combined": "sum",
        "altogether": "sum",
        "average": "mean",
        "avg": "mean",
        "mean": "mean",
        "typical": "mean",
        "median": "median",
        "minimum": "min",
        "min": "min",
        "lowest": "min",
        "smallest": "min",
        "maximum": "max",
        "max": "max",
        "highest": "max",
        "largest": "max",
        "peak": "max",
    }

    @classmethod
    def _find_matching_column(
        cls,
        tokens: list[str],
        columns: list[str],
        numeric_only: bool = False,
        df: pd.DataFrame | None = None,
    ) -> str | None:
        """Fuzzy and synonym-aware column resolver."""
        col_lower_map = {c.lower(): c for c in columns}

        # 1. Exact match with any token or multi-token ngram
        for token in tokens:
            if token in col_lower_map:
                col = col_lower_map[token]
                if not numeric_only or (df is not None and pd.api.types.is_numeric_dtype(df[col])):
                    return col

        # 2. Substring matching
        for token in tokens:
            if len(token) >= 3:
                for c_lower, orig_col in col_lower_map.items():
                    if token in c_lower or c_lower in token:
                        if not numeric_only or (df is not None and pd.api.types.is_numeric_dtype(df[orig_col])):
                            return orig_col

        # 3. Synonym matching
        for concept, synonyms in cls.SYNONYM_MAP.items():
            if any(syn in tokens for syn in synonyms):
                for syn in synonyms:
                    for c_lower, orig_col in col_lower_map.items():
                        if syn in c_lower:
                            if not numeric_only or (df is not None and pd.api.types.is_numeric_dtype(df[orig_col])):
                                return orig_col

        return None

    @classmethod
    def execute_query(
        cls,
        dataset_id: str,
        query: str,
        settings: Settings,
    ) -> NaturalLanguageQueryResponse:
        """Parse natural language question, execute deterministic analytics, and format answer."""
        df = DatasetService.get_dataframe(dataset_id=dataset_id, settings=settings)
        q_clean = query.strip().lower()
        tokens = re.findall(r"\b[a-z0-9_]+\b", q_clean)

        numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
        cat_cols = list(df.select_dtypes(include=["object", "category", "string"]).columns)

        # -------------------------------------------------------------
        # Intent 1: General Dataset Count / Size
        # -------------------------------------------------------------
        if any(phrase in q_clean for phrase in ["how many rows", "row count", "how big", "how many records", "number of rows"]):
            return NaturalLanguageQueryResponse(
                dataset_id=dataset_id,
                query=query,
                intent="general_count",
                answer=f"The dataset contains {len(df):,} rows and {len(df.columns)} columns.",
                data_preview=[{"row_count": len(df), "column_count": len(df.columns)}],
                confidence=0.95,
            )

        # -------------------------------------------------------------
        # Intent 2: Correlation Inquiry
        # -------------------------------------------------------------
        if any(term in q_clean for term in ["correlation", "correlated", "relate", "relationship", "dependence"]):
            if len(numeric_cols) < 2:
                raise QueryInterpretationError("Correlation analysis requires at least two numeric columns in the dataset.")

            corr_res = AnalyticsService.compute_correlation(dataset_id=dataset_id, settings=settings)
            # Find if specific columns were mentioned
            matched_num_cols = [c for c in numeric_cols if c.lower() in q_clean]

            if len(matched_num_cols) >= 2:
                c1, c2 = matched_num_cols[0], matched_num_cols[1]
                val = corr_res.matrix.get(c1, {}).get(c2)
                strength = "strong" if val and abs(val) >= 0.7 else "moderate" if val and abs(val) >= 0.4 else "weak"
                ans = f"The Pearson correlation between '{c1}' and '{c2}' is {val:.3f} ({strength})."
                preview = [{"feature_x": c1, "feature_y": c2, "correlation": val}]
            elif corr_res.top_correlations:
                top = corr_res.top_correlations[0]
                ans = (
                    f"The strongest relationship in this dataset is between '{top.feature_x}' and '{top.feature_y}' "
                    f"with a correlation coefficient of {top.coefficient:.3f} ({top.strength.replace('_', ' ')})."
                )
                preview = [top.model_dump() for top in corr_res.top_correlations[:5]]
            else:
                ans = "No significant numeric correlations were identified."
                preview = None

            return NaturalLanguageQueryResponse(
                dataset_id=dataset_id,
                query=query,
                intent="correlation_inquiry",
                answer=ans,
                data_preview=preview,
                confidence=0.92,
            )

        # -------------------------------------------------------------
        # Intent 3: Outlier / Anomaly Inquiry
        # -------------------------------------------------------------
        if any(term in q_clean for term in ["outlier", "anomaly", "anomalies", "abnormal", "unusual", "spike"]):
            target_col = cls._find_matching_column(tokens, numeric_cols, numeric_only=True, df=df) or (numeric_cols[0] if numeric_cols else None)
            if not target_col:
                raise QueryInterpretationError("No numeric column found to evaluate for outliers.")

            outlier_res = AnalyticsService.detect_outliers(dataset_id=dataset_id, column=target_col, settings=settings)
            count = outlier_res.outlier_count
            if count > 0:
                highest_outlier = outlier_res.outliers[0].value
                ans = (
                    f"Found {count} statistical outlier(s) in '{target_col}' (lower bound: {outlier_res.lower_bound:,.2f}, "
                    f"upper bound: {outlier_res.upper_bound:,.2f}). Most extreme value: {highest_outlier:,.2f}."
                )
                preview = [o.model_dump() for o in outlier_res.outliers[:5]]
            else:
                ans = f"No statistical anomalies were detected in '{target_col}' under standard IQR thresholds."
                preview = []

            return NaturalLanguageQueryResponse(
                dataset_id=dataset_id,
                query=query,
                intent="anomaly_inquiry",
                target_metric=target_col,
                answer=ans,
                data_preview=preview,
                confidence=0.90,
            )

        # -------------------------------------------------------------
        target_dim = cls._find_matching_column(tokens, cat_cols, numeric_only=False, df=df)
        target_metric = cls._find_matching_column(tokens, numeric_cols, numeric_only=True, df=df)

        # Inferred aggregation function
        agg_func = "sum"
        for kw, func in cls.AGG_KEYWORDS.items():
            if kw in tokens:
                agg_func = func
                break

        # -------------------------------------------------------------
        # Intent 4: Ranking Extreme (e.g. "top store", "highest revenue")
        # -------------------------------------------------------------
        if any(term in tokens for term in ["top", "highest", "best", "lowest", "worst", "bottom"]):
            metric = target_metric or (numeric_cols[0] if numeric_cols else None)
            dim = target_dim or (cat_cols[0] if cat_cols else None)

            if metric:
                is_ascending = any(term in tokens for term in ["lowest", "worst", "bottom", "least"])
                sorted_df = df.sort_values(by=metric, ascending=is_ascending).head(5)

                top_val = float(sorted_df[metric].iloc[0])
                top_name = str(sorted_df[dim].iloc[0]) if dim else f"Row {sorted_df.index[0]}"
                direction_word = "lowest" if is_ascending else "highest"

                ans = f"The {direction_word} '{metric}' is {top_val:,.2f} (associated with '{top_name}')."
                preview = (
                    sorted_df.astype(object)
                    .where(pd.notna(sorted_df), None)
                    .to_dict(orient="records")
                )

                return NaturalLanguageQueryResponse(
                    dataset_id=dataset_id,
                    query=query,
                    intent="ranking_extreme",
                    target_metric=metric,
                    group_by_dimension=dim,
                    answer=ans,
                    data_preview=preview,
                    confidence=0.85,
                )

        # -------------------------------------------------------------
        # Intent 5: Grouped Aggregation (e.g. "sales by region", "budget per dept")
        # -------------------------------------------------------------
        has_by_phrase = any(w in tokens for w in ["by", "per", "across", "for each"])

        if (has_by_phrase or target_dim) and target_dim and target_metric:
            req = AggregationRequest(
                group_by=[target_dim],
                metrics={target_metric: [agg_func]},  # type: ignore[list-item]
                sort_by=f"{target_metric}_{agg_func}",
                ascending=False,
                limit=10,
            )
            agg_res = AnalyticsService.compute_aggregations(dataset_id=dataset_id, request=req, settings=settings)
            records = agg_res.data
            metric_key = f"{target_metric}_{agg_func}"

            if records:
                top_row = records[0]
                ans = (
                    f"Grouped '{target_metric}' by '{target_dim}' ({agg_func}). Top result: '{top_row[target_dim]}' "
                    f"with {top_row[metric_key]:,.2f}."
                )
            else:
                ans = f"No grouped records returned for '{target_dim}'."

            return NaturalLanguageQueryResponse(
                dataset_id=dataset_id,
                query=query,
                intent="grouped_aggregation",
                target_metric=target_metric,
                group_by_dimension=target_dim,
                answer=ans,
                data_preview=records,
                confidence=0.88,
            )


        # -------------------------------------------------------------
        # Intent 6: Filtered Metric (e.g. "revenue in North", "profit for Store A")
        # -------------------------------------------------------------
        for cat in cat_cols:
            unique_vals = [str(v) for v in df[cat].dropna().unique() if len(str(v)) > 1]
            for val in unique_vals:
                if val.lower() in q_clean:
                    metric = target_metric or (numeric_cols[0] if numeric_cols else None)
                    if metric:
                        filtered = df[df[cat].astype(str).str.lower() == val.lower()]
                        val_sum = float(filtered[metric].sum())
                        val_avg = float(filtered[metric].mean())
                        ans = (
                            f"Filtered by {cat}='{val}': Total '{metric}' is {val_sum:,.2f} "
                            f"(average: {val_avg:,.2f} across {len(filtered):,} records)."
                        )
                        preview = (
                            filtered.head(5)
                            .astype(object)
                            .where(pd.notna(filtered), None)
                            .to_dict(orient="records")
                        )
                        return NaturalLanguageQueryResponse(
                            dataset_id=dataset_id,
                            query=query,
                            intent="filtered_metric",
                            target_metric=metric,
                            group_by_dimension=cat,
                            filter_description=f"{cat} == '{val}'",
                            answer=ans,
                            data_preview=preview,
                            confidence=0.87,
                        )

        # -------------------------------------------------------------
        # Intent 7: Default Metric Summary (e.g. "total sales", "average revenue")
        # -------------------------------------------------------------
        metric = target_metric or (numeric_cols[0] if numeric_cols else None)
        if metric:
            clean_s = df[metric].dropna()
            func_name = agg_func
            if func_name == "mean":
                computed_val = float(clean_s.mean())
            elif func_name == "min":
                computed_val = float(clean_s.min())
            elif func_name == "max":
                computed_val = float(clean_s.max())
            elif func_name == "median":
                computed_val = float(clean_s.median())
            else:
                computed_val = float(clean_s.sum())

            ans = f"The {func_name} for '{metric}' is {computed_val:,.2f} (calculated across {len(clean_s):,} values)."
            preview = [{f"{metric}_{func_name}": round(computed_val, 2), "non_null_count": len(clean_s)}]

            return NaturalLanguageQueryResponse(
                dataset_id=dataset_id,
                query=query,
                intent="metric_summary",
                target_metric=metric,
                answer=ans,
                data_preview=preview,
                confidence=0.80,
            )

        # Unrecognized fallback
        return NaturalLanguageQueryResponse(
            dataset_id=dataset_id,
            query=query,
            intent="unrecognized",
            answer=(
                f"Could not clearly map '{query}' to available attributes. "
                f"Available metrics: {numeric_cols}. Available dimensions: {cat_cols}."
            ),
            data_preview=None,
            confidence=0.20,
        )
