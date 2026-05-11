"""Serial executor: runs atomic steps one-by-one with dependency resolution.

Design:
- No parallelism — each step fully completes before the next starts.
- Results cached in-memory (Dict[str, Any] keyed by output_key) during execution.
- State persisted to metadata.db after each step for crash recovery.
- On failure: remaining tasks marked 'skipped', job marked 'failed'.
"""

import uuid
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.app.perfact.models import (
    Job, AtomicTask, TaskStatus, JobStatus,
)
from backend.app.perfact.operations import OPERATION_REGISTRY
from backend.app.perfact.metadata_db import MetadataDB
from backend.app.perfact.job_db import JobDB
from backend.app.flow_builder.models import WorkflowDefinition
from backend.app.services.data_service import DataService


class SerialExecutor:
    """Executes a workflow's steps serially."""

    def __init__(
        self,
        metadata_db: MetadataDB,
        data_service: DataService,
        jobs_db_dir: str = "./db/jobs",
    ):
        self.metadata_db = metadata_db
        self.data_service = data_service
        self.jobs_db_dir = jobs_db_dir

    def run_job(self, workflow: WorkflowDefinition, session_id: str) -> Job:
        """Execute the full workflow serially. Returns Job with all task states."""
        job = self._create_job(workflow, session_id)
        self.metadata_db.insert_job(job)

        job_db = JobDB(job.job_id, self.jobs_db_dir)
        results_cache: Dict[str, Any] = {}

        try:
            for idx, step in enumerate(workflow.steps):
                task = job.tasks[idx]

                # Mark running
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now(timezone.utc)
                job.status = JobStatus.RUNNING
                job.current_step_index = idx
                self.metadata_db.update_task(task)
                self.metadata_db.update_job(job)

                try:
                    # Resolve inputs from cache
                    inputs = {
                        dep: results_cache[dep]
                        for dep in step.depends_on
                    }

                    # Instantiate and execute operation
                    op_class = OPERATION_REGISTRY[step.step_type.value]
                    op = op_class(data_service=self.data_service)

                    # Inject session_id for operations that need data loading
                    step_params = dict(step.parameters)
                    if "session_id" not in step_params:
                        step_params["session_id"] = session_id

                    outputs = op.execute(inputs, step_params)

                    # Persist outputs to per-job DB
                    result_keys = job_db.store_results(
                        task.task_id,
                        step.step_type.value,
                        outputs,
                    )

                    # Store each output key in the cache
                    for output_key, output_value in outputs.items():
                        results_cache[output_key] = output_value

                    # Mark completed
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now(timezone.utc)
                    task.result_keys = result_keys
                    job.completed_steps += 1
                    self.metadata_db.update_task(task)
                    self.metadata_db.update_job(job)

                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now(timezone.utc)
                    task.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                    job.error_message = task.error_message
                    self.metadata_db.update_task(task)

                    # Mark remaining tasks as skipped
                    for remaining_task in job.tasks[idx + 1:]:
                        remaining_task.status = TaskStatus.SKIPPED
                        self.metadata_db.update_task(remaining_task)

                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.now(timezone.utc)
                    self.metadata_db.update_job(job)
                    return job

            # All steps completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            self.metadata_db.update_job(job)

        finally:
            job_db.close()

        return job

    def _create_job(self, workflow: WorkflowDefinition, session_id: str) -> Job:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        tasks = []
        for i, step in enumerate(workflow.steps):
            tasks.append(AtomicTask(
                task_id=str(uuid.uuid4()),
                job_id=job_id,
                step_type=step.step_type.value,
                order=i,
                status=TaskStatus.PENDING,
            ))
        return Job(
            job_id=job_id,
            workflow_id=workflow.workflow_id,
            session_id=session_id,
            template_id=workflow.template_id,
            parameters=workflow.parameters,
            total_steps=len(tasks),
            tasks=tasks,
            created_at=now,
        )
