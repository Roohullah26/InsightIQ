"""Pydantic schemas for natural language data querying and semantic question answering."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

QueryIntent = Literal[
    "metric_summary",
    "grouped_aggregation",
    "ranking_extreme",
    "filtered_metric",
    "correlation_inquiry",
    "anomaly_inquiry",
    "general_count",
    "open_ended_reasoning",
    "risk_analysis",
    "chart_request",
    "unrecognized",
]


class NaturalLanguageQueryRequest(BaseModel):
    """Input payload for natural language inquiries."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=2,
        max_length=500,
        description="Natural language question about the dataset (e.g. 'What is the average sales by region?')",
    )


class NaturalLanguageQueryResponse(BaseModel):
    """Structured response containing direct conversational answer and supporting data."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str = Field(description="Unique dataset identifier")
    query: str = Field(description="Original user inquiry")
    intent: QueryIntent = Field(description="Inferred analytical query intent")
    source: Literal["ai_model", "deterministic_engine"] = Field(
        default="deterministic_engine",
        description="Engine used to answer: 'ai_model' (LLM) or 'deterministic_engine' (local heuristics)",
    )
    target_metric: str | None = Field(default=None, description="Primary numeric column identified")
    group_by_dimension: str | None = Field(default=None, description="Categorical dimension identified for grouping")
    filter_description: str | None = Field(default=None, description="Human-readable filter condition if applied")
    answer: str = Field(description="Direct, synthesized plain-English answer to the question")
    data_preview: list[dict[str, Any]] | None = Field(
        default=None,
        description="Structured tabular rows backing the natural language answer",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score of the intent parsing (0.0 to 1.0)")
    chart: dict[str, Any] | None = Field(
        default=None,
        description="Inline chart spec (type bar|scatter, labels/values or points) for rendering in chat",
    )
    action: dict[str, Any] | None = Field(
        default=None,
        description="Clickable follow-up action (label, target_tab, and pre-selected variables)",
    )


class QuerySuggestionsResponse(BaseModel):
    """Dataset-specific Quick Metrics prompt chips."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str
    primary_metric: str | None = None
    primary_dimension: str | None = None
    excluded_identifiers: list[str] = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)

