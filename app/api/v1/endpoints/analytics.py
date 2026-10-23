"""Analytics endpoints for correlations, multi-dimensional aggregations, and anomaly detection."""

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.config import Settings, get_settings
from app.schemas.analytics import (
    AggregationRequest,
    AggregationResponse,
    AnomalyDetectionResponse,
    AnomalyMethod,
    CorrelationMethod,
    CorrelationResponse,
)
from app.services.analytics_service import AnalyticsError, AnalyticsService
from app.services.dataset_service import DatasetNotFoundError

router = APIRouter()


def _get_active_settings(request: Request) -> Settings:
    """Retrieve active application settings from app state or singleton."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get(
    "/correlations/{dataset_id}",
    response_model=CorrelationResponse,
    summary="Compute feature correlation matrix",
    description="Calculates pairwise correlation coefficients (Pearson or Spearman) and ranks strongest associations.",
)
def get_correlations(
    request: Request,
    dataset_id: str,
    method: CorrelationMethod = Query(
        default="pearson",
        description="Correlation algorithm to apply ('pearson' or 'spearman')",
    ),
) -> CorrelationResponse:
    """Return correlation matrix and ranked pairs for dataset numeric columns."""
    settings = _get_active_settings(request)
    try:
        return AnalyticsService.compute_correlation(
            dataset_id=dataset_id,
            settings=settings,
            method=method,
        )
    except DatasetNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except AnalyticsError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.post(
    "/aggregate/{dataset_id}",
    response_model=AggregationResponse,
    summary="Execute grouped metrics aggregation",
    description="Groups dataset by categorical attributes and computes summary metrics (sum, mean, median, min, max, count).",
)
def compute_aggregation(
    request: Request,
    dataset_id: str,
    body: AggregationRequest,
) -> AggregationResponse:
    """Group dataset and calculate aggregated metrics."""
    settings = _get_active_settings(request)
    try:
        return AnalyticsService.compute_aggregations(
            dataset_id=dataset_id,
            request=body,
            settings=settings,
        )
    except DatasetNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except AnalyticsError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get(
    "/outliers/{dataset_id}",
    response_model=AnomalyDetectionResponse,
    summary="Detect statistical outliers and anomalies",
    description="Identifies statistical anomalies in a numeric column using Interquartile Range (IQR) or Z-score thresholds.",
)
def detect_outliers(
    request: Request,
    dataset_id: str,
    column: str = Query(..., description="Numeric column to analyze for anomalies"),
    method: AnomalyMethod = Query(
        default="iqr",
        description="Anomaly detection algorithm ('iqr' or 'zscore')",
    ),
    threshold: float = Query(
        default=1.5,
        ge=0.1,
        le=10.0,
        description="Sensitivity multiplier (e.g. 1.5 for standard IQR, 3.0 for standard Z-score)",
    ),
) -> AnomalyDetectionResponse:
    """Identify outliers in a specific dataset column."""
    settings = _get_active_settings(request)
    try:
        return AnalyticsService.detect_outliers(
            dataset_id=dataset_id,
            column=column,
            settings=settings,
            method=method,
            threshold=threshold,
        )
    except DatasetNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except AnalyticsError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
