"""FastAPI router for perfact job management endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional

from backend.app.perfact.metadata_db import MetadataDB
from backend.app.perfact.job_db import JobDB
from backend.app.config import settings

router = APIRouter(prefix="/api/v1/perfact", tags=["perfact"])


def _get_metadata_db() -> MetadataDB:
    """Dependency: create MetadataDB instance."""
    return MetadataDB(settings.METADATA_DB_PATH)


def _get_metadata_db_replica(request: Request = None) -> MetadataDB:
    """LiteFS-aware: reads from replica for GET requests, primary otherwise."""
    is_read = request and request.method in ("GET", "OPTIONS", "HEAD")
    if is_read and settings.METADATA_REPLICA_DB_PATH:
        repl_path = settings.METADATA_REPLICA_DB_PATH
        return MetadataDB(repl_path, read_only=True)
    return MetadataDB(settings.METADATA_DB_PATH)


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Get job with all tasks."""
    meta = _get_metadata_db_replica()
    try:
        job = meta.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        tasks = meta.get_job_tasks(job_id)
        return {"job": job, "tasks": tasks}
    finally:
        meta.close()


@router.get("/jobs/{job_id}/tasks")
def get_job_tasks(job_id: str):
    """Get tasks for a job."""
    meta = _get_metadata_db_replica()
    try:
        tasks = meta.get_job_tasks(job_id)
        if not tasks:
            # Check if job exists at all
            job = meta.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
        return {"job_id": job_id, "tasks": tasks}
    finally:
        meta.close()


@router.get("/jobs/{job_id}/results/{task_id}")
def get_task_results(job_id: str, task_id: str, result_key: Optional[str] = None):
    """Get stored results for a specific task from the per-job DB.

    If result_key is provided, returns only that result.
    Otherwise returns all result tables for the task.
    """
    job_db = JobDB(job_id, settings.JOBS_DB_DIR)
    try:
        tables = job_db.list_tables()
        task_tables = [t for t in tables if t.startswith(task_id)]

        if result_key:
            data = job_db.read_result(task_id, result_key)
            if data is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Result '{result_key}' not found for task {task_id}",
                )
            return {"job_id": job_id, "task_id": task_id, "result_key": result_key, "data": data}

        results = {}
        for table in task_tables:
            meta_suffix = "__meta"
            if table.endswith(meta_suffix):
                continue
            # Parse result_key from table name: {task_id}_{result_key}
            prefix = f"{task_id}_"
            if table.startswith(prefix):
                key = table[len(prefix):]
                data = job_db.read_result(task_id, key)
                results[key] = data

        return {"job_id": job_id, "task_id": task_id, "results": results}
    finally:
        job_db.close()


@router.get("/jobs")
def list_jobs(session_id: Optional[str] = None, limit: int = 50, offset: int = 0):
    """List jobs, optionally filtered by session_id."""
    meta = _get_metadata_db_replica()
    try:
        if session_id:
            jobs = meta.get_jobs_by_session(session_id)
        else:
            jobs = meta.list_jobs(limit=limit, offset=offset)
        return {"jobs": jobs, "total": len(jobs)}
    finally:
        meta.close()


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str):
    """Reset a failed job status to allow re-execution.

    This just resets the metadata — re-execution is triggered via a new
    POST to flow-builder/workflows or manually.
    """
    meta = MetadataDB(settings.METADATA_DB_PATH)
    job = meta.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") not in ("failed",):
        raise HTTPException(status_code=400, detail=f"Cannot retry job with status '{job['status']}'")

    # Reset job metadata
    from backend.app.perfact.models import Job as JobModel, JobStatus, AtomicTask, TaskStatus
    from datetime import datetime

    tasks_data = meta.get_job_tasks(job_id)
    tasks = [
        AtomicTask(
            task_id=t["task_id"],
            job_id=t["job_id"],
            step_type=t["step_type"],
            order=t["order_num"],
            status=TaskStatus.PENDING,
        )
        for t in tasks_data
    ]
    reset_job = JobModel(
        job_id=job_id,
        workflow_id=job["workflow_id"],
        session_id=job["session_id"],
        template_id=job["template_id"],
        status=JobStatus.PENDING,
        parameters=job.get("parameters", {}),
        total_steps=job["total_steps"],
        tasks=tasks,
        created_at=datetime.utcnow(),
    )

    meta.update_task.__func__(meta, tasks[0])  # force schema update
    meta.update_job(reset_job)

    return {"status": "pending", "job_id": job_id, "message": "Job reset for retry"}
