"""Pydantic schemas for AI-powered business insights and executive synthesis."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

InsightCategory = Literal[
    "executive_summary",
    "data_quality",
    "trend",
    "correlation",
    "anomaly",
    "risk",
    "recommendation",
]

InsightSeverity = Literal["info", "positive", "warning", "critical"]


class InsightItem(BaseModel):
    """An individual actionable finding, anomaly, correlation, or business recommendation."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(description="Punchy, executive-level headline")
    category: InsightCategory = Field(description="Insight classification")
    severity: InsightSeverity = Field(description="Business urgency or sentiment tier")
    summary: str = Field(description="Detailed narrative explaining the observation")
    evidence: str = Field(description="Concrete quantitative evidence backing this finding")
    recommendation: str | None = Field(default=None, description="Actionable business or data engineering next step")


class DataQualityScore(BaseModel):
    """Multi-factor data quality assessment."""

    model_config = ConfigDict(extra="ignore")

    overall_score: float = Field(ge=0.0, le=100.0, description="Overall health score (0-100)")
    completeness_score: float = Field(ge=0.0, le=100.0, description="Percentage of non-null records")
    anomaly_score: float = Field(ge=0.0, le=100.0, description="Metric stability score (penalizes extreme outliers)")
    notes: list[str] = Field(default_factory=list, description="Observations regarding missingness or data hygiene")


class DatasetInsightsResponse(BaseModel):
    """Comprehensive executive intelligence briefing for a dataset."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str = Field(description="Unique dataset identifier")
    filename: str = Field(description="Original filename analyzed")
    generated_at: str = Field(description="ISO timestamp of insight generation")
    executive_summary: str = Field(description="High-level strategic briefing synthesizing main takeaways")
    data_quality: DataQualityScore = Field(description="Data reliability and cleanliness metrics")
    key_metrics: dict[str, Any] = Field(default_factory=dict, description="Primary quantitative metrics and totals")
    insights: list[InsightItem] = Field(default_factory=list, description="Categorized actionable insights")
