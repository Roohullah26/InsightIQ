"""Natural language dataset querying endpoints for API v1."""

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.schemas.query import (
    NaturalLanguageQueryRequest,
    NaturalLanguageQueryResponse,
    QuerySuggestionsResponse,
)
from app.services.dataset_service import DatasetNotFoundError
from app.services.query_service import QueryInterpretationError, QueryService

router = APIRouter()


def _get_active_settings(request: Request) -> Settings:
    """Retrieve active application settings from app state or singleton."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get(
    "/{dataset_id}/suggestions",
    response_model=QuerySuggestionsResponse,
    summary="Dynamic quick-metric prompt chips for a dataset",
)
def get_suggestions(request: Request, dataset_id: str) -> QuerySuggestionsResponse:
    """Return schema-driven quick metric chips (identifier columns excluded)."""
    settings = _get_active_settings(request)
    try:
        return QueryService.build_quick_metric_suggestions(dataset_id=dataset_id, settings=settings)
    except DatasetNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post(
    "/{dataset_id}",
    response_model=NaturalLanguageQueryResponse,
    summary="Ask a question about a dataset in natural language",
    description="Interprets plain English inquiries (aggregations, rankings, filters, correlations, outliers) and returns direct answers backed by data.",
)
def ask_question(
    request: Request,
    dataset_id: str,
    body: NaturalLanguageQueryRequest,
) -> NaturalLanguageQueryResponse:
    """Execute natural language analytical query against a dataset."""
    settings = _get_active_settings(request)
    try:
        return QueryService.execute_query(
            dataset_id=dataset_id,
            query=body.query,
            settings=settings,
        )
    except DatasetNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except (QueryInterpretationError, ValueError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
