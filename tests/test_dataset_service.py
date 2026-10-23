"""Unit tests for the DatasetService data validation and profiling layer."""

import pytest
from app.core.config import Settings
from app.services.dataset_service import (
    DatasetNotFoundError,
    DatasetService,
    DatasetValidationError,
)


@pytest.fixture
def temp_settings(tmp_path):
    """Provide isolated Settings pointing to a temporary data directory."""
    return Settings(
        app_name="Test Platform",
        environment="development",
        data_dir=tmp_path / "test_data",
        max_upload_size_bytes=1024 * 1024,  # 1 MB
        max_rows_limit=5000,
        max_columns_limit=50,
        _env_file=None,
    )


def test_ingest_valid_csv(temp_settings):
    """Verify clean ingestion, statistical profiling, and persistence of a valid CSV."""
    csv_data = (
        "region,sales,units,profitable\n"
        "North,150.50,10,true\n"
        "South,200.00,15,true\n"
        "East,80.25,5,false\n"
        "West,,8,true\n"
    ).encode("utf-8")

    result = DatasetService.ingest_csv(
        file_bytes=csv_data,
        filename="sales_q1.csv",
        settings=temp_settings,
    )

    assert result.summary.row_count == 4
    assert result.summary.column_count == 4
    assert result.summary.columns == ["region", "sales", "units", "profitable"]

    # Check numeric stats on 'sales' (has 1 null)
    col_map = {col.name: col for col in result.profile.columns}
    sales_col = col_map["sales"]
    assert sales_col.category == "numeric"
    assert sales_col.null_count == 1
    assert sales_col.null_percentage == 25.0
    assert sales_col.distinct_count == 3
    assert sales_col.stats["min"] == 80.25
    assert sales_col.stats["max"] == 200.0
    assert sales_col.stats["mean"] == round((150.50 + 200.00 + 80.25) / 3, 4)

    # Check categorical stats on 'region'
    region_col = col_map["region"]
    assert region_col.category in ("categorical", "text")
    assert region_col.null_count == 0

    # Retrieve stored profile
    fetched_profile = DatasetService.get_dataset_profile(result.summary.dataset_id, temp_settings)
    assert fetched_profile.dataset_id == result.summary.dataset_id

    # Retrieve stored DataFrame
    df = DatasetService.get_dataframe(result.summary.dataset_id, temp_settings)
    assert len(df) == 4
    assert list(df.columns) == ["region", "sales", "units", "profitable"]


def test_ingest_empty_file_rejected(temp_settings):
    """Verify empty or whitespace-only CSVs are rejected with validation error."""
    with pytest.raises(DatasetValidationError, match="empty"):
        DatasetService.ingest_csv(b"", "empty.csv", temp_settings)

    with pytest.raises(DatasetValidationError, match="empty"):
        DatasetService.ingest_csv(b"   \n  \n", "whitespace.csv", temp_settings)


def test_ingest_non_csv_extension_rejected(temp_settings):
    """Verify non-CSV files are rejected."""
    with pytest.raises(DatasetValidationError, match="Only CSV"):
        DatasetService.ingest_csv(b"a,b,c\n1,2,3", "data.json", temp_settings)


def test_ingest_file_size_limit_enforced(temp_settings):
    """Verify file exceeding max_upload_size_bytes is rejected."""
    small_limit_settings = Settings(
        data_dir=temp_settings.data_dir,
        max_upload_size_bytes=50,  # 50 bytes limit
        _env_file=None,
    )
    oversized = b"column1,column2\n" + b"very_long_data_entry_string," * 5
    with pytest.raises(DatasetValidationError, match="maximum allowed limit"):
        DatasetService.ingest_csv(oversized, "large.csv", small_limit_settings)


def test_ingest_row_limit_enforced(temp_settings):
    """Verify dataset exceeding max_rows_limit is rejected."""
    strict_settings = Settings(
        data_dir=temp_settings.data_dir,
        max_rows_limit=3,
        _env_file=None,
    )
    csv_data = "x,y\n1,2\n3,4\n5,6\n7,8\n".encode("utf-8")
    with pytest.raises(DatasetValidationError, match="exceeds the configured limit"):
        DatasetService.ingest_csv(csv_data, "four_rows.csv", strict_settings)


def test_get_nonexistent_dataset_raises_not_found(temp_settings):
    """Verify querying non-existent dataset ID raises DatasetNotFoundError."""
    with pytest.raises(DatasetNotFoundError):
        DatasetService.get_dataset_profile("non_existent_uuid", temp_settings)

    with pytest.raises(DatasetNotFoundError):
        DatasetService.get_dataframe("non_existent_uuid", temp_settings)


def test_list_datasets(temp_settings):
    """Verify listing multiple ingested datasets."""
    csv_1 = b"id,val\n1,10\n"
    csv_2 = b"name,score\nAlice,95\n"

    r1 = DatasetService.ingest_csv(csv_1, "first.csv", temp_settings)
    r2 = DatasetService.ingest_csv(csv_2, "second.csv", temp_settings)

    datasets = DatasetService.list_datasets(temp_settings)
    assert len(datasets) == 2
    ids = {d.dataset_id for d in datasets}
    assert r1.summary.dataset_id in ids
    assert r2.summary.dataset_id in ids
