"""SQLite-based metadata database for job/task lifecycle.

Schema:
  - jobs: job_id, workflow_id, session_id, template_id, status, parameters (JSON),
          total_steps, completed_steps, current_step_index, timestamps, error_message
  - tasks: task_id, job_id, step_type, order_num, status, timestamps, error_message, result_keys (JSON)
  - sessions: mirrored from DuckDB for backward compat during migration
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from backend.app.perfact.models import Job, AtomicTask, TaskStatus, JobStatus


class MetadataDB:
    """Manages the metadata.db SQLite database for job/task lifecycle."""

    def __init__(self, db_path: str = "./db/metadata.db", read_only: bool = False):
        self.db_path = os.path.abspath(db_path)
        self.read_only = read_only
        if not read_only:
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if self.read_only:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        else:
            conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                parameters TEXT DEFAULT '{}',
                total_steps INTEGER NOT NULL DEFAULT 0,
                completed_steps INTEGER NOT NULL DEFAULT 0,
                current_step_index INTEGER NOT NULL DEFAULT -1,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                step_type TEXT NOT NULL,
                order_num INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                result_keys TEXT DEFAULT '[]',
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_job_id ON tasks(job_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_session_id ON jobs(session_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'active'
            );
        """)
        conn.commit()
        conn.close()

    # --- Job CRUD ---

    def insert_job(self, job: Job):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO jobs (job_id, workflow_id, session_id, template_id,
               status, parameters, total_steps, completed_steps,
               current_step_index, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job.job_id, job.workflow_id, job.session_id, job.template_id,
             job.status.value, json.dumps(job.parameters),
             job.total_steps, job.completed_steps, job.current_step_index,
             job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat()),
        )
        for task in job.tasks:
            conn.execute(
                """INSERT INTO tasks (task_id, job_id, step_type, order_num, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (task.task_id, task.job_id, task.step_type,
                 task.order, task.status.value),
            )
        conn.commit()
        conn.close()

    def update_job(self, job: Job):
        conn = self._get_conn()
        conn.execute(
            """UPDATE jobs SET status=?, completed_steps=?,
               current_step_index=?, started_at=?, completed_at=?,
               error_message=?
               WHERE job_id=?""",
            (job.status.value, job.completed_steps, job.current_step_index,
             job.started_at.isoformat() if job.started_at else None,
             job.completed_at.isoformat() if job.completed_at else None,
             job.error_message, job.job_id),
        )
        conn.commit()
        conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        conn.close()
        if row:
            result = dict(row)
            if isinstance(result.get("parameters"), str):
                result["parameters"] = json.loads(result["parameters"])
            return result
        return None

    def get_jobs_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_jobs_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def list_jobs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- Task CRUD ---

    def update_task(self, task: AtomicTask):
        conn = self._get_conn()
        conn.execute(
            """UPDATE tasks SET status=?, started_at=?, completed_at=?,
               error_message=?, result_keys=?
               WHERE task_id=?""",
            (task.status.value,
             task.started_at.isoformat() if task.started_at else None,
             task.completed_at.isoformat() if task.completed_at else None,
             task.error_message, json.dumps(task.result_keys),
             task.task_id),
        )
        conn.commit()
        conn.close()

    def get_job_tasks(self, job_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM tasks WHERE job_id = ? ORDER BY order_num",
            (job_id,),
        ).fetchall()
        conn.close()
        tasks = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("result_keys"), str):
                d["result_keys"] = json.loads(d["result_keys"])
            tasks.append(d)
        return tasks

    # --- Session tracking (migration support) ---

    def insert_session(self, session_id: str, name: Optional[str] = None,
                       description: Optional[str] = None):
        conn = self._get_conn()
        conn.execute(
            """INSERT OR IGNORE INTO sessions (session_id, name, description, created_at, status)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, name, description, datetime.now(timezone.utc).isoformat(), "active"),
        )
        conn.commit()
        conn.close()

    def close(self):
        pass
