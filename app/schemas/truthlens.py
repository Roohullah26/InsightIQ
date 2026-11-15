"""Pydantic schemas for InsightIQ TruthLens — Evidence-Based Intelligence Engine."""

from typing import Any, Literal
from pydantic import BaseModel, Field

TruthLensSeverity = Literal["Critical", "High", "Medium", "Low"]
TruthLensConfidence = Literal["High", "Medium", "Low"]
TruthLensCategory = Literal[
    "kpi_contradiction",
    "hidden_segment_decline",
    "sampling_and_response_bias",
    "misleading_averages",
    "incomplete_comparisons",
    "data_quality_problems",
    "correlation_vs_causation",
    "statistical_anomalies",
]


class TruthLensChartDataset(BaseModel):
    """Single data series for supporting TruthLens chart visualization."""

    label: str = Field(..., description="Series display label")
    data: list[float] = Field(..., description="Numeric values aligned with chart labels")
    unit: str | None = Field(default=None, description="Optional unit symbol such as '$', '%', or 'count'")


class TruthLensChartSpec(BaseModel):
    """Chart specification for visual verification of a TruthLens finding."""

    chart_type: Literal["bar", "line", "horizontalBar", "scatter"] = Field(
        default="bar",
        description="Recommended chart rendering type",
    )
    title: str = Field(..., description="Chart title summarizing the visual evidence")
    labels: list[str] = Field(..., description="X-axis or category labels")
    datasets: list[TruthLensChartDataset] = Field(..., description="One or more numeric series")
    reference_value: float | None = Field(
        default=None,
        description="Optional horizontal reference line value (e.g., global mean or upper IQR fence)",
    )
    reference_label: str | None = Field(
        default=None,
        description="Optional label for the horizontal reference line",
    )


class TruthLensFinding(BaseModel):
    """Mandatory structured evidence-based finding produced by TruthLens."""

    id: str = Field(..., description="Unique deterministic finding identifier")
    title: str = Field(..., description="Concise issue title")
    severity: TruthLensSeverity = Field(
        ...,
        description="Severity level: Critical, High, Medium, or Low",
    )
    category: TruthLensCategory = Field(
        ...,
        description="Machine-readable detection category key",
    )
    category_label: str = Field(
        ...,
        description="Human-readable detection category label",
    )
    what_happened: str = Field(
        ...,
        description="Factual statement of what occurred in the data",
    )
    supporting_evidence: str = Field(
        ...,
        description="Exact numerical evidence verifying the observation",
    )
    comparison_baseline: str = Field(
        ...,
        description="Comparison period, peer segment benchmark, or statistical baseline",
    )
    why_it_matters: str = Field(
        ...,
        description="Business and analytical impact of this finding",
    )
    hypotheses: list[str] = Field(
        default_factory=list,
        description="Possible explanations, explicitly framed as unproven hypotheses",
    )
    confidence_level: TruthLensConfidence = Field(
        ...,
        description="Confidence level in the empirical observation (High, Medium, Low)",
    )
    confidence_justification: str = Field(
        ...,
        description="Statistical or data-completeness justification for the confidence level",
    )
    recommended_investigation: list[str] = Field(
        default_factory=list,
        description="Actionable next steps to investigate and validate the root cause",
    )
    relevant_columns: list[str] = Field(
        default_factory=list,
        description="Dataset column names used to derive this finding",
    )
    calculations: list[str] = Field(
        default_factory=list,
        description="Exact mathematical formulas and calculations executed",
    )
    supporting_row_references: list[str] = Field(
        default_factory=list,
        description="Exact row indices or record identifiers supporting this finding",
    )
    group_references: list[str] = Field(
        default_factory=list,
        description="Aggregated group or period-segment partition references supporting this finding",
    )
    calculation_methodology: str = Field(
        default="",
        description="Explicit mathematical formula and aggregation methodology applied",
    )
    comparison_periods: list[str] = Field(
        default_factory=list,
        description="Baseline and target comparison periods or benchmark partitions evaluated",
    )
    data_quality_warnings: list[str] = Field(
        default_factory=list,
        description="Data quality caveats or sample depth warnings qualifying this finding",
    )
    ai_explanation: str = Field(
        ...,
        description="Grounded AI narrative explaining the verified finding without inventing causes",
    )
    evidence_table: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tabular rows of supporting numerical evidence traceable to the dataset",
    )
    source_rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Filtered subset of raw dataset records supporting this finding",
    )
    chart_spec: TruthLensChartSpec | None = Field(
        default=None,
        description="Optional chart specification for visual inspection",
    )


class InsufficientEvidenceNotice(BaseModel):
    """Explicit notice when a detection check cannot run due to missing schema or sample depth."""

    category: TruthLensCategory = Field(..., description="Detection category evaluated")
    category_label: str = Field(..., description="Human-readable category name")
    reason: str = Field(
        ...,
        description="Explanation of why evidence is insufficient to generate a finding",
    )
    required_signals: list[str] = Field(
        default_factory=list,
        description="Columns or data structure required to enable this check",
    )


class DataReliabilityIndicator(BaseModel):
    """Summary of dataset reliability and trustworthiness for executive decision-making."""

    score: float = Field(..., ge=0.0, le=100.0, description="Overall reliability score (0-100)")
    status: Literal["High Reliability", "Moderate Caution", "High Distortion Risk"] = Field(
        ...,
        description="Executive reliability classification",
    )
    completeness_pct: float = Field(..., ge=0.0, le=100.0)
    sample_size: int = Field(..., ge=0)
    has_temporal_dimension: bool = Field(default=False)
    has_segment_dimension: bool = Field(default=False)
    distortion_flags: list[str] = Field(
        default_factory=list,
        description="Key reliability warnings (e.g., response drop, outlier skew, small sample)",
    )


class TruthLensSummaryCounts(BaseModel):
    """Top-level alert counters for the TruthLens dashboard header."""

    total_findings: int = Field(..., ge=0)
    critical_and_high_count: int = Field(..., ge=0)
    critical_count: int = Field(..., ge=0)
    high_count: int = Field(..., ge=0)
    medium_count: int = Field(..., ge=0)
    low_count: int = Field(..., ge=0)
    kpi_contradictions_count: int = Field(..., ge=0)
    segment_warnings_count: int = Field(..., ge=0)
    statistical_anomalies_count: int = Field(..., ge=0)
    bias_and_averages_count: int = Field(..., ge=0)


class TruthLensScenarioMeta(BaseModel):
    """Metadata describing a built-in TruthLens demonstration scenario."""

    scenario_key: Literal["scenario_a", "scenario_b", "scenario_c"]
    title: str
    subtitle: str
    description: str
    filename: str


class TruthLensReportResponse(BaseModel):
    """Complete 5-layer TruthLens analysis report for a dataset."""

    dataset_id: str
    filename: str
    generated_at: str
    row_count: int = Field(default=0, ge=0, description="Total rows in the evaluated dataset")
    column_count: int = Field(default=0, ge=0, description="Total columns in the evaluated dataset")
    comparison_periods: list[str] = Field(
        default_factory=list,
        description="Detected temporal comparison periods or snapshot scope",
    )
    data_quality_warnings: list[str] = Field(
        default_factory=list,
        description="Dataset-level data quality warnings for the Dataset Trace View",
    )
    executive_verdict: str = Field(
        ...,
        description="High-level evidence-based synthesis of misleading KPIs and risks",
    )
    summary_counts: TruthLensSummaryCounts
    reliability: DataReliabilityIndicator
    detected_roles: dict[str, Any] = Field(
        default_factory=dict,
        description="Layer 1 semantic column mapping discovered in the dataset",
    )
    findings: list[TruthLensFinding] = Field(
        default_factory=list,
        description="Prioritized list of evidence-backed findings",
    )
    insufficient_evidence: list[InsufficientEvidenceNotice] = Field(
        default_factory=list,
        description="Transparent notices where data was insufficient to make claims",
    )

