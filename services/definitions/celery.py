"""Celery worker service definition."""

import sys
from services import ServiceDef

service = ServiceDef(
    name="celery",
    display_name="Celery Worker",
    description="Celery worker for async analysis task execution",
    command_dev=[
        sys.executable, "-m", "celery",
        "-A", "backend.app.celery_app", "worker",
        "--loglevel=info", "--concurrency=2",
    ],
    command_prod=[
        sys.executable, "-m", "celery",
        "-A", "backend.app.celery_app", "worker",
        "--loglevel=info", "--concurrency=4",
    ],
    depends_on=["redis", "backend"],
    order=30,
)
