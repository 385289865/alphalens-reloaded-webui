"""FastAPI backend service definition."""

import sys
from alphalens import ServiceDef

service = ServiceDef(
    name="backend",
    display_name="FastAPI Backend",
    description="FastAPI backend serving the alphalens analysis API on port 8000",
    command_dev=[
        sys.executable, "-m", "uvicorn",
        "backend.app.main:app",
        "--host", "0.0.0.0", "--port", "8000", "--reload",
    ],
    command_prod=[
        sys.executable, "-m", "uvicorn",
        "backend.app.main:app",
        "--host", "0.0.0.0", "--port", "8000",
        "--workers", "4",
    ],
    health_check="http:http://localhost:8000/api/v1/health",
    depends_on=["redis"],
    order=20,
    port=8000,
)
