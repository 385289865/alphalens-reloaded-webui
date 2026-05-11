"""Per-job SQLite database for computation results.

Each job gets its own SQLite file: ./db/jobs/{job_id}.db

Results are stored in dynamically-created tables named {task_id}_{result_key}.
Supports DataFrames, dicts, base64 blobs, and scalar values.
"""

import sqlite3
import json
import os
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class JobDB:
    """Writes computation results to a per-job SQLite database."""

    def __init__(self, job_id: str, db_dir: str = "./db/jobs"):
        self.job_id = job_id
        self.db_path = os.path.join(db_dir, f"{job_id}.db")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")

    def store_results(
        self,
        task_id: str,
        step_type: str,
        outputs: Dict[str, Any],
    ) -> List[str]:
        """Store operation outputs and return list of result keys stored."""
        result_keys = []
        for key, value in outputs.items():
            table_name = f"{task_id}_{key}".replace("-", "_")
            self._store_value(table_name, value)
            result_keys.append(key)
        self._conn.commit()
        return result_keys

    def read_result(self, task_id: str, result_key: str) -> Any:
        """Read a stored result back (returns DataFrame for tabular data)."""
        table_name = f"{task_id}_{result_key}".replace("-", "_")
        try:
            return pd.read_sql(f"SELECT * FROM [{table_name}]", self._conn)
        except Exception:
            try:
                cursor = self._conn.execute(
                    f"SELECT data FROM [{table_name}] ORDER BY created_at DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
            except Exception:
                return None
        return None

    def list_tables(self) -> List[str]:
        cursor = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return [row[0] for row in cursor.fetchall()]

    def _store_value(self, table_name: str, value: Any):
        if isinstance(value, pd.DataFrame):
            self._store_dataframe(table_name, value)
        elif isinstance(value, pd.Series):
            self._store_dataframe(table_name, value.to_frame("value"))
        elif isinstance(value, dict):
            self._store_json(table_name, value)
        elif isinstance(value, str) and value.startswith("data:image"):
            self._store_blob(table_name, value)
        else:
            self._store_json(table_name, {"value": value})

    def _store_dataframe(self, table_name: str, df: pd.DataFrame):
        df.to_sql(table_name, self._conn, if_exists="replace", index=True)
        meta_table = f"{table_name}__meta"
        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS [{meta_table}] ("
            "created_at TEXT, row_count INTEGER, columns TEXT)"
        )
        self._conn.execute(
            f"INSERT INTO [{meta_table}] (created_at, row_count, columns) VALUES (?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), len(df), json.dumps(list(df.columns))),
        )

    def _store_json(self, table_name: str, data: dict):
        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS [{table_name}] ("
            "created_at TEXT, data TEXT)"
        )
        self._conn.execute(
            f"INSERT INTO [{table_name}] (created_at, data) VALUES (?, ?)",
            (datetime.now(timezone.utc).isoformat(), json.dumps(data, default=str)),
        )

    def _store_blob(self, table_name: str, b64_data: str):
        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS [{table_name}] ("
            "created_at TEXT, data TEXT, format TEXT)"
        )
        self._conn.execute(
            f"INSERT INTO [{table_name}] (created_at, data, format) VALUES (?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), b64_data, "png"),
        )

    def close(self):
        self._conn.close()
