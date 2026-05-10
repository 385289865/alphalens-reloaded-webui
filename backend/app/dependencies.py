"""FastAPI dependency injection for Alphalens WebUI."""

from functools import lru_cache
from fastapi import Request

from backend.app.services.data_service import DataService


@lru_cache
def _get_data_service_instance() -> DataService:
    """Create or return the singleton DataService instance."""
    from backend.app.config import settings
    return DataService(settings.DB_PATH)


def get_data_service(request: Request = None) -> DataService:
    """FastAPI dependency that provides a DataService instance.

    Uses the app's lifespan-managed instance when available,
    falls back to a module-level singleton.
    """
    if request is not None:
        app = request.app
        if hasattr(app.state, "data_service") and app.state.data_service is not None:
            return app.state.data_service
    return _get_data_service_instance()
