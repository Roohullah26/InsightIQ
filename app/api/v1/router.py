"""InsightIQ API v1 aggregated router."""

from fastapi import APIRouter
from app.api.v1.endpoints import analytics, datasets, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


