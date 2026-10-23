"""Health check and telemetry endpoints for API v1."""

import time
from fastapi import APIRouter, Request

from app import __version__
from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health and diagnostics",
    description="Returns service health status, application version, environment, and uptime.",
)
def get_health(request: Request) -> HealthResponse:
    """Return health metrics, deployment environment, and service uptime."""
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    start_time = getattr(request.app.state, "start_time", time.time())

    uptime = max(0.0, time.time() - start_time)

    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        environment=settings.environment,
        version=__version__,
        uptime_seconds=round(uptime, 2),
    )
