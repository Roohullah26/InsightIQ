"""TruthLens — Evidence-Based Intelligence endpoints for API v1."""

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.schemas.truthlens import TruthLensReportResponse, TruthLensScenarioMeta
from app.services.dataset_service import DatasetNotFoundError
from app.services.truthlens_service import TruthLensService

router = APIRouter()


def _get_active_settings(request: Request) -> Settings:
    """Retrieve active application settings from app state or singleton."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get(
    "/scenarios",
    response_model=list[TruthLensScenarioMeta],
    summary="List TruthLens demonstration scenarios",
    description="Returns metadata for the three mandatory TruthLens evidence-based demonstration scenarios (Scenarios A, B, and C).",
)
def list_truthlens_scenarios() -> list[TruthLensScenarioMeta]:
    """List built-in TruthLens benchmark scenarios."""
    return TruthLensService.list_scenarios()


@router.get(
    "/scenarios/{scenario_key}/report",
    response_model=TruthLensReportResponse,
    summary="Evaluate a TruthLens benchmark scenario in-place (context-preserving)",
    description=(
        "Evaluates the requested TruthLens benchmark scenario (scenario_a, scenario_b, or scenario_c) "
        "in memory and returns its complete 5-layer TruthLens report without overwriting the active workspace dataset."
    ),
)
def preview_scenario_report(scenario_key: str) -> TruthLensReportResponse:
    """Evaluate a built-in TruthLens scenario without mutating active workspace datasets."""
    try:
        return TruthLensService.generate_scenario_report(scenario_key=scenario_key)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.post(
    "/scenarios/{scenario_key}",
    response_model=TruthLensReportResponse,
    summary="Load and analyze a TruthLens demonstration scenario",
    description="Ingests the requested TruthLens benchmark scenario (scenario_a, scenario_b, or scenario_c) as an active dataset and returns its complete 5-layer TruthLens report.",
)
def load_and_analyze_scenario(request: Request, scenario_key: str) -> TruthLensReportResponse:
    """Ingest a benchmark scenario and execute TruthLens analysis."""
    settings = _get_active_settings(request)
    try:
        dataset_id = TruthLensService.load_scenario_dataset(scenario_key=scenario_key, settings=settings)
        return TruthLensService.analyze_dataset(dataset_id=dataset_id, settings=settings)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get(
    "/{dataset_id}",
    response_model=TruthLensReportResponse,
    summary="Run TruthLens Evidence-Based Intelligence analysis",
    description=(
        "Executes the 5-layer TruthLens engine on a dataset to identify KPI contradictions, "
        "hidden segment declines, sampling/response bias, misleading averages, incomplete comparisons, "
        "correlation-vs-causation risks, and statistical anomalies."
    ),
)
def get_truthlens_report(request: Request, dataset_id: str) -> TruthLensReportResponse:
    """Run TruthLens analysis on an uploaded dataset."""
    settings = _get_active_settings(request)
    try:
        return TruthLensService.analyze_dataset(dataset_id=dataset_id, settings=settings)
    except DatasetNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err

