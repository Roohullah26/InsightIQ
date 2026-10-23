"""Executive insights and automated business intelligence endpoints for API v1."""

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.schemas.insights import DatasetInsightsResponse
from app.services.dataset_service import DatasetNotFoundError
from app.services.insights_service import InsightsService

router = APIRouter()


def _get_active_settings(request: Request) -> Settings:
    """Retrieve active application settings from app state or singleton."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get(
    "/{dataset_id}",
    response_model=DatasetInsightsResponse,
    summary="Generate AI-powered executive insights",
    description="Synthesizes automated executive briefing, data quality scoring, driver correlations, and anomaly alerts.",
)
def get_dataset_insights(request: Request, dataset_id: str) -> DatasetInsightsResponse:
    """Generate comprehensive business intelligence insights for a dataset."""
    settings = _get_active_settings(request)
    try:
        return InsightsService.generate_insights(dataset_id=dataset_id, settings=settings)
    except DatasetNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
