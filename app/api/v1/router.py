"""InsightIQ API v1 aggregated router."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    analytics,
    datasets,
    health,
    insights,
    query,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(query.router, prefix="/query", tags=["query"])




