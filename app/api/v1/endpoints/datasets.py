"""Dataset ingestion and profiling endpoints for API v1."""

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.core.config import Settings, get_settings
from app.schemas.dataset import (
    DatasetProfile,
    DatasetSummary,
    DatasetUploadResponse,
)
from app.services.dataset_service import (
    DatasetNotFoundError,
    DatasetService,
    DatasetValidationError,
)

router = APIRouter()


def _get_active_settings(request: Request) -> Settings:
    """Retrieve active application settings from app state or singleton."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and profile a CSV dataset",
    description="Uploads a CSV file, performs data validation, profiles each column, and stores it.",
)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(..., description="CSV file to upload and profile"),
) -> DatasetUploadResponse:
    """Validate, ingest, and profile an uploaded CSV file."""
    settings = _get_active_settings(request)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    try:
        content = await file.read()
        return DatasetService.ingest_csv(
            file_bytes=content,
            filename=file.filename,
            settings=settings,
        )
    except DatasetValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    finally:
        await file.close()


@router.get(
    "",
    response_model=list[DatasetSummary],
    summary="List all ingested datasets",
    description="Returns metadata summaries for all stored datasets.",
)
def list_datasets(request: Request) -> list[DatasetSummary]:
    """Return all ingested dataset summaries."""
    settings = _get_active_settings(request)
    return DatasetService.list_datasets(settings=settings)


@router.get(
    "/{dataset_id}",
    response_model=DatasetProfile,
    summary="Retrieve dataset profile",
    description="Returns the full EDA statistical profile and preview for a specific dataset ID.",
)
def get_dataset(request: Request, dataset_id: str) -> DatasetProfile:
    """Return full EDA statistical profile and column metrics for a dataset."""
    settings = _get_active_settings(request)
    try:
        return DatasetService.get_dataset_profile(dataset_id=dataset_id, settings=settings)
    except DatasetNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
