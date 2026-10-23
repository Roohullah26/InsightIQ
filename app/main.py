"""InsightIQ application factory and primary ASGI entry point.

Provides ``create_app()`` to construct an isolated, fully configured
FastAPI application with lifespan lifecycle management, middleware,
and routing. Exposes a default module-level ``app`` instance for ASGI
servers (e.g., uvicorn app.main:app).
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings

_STATIC_DIR = Path(__file__).resolve().parent / "static"



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""
    app.state.start_time = time.time()
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
    application.state.settings = cfg
    application.state.start_time = time.time()


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

    # Register API v1 aggregated router
    application.include_router(api_router, prefix=cfg.api_v1_prefix)

    # Mount static assets and serve interactive web dashboard
    if _STATIC_DIR.exists():
        application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

        @application.get("/dashboard", response_class=HTMLResponse, tags=["ui"], include_in_schema=False)
        def dashboard() -> FileResponse:
            index_path = _STATIC_DIR / "index.html"
            return FileResponse(index_path)

    return application




# Default module-level instance for ASGI servers
app = create_app()
