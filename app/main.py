"""InsightIQ application factory and primary ASGI entry point.

Provides ``create_app()`` to construct an isolated, fully configured
FastAPI application with lifespan lifecycle management, middleware,
and routing. Exposes a default module-level ``app`` instance for ASGI
servers (e.g., uvicorn app.main:app).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""
    # Startup tasks (state initialization, DB connections, caches)
    yield
    # Shutdown tasks (releasing resources, closing pools)


def create_app(custom_settings: Settings | None = None) -> FastAPI:
    """Construct and configure a FastAPI instance for InsightIQ.

    Args:
        custom_settings: Optional Settings override, useful for isolated testing.

    Returns:
        A configured FastAPI application instance.
    """
    cfg = custom_settings or get_settings()

    application = FastAPI(
        title=cfg.app_name,
        debug=cfg.debug,
        lifespan=lifespan,
    )

    # Cross-Origin Resource Sharing (CORS) middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Core baseline routes (preserved for backward compatibility)
    @application.get("/", tags=["system"])
    def home() -> dict[str, str]:
        return {
            "message": "Welcome to InsightIQ!",
            "status": "running",
        }

    @application.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    return application


# Default module-level instance for ASGI servers
app = create_app()
