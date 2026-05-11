"""Perfact job and task lifecycle models."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AtomicTask(BaseModel):
    """One atomic operation within a job."""
    task_id: str
    job_id: str
    step_type: str
    order: int
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_summary: Optional[Dict[str, Any]] = None
    result_keys: List[str] = []


class Job(BaseModel):
    """A job = one workflow execution lifecycle."""
    job_id: str
    workflow_id: str
    session_id: str
    template_id: str
    status: JobStatus = JobStatus.PENDING
    parameters: Dict[str, Any] = {}
    total_steps: int = 0
    completed_steps: int = 0
    current_step_index: int = -1
    tasks: List[AtomicTask] = []
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
