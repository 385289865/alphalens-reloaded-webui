"""FastAPI application factory for Alphalens WebUI."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.services.data_service import DataService
from backend.app.routers import upload, data, analysis, tasks
from backend.app.flow_builder.router import router as flow_builder_router
from backend.app.perfact.router import router as perfact_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Startup: create data directories and initialize DuckDB
    os.makedirs(os.path.dirname(settings.DB_PATH) or ".", exist_ok=True)
    os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
    if settings.CHART_OUTPUT_DIR:
        os.makedirs(settings.CHART_OUTPUT_DIR, exist_ok=True)

    app.state.data_service = DataService(settings.DB_PATH)
    yield
    # Shutdown: close DuckDB connection
    if hasattr(app.state, "data_service") and app.state.data_service:
        app.state.data_service.close()
        app.state.data_service = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Web UI for alphalens-reloaded factor analysis",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
    app.include_router(data.router, prefix="/api/v1/data", tags=["Data"])
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
    app.include_router(flow_builder_router)
    app.include_router(perfact_router)

    @app.get("/api/v1/health", tags=["Health"])
    async def health():
        """Health check endpoint."""
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "db_path": settings.DB_PATH,
        }

    return app


app = create_app()
