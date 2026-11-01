"""Pydantic schemas for deterministic data analytics, correlations, aggregations, and anomaly detection."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

CorrelationMethod = Literal["pearson", "spearman"]
AnomalyMethod = Literal["iqr", "zscore", "hybrid"]
AggregateFunction = Literal["sum", "mean", "median", "min", "max", "count"]


class CorrelationPair(BaseModel):
    """Pairwise correlation metric between two numeric features."""

    model_config = ConfigDict(extra="ignore")

    feature_x: str = Field(description="First feature name")
    feature_y: str = Field(description="Second feature name")
    coefficient: float = Field(description="Correlation coefficient (-1.0 to 1.0)")
    strength: str = Field(description="Descriptive strength category (e.g. strong_positive, moderate_negative)")


class CorrelationResponse(BaseModel):
    """Full correlation matrix and ranked top correlations for a dataset."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str = Field(description="Unique dataset identifier")
    method: CorrelationMethod = Field(description="Correlation algorithm applied")
    features: list[str] = Field(description="List of numeric feature names analyzed")
    matrix: dict[str, dict[str, float | None]] = Field(description="2D correlation coefficient matrix")
    top_correlations: list[CorrelationPair] = Field(
        default_factory=list,
        description="Ranked distinct pairwise correlations sorted by absolute strength",
    )


class AggregationRequest(BaseModel):
    """Specification for grouped aggregation queries."""

    model_config = ConfigDict(extra="forbid")

    group_by: list[str] = Field(min_length=1, description="One or more categorical columns to group by")
    metrics: dict[str, list[AggregateFunction]] = Field(
        description="Mapping from numeric column names to list of aggregation functions (e.g. {'sales': ['sum', 'mean']})"
    )
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum aggregated rows to return")
    sort_by: str | None = Field(default=None, description="Optional column name to sort aggregated results by")
    ascending: bool = Field(default=False, description="Sort direction when sort_by is specified")


class AggregationResponse(BaseModel):
    """Results of a grouped dataset aggregation."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str = Field(description="Unique dataset identifier")
    group_by: list[str] = Field(description="Columns grouped by")
    row_count: int = Field(ge=0, description="Total aggregated rows returned")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Aggregated tabular records")


class OutlierRecord(BaseModel):
    """Individual anomaly or outlier detected in a numeric column."""

    model_config = ConfigDict(extra="ignore")

    row_index: int = Field(ge=0, description="0-indexed row position in the dataset")
    value: float = Field(description="Observed outlier value")
    score: float = Field(description="Distance metric (IQR distance or Z-score value)")


class AnomalyDetectionResponse(BaseModel):
    """Anomaly and outlier detection results for a specific column."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str = Field(description="Unique dataset identifier")
    column: str = Field(description="Analyzed numeric column")
    method: AnomalyMethod = Field(description="Statistical anomaly detection method (iqr or zscore)")
    total_rows: int = Field(ge=0, description="Number of non-null values analyzed")
    outlier_count: int = Field(ge=0, description="Count of detected outliers")
    outlier_percentage: float = Field(ge=0.0, le=100.0, description="Percentage of values identified as outliers")
    lower_bound: float = Field(description="Computed lower threshold boundary")
    upper_bound: float = Field(description="Computed upper threshold boundary")
    outliers: list[OutlierRecord] = Field(default_factory=list, description="Detected outlier records")
