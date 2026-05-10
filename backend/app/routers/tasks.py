"""Tasks router - Celery task status and management endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from celery.result import AsyncResult

from backend.app.models.schemas import TaskStatusResponse, TaskSummary
from backend.app.celery_app import celery_app

router = APIRouter()


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get Celery task status with progress information."""
    try:
        async_result = AsyncResult(task_id, app=celery_app)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid task ID: {e}")

    state = async_result.state
    meta = {}
    if async_result.info:
        if isinstance(async_result.info, dict):
            meta = async_result.info

    return TaskStatusResponse(
        task_id=task_id,
        status=state.lower(),
        progress_pct=meta.get("progress_pct"),
        current_stage=meta.get("stage"),
        message=meta.get("message") or meta.get("exc_message", str(async_result.info)),
    )


@router.get("/", response_model=List[TaskSummary])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List recent Celery tasks.

    Note: This uses the Celery result backend which may have limited
    introspection capabilities. For a complete task list, query
    the analysis_runs table via /api/v1/data/sessions.
    """
    # Celery does not natively support listing past tasks from the result backend.
    # This endpoint returns an empty list as a placeholder.
    # For comprehensive task tracking, use the analysis status endpoints.
    return []


@router.post("/{task_id}/revoke", status_code=202)
async def revoke_task(task_id: str):
    """Cancel a running task."""
    try:
        async_result = AsyncResult(task_id, app=celery_app)
        async_result.revoke(terminate=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to revoke task: {e}")

    return {"status": "revoked", "task_id": task_id}
