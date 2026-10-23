"""Pydantic schemas for system health and diagnostic endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Structured health and status metadata for InsightIQ."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="healthy", description="Overall service status")
    app_name: str = Field(description="Configured application name")
    environment: str = Field(description="Operational environment (e.g. development, staging, production)")
    version: str = Field(description="Software version identifier")
    uptime_seconds: float = Field(ge=0.0, description="Elapsed seconds since application startup")
