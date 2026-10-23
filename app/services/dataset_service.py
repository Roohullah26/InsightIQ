"""Service layer for dataset validation, ingestion, exploratory profiling, and persistence."""

from datetime import datetime, timezone
import io
import json
from pathlib import Path
from typing import Any
import uuid

import numpy as np
import pandas as pd

from app.core.config import Settings
from app.schemas.dataset import (
    ColumnDtypeCategory,
    ColumnProfile,
    DatasetProfile,
    DatasetSummary,
    DatasetUploadResponse,
)


class DatasetValidationError(ValueError):
    """Raised when an uploaded dataset violates validation rules or constraints."""


class DatasetNotFoundError(FileNotFoundError):
    """Raised when a requested dataset ID does not exist."""


class DatasetService:
    """Handles dataset ingestion, validation, exploratory analysis, and storage."""

    @staticmethod
    def _infer_column_category(series: pd.Series) -> ColumnDtypeCategory:
        """Categorize a pandas Series into high-level semantic types."""
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        # Check if object column can reasonably be parsed as datetime
        non_null = series.dropna()
        if len(non_null) > 0 and len(non_null) <= 500:
            try:
                pd.to_datetime(non_null.iloc[:20], errors="raise", format="mixed")
                return "datetime"
            except (ValueError, TypeError):
                pass


        # Distinguish categorical (low cardinality) from free-form text
        total_count = len(series)
        unique_count = series.nunique(dropna=True)
        if total_count > 0:
            distinct_pct = (unique_count / total_count) * 100
            if unique_count <= 50 or distinct_pct <= 20.0:
                return "categorical"

        return "text"

    @classmethod
    def _compute_column_profile(cls, series: pd.Series) -> ColumnProfile:
        """Compute detailed statistical summary for a single column."""
        total_rows = len(series)
        null_count = int(series.isna().sum())
        null_pct = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0.0
        distinct_count = int(series.nunique(dropna=True))
        distinct_pct = round((distinct_count / total_rows) * 100, 2) if total_rows > 0 else 0.0

        category = cls._infer_column_category(series)
        clean = series.dropna()

        # Representative non-null samples (up to 5 distinct values)
        samples = [
            str(x) if not isinstance(x, (int, float, bool)) else (None if pd.isna(x) else x)
            for x in clean.unique()[:5]
        ]

        stats: dict[str, Any] = {}
        if category == "numeric" and len(clean) > 0:
            numeric_vals = pd.to_numeric(clean, errors="coerce").dropna()
            if len(numeric_vals) > 0:
                std_val = numeric_vals.std()
                stats = {
                    "min": float(numeric_vals.min()),
                    "max": float(numeric_vals.max()),
                    "mean": round(float(numeric_vals.mean()), 4),
                    "median": round(float(numeric_vals.median()), 4),
                    "std": round(float(std_val), 4) if pd.notna(std_val) else None,
                    "q25": round(float(numeric_vals.quantile(0.25)), 4),
                    "q75": round(float(numeric_vals.quantile(0.75)), 4),
                }
        elif category in ("categorical", "text") and len(clean) > 0:
            val_counts = clean.value_counts()
            if not val_counts.empty:
                stats = {
                    "most_frequent_value": str(val_counts.index[0]),
                    "frequency_of_most_frequent": int(val_counts.iloc[0]),
                }

        return ColumnProfile(
            name=str(series.name),
            category=category,
            native_dtype=str(series.dtype),
            null_count=null_count,
            null_percentage=null_pct,
            distinct_count=distinct_count,
            distinct_percentage=distinct_pct,
            sample_values=samples,
            stats=stats if stats else None,
        )

    @classmethod
    def profile_dataframe(
        cls,
        df: pd.DataFrame,
        dataset_id: str,
        filename: str,
        uploaded_at: str,
    ) -> DatasetProfile:
        """Generate full EDA profile for a loaded DataFrame."""
        row_count = len(df)
        column_count = len(df.columns)
        memory_usage = int(df.memory_usage(deep=True).sum())

        column_profiles = [cls._compute_column_profile(df[col]) for col in df.columns]

        # Generate preview rows with NaN/None properly converted for JSON safety
        preview_df = df.head(5).copy()
        # Replace NaN with None
        preview_records = (
            preview_df.astype(object)
            .where(pd.notna(preview_df), None)
            .to_dict(orient="records")
        )

        return DatasetProfile(
            dataset_id=dataset_id,
            filename=filename,
            uploaded_at=uploaded_at,
            row_count=row_count,
            column_count=column_count,
            memory_usage_bytes=memory_usage,
            columns=column_profiles,
            preview=preview_records,
        )

    @classmethod
    def ingest_csv(
        cls,
        file_bytes: bytes,
        filename: str,
        settings: Settings,
    ) -> DatasetUploadResponse:
        """Validate, decode, profile, and persist an uploaded CSV file."""
        # 1. Validation checks
        if not file_bytes or len(file_bytes.strip()) == 0:
            raise DatasetValidationError("Uploaded file is empty.")

        if len(file_bytes) > settings.max_upload_size_bytes:
            limit_mb = settings.max_upload_size_bytes / (1024 * 1024)
            raise DatasetValidationError(
                f"File size exceeds maximum allowed limit of {limit_mb:.1f} MB."
            )

        if not filename.lower().endswith(".csv"):
            raise DatasetValidationError("Only CSV (.csv) files are supported for ingestion.")

        # 2. Encoding detection and parsing
        decoded_text: str | None = None
        for enc in ("utf-8", "utf-8-sig", "latin1", "cp1252"):
            try:
                decoded_text = file_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None:
            raise DatasetValidationError("Unable to decode CSV file with supported encodings (UTF-8, Latin-1).")

        try:
            df = pd.read_csv(io.StringIO(decoded_text))
        except Exception as exc:
            raise DatasetValidationError(f"Malformed CSV content: {exc}") from exc

        if df.empty or len(df.columns) == 0:
            raise DatasetValidationError("The parsed dataset contains no columns or data rows.")

        if len(df) > settings.max_rows_limit:
            raise DatasetValidationError(
                f"Dataset row count ({len(df):,}) exceeds the configured limit of {settings.max_rows_limit:,} rows."
            )

        if len(df.columns) > settings.max_columns_limit:
            raise DatasetValidationError(
                f"Dataset column count ({len(df.columns)}) exceeds the configured limit of {settings.max_columns_limit} columns."
            )

        # 3. Identifiers and persistence paths
        dataset_id = uuid.uuid4().hex
        uploaded_at = datetime.now(timezone.utc).isoformat()
        storage_dir = Path(settings.data_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)

        csv_path = storage_dir / f"{dataset_id}.csv"
        meta_path = storage_dir / f"{dataset_id}.json"

        # Save normalized CSV
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # 4. Profile generation
        profile = cls.profile_dataframe(
            df=df,
            dataset_id=dataset_id,
            filename=filename,
            uploaded_at=uploaded_at,
        )

        summary = DatasetSummary(
            dataset_id=dataset_id,
            filename=filename,
            uploaded_at=uploaded_at,
            file_size_bytes=len(file_bytes),
            row_count=len(df),
            column_count=len(df.columns),
            columns=[str(c) for c in df.columns],
        )

        # Persist metadata / profile JSON
        meta_payload = {
            "summary": summary.model_dump(),
            "profile": profile.model_dump(),
        }
        meta_path.write_text(json.dumps(meta_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return DatasetUploadResponse(
            message="Dataset successfully uploaded and profiled.",
            summary=summary,
            profile=profile,
        )

    @classmethod
    def get_dataset_profile(cls, dataset_id: str, settings: Settings) -> DatasetProfile:
        """Retrieve stored profile metadata for a given dataset ID."""
        meta_path = Path(settings.data_dir) / f"{dataset_id}.json"
        if not meta_path.exists():
            raise DatasetNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return DatasetProfile.model_validate(data["profile"])

    @classmethod
    def list_datasets(cls, settings: Settings) -> list[DatasetSummary]:
        """List summaries of all ingested datasets."""
        storage_dir = Path(settings.data_dir)
        if not storage_dir.exists():
            return []

        summaries: list[DatasetSummary] = []
        for meta_file in sorted(storage_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                if "summary" in data:
                    summaries.append(DatasetSummary.model_validate(data["summary"]))
            except Exception:
                continue

        return summaries

    @classmethod
    def get_dataframe(cls, dataset_id: str, settings: Settings) -> pd.DataFrame:
        """Load the persisted DataFrame for analysis."""
        csv_path = Path(settings.data_dir) / f"{dataset_id}.csv"
        if not csv_path.exists():
            raise DatasetNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

        return pd.read_csv(csv_path)
