"""Pydantic models and schemas for dataset ingestion, schemas, and profiling."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

ColumnDtypeCategory = Literal["numeric", "categorical", "datetime", "boolean", "text"]


class ColumnProfile(BaseModel):
    """Detailed statistical and structural profile of a single dataset column."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Column name")
    category: ColumnDtypeCategory = Field(description="Inferred semantic data category")
    native_dtype: str = Field(description="Native Pandas or NumPy data type string")
    null_count: int = Field(ge=0, description="Number of missing or null entries")
    null_percentage: float = Field(ge=0.0, le=100.0, description="Percentage of null values")
    distinct_count: int = Field(ge=0, description="Number of unique non-null values")
    distinct_percentage: float = Field(ge=0.0, le=100.0, description="Unique values as percentage of total rows")
    sample_values: list[Any] = Field(default_factory=list, description="Sample representative values from this column")
    stats: dict[str, Any] | None = Field(default=None, description="Statistical summaries (e.g. min, max, mean, quartiles)")
    is_identifier: bool = Field(default=False, description="True if column is an identifier (ID/UUID/key/code/zip/phone or sequential integers) and must not be used as a metric")


class DatasetSummary(BaseModel):
    """Compact summary of a stored dataset."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str = Field(description="Unique dataset identifier (UUID4)")
    filename: str = Field(description="Original filename uploaded by the user")
    uploaded_at: str = Field(description="ISO timestamp of dataset upload")
    file_size_bytes: int = Field(ge=0, description="Original file size in bytes")
    row_count: int = Field(ge=0, description="Total number of records/rows")
    column_count: int = Field(ge=0, description="Total number of attributes/columns")
    columns: list[str] = Field(default_factory=list, description="List of column names")


class DatasetProfile(BaseModel):
    """Full exploratory data analysis profile of an ingested dataset."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str = Field(description="Unique dataset identifier")
    filename: str = Field(description="Original uploaded filename")
    uploaded_at: str = Field(description="ISO timestamp of upload")
    row_count: int = Field(ge=0, description="Total rows in dataset")
    column_count: int = Field(ge=0, description="Total columns in dataset")
    memory_usage_bytes: int = Field(ge=0, description="Memory footprint in bytes")
    columns: list[ColumnProfile] = Field(default_factory=list, description="Column-level profiles")
    preview: list[dict[str, Any]] = Field(default_factory=list, description="Sample first rows preview")


class DatasetUploadResponse(BaseModel):
    """Response returned upon successful CSV upload and ingestion."""

    model_config = ConfigDict(extra="ignore")

    message: str = "Dataset successfully uploaded and profiled."
    summary: DatasetSummary
    profile: DatasetProfile
