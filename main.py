"""InsightIQ entry point and backward-compatible ASGI shim.

Delegates application construction to the modular factory in ``app.main``.
Running ``python -m uvicorn main:app`` imports the shared ``app`` instance here.
"""

from app.main import app, create_app

__all__ = ["app", "create_app"]

