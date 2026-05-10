"""DataService - DuckDB persistence layer for Alphalens WebUI.

Three-tier storage architecture:
1. Raw Dataset: original CSV files in ./db/raw/{session_id}/
2. User Database: DuckDB file at ./db/alphalens.db
3. Task State: Celery/Redis (primary) + task_progress table (fallback)
"""

import json
import os
import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

import duckdb
import pandas as pd

from backend.app.config import settings


class DataService:
    """Manages DuckDB connection lifecycle and all CRUD operations."""

    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = duckdb.connect(db_path)
        self._init_schema()

    # ============================================================
    # Schema initialization
    # ============================================================

    def _init_schema(self):
        """Create all tables if they don't exist."""
        schema = """
        -- Sessions
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            description VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR DEFAULT 'active',
            row_count_factor INTEGER,
            row_count_prices INTEGER,
            date_range_start DATE,
            date_range_end DATE,
            asset_count INTEGER
        );

        -- Uploaded raw file metadata
        CREATE TABLE IF NOT EXISTS raw_files (
            file_id VARCHAR PRIMARY KEY,
            session_id VARCHAR NOT NULL,
            file_type VARCHAR NOT NULL,
            original_filename VARCHAR NOT NULL,
            storage_path VARCHAR NOT NULL,
            file_size_bytes BIGINT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            row_count INTEGER,
            column_count INTEGER
        );

        -- Analysis run metadata
        CREATE TABLE IF NOT EXISTS analysis_runs (
            analysis_id VARCHAR PRIMARY KEY,
            session_id VARCHAR NOT NULL,
            task_id VARCHAR,
            status VARCHAR DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message VARCHAR
        );

        -- Analysis configuration parameters
        CREATE TABLE IF NOT EXISTS analysis_configs (
            analysis_id VARCHAR PRIMARY KEY,
            periods INTEGER[],
            quantiles INTEGER,
            bins INTEGER,
            filter_zscore FLOAT DEFAULT 20.0,
            max_loss FLOAT DEFAULT 0.35,
            zero_aware BOOLEAN DEFAULT FALSE,
            cumulative_returns BOOLEAN DEFAULT TRUE,
            long_short BOOLEAN DEFAULT TRUE,
            group_neutral BOOLEAN DEFAULT FALSE,
            by_group BOOLEAN DEFAULT FALSE
        );

        -- Factor values (from uploaded factor.csv)
        CREATE TABLE IF NOT EXISTS factor_values (
            session_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            asset VARCHAR NOT NULL,
            factor_value DOUBLE NOT NULL
        );

        -- Price data (from uploaded prices.csv)
        CREATE TABLE IF NOT EXISTS price_data (
            session_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            asset VARCHAR NOT NULL,
            price DOUBLE NOT NULL
        );

        -- Group mappings (optional)
        CREATE TABLE IF NOT EXISTS group_mappings (
            session_id VARCHAR NOT NULL,
            asset VARCHAR NOT NULL,
            group_name VARCHAR NOT NULL
        );

        -- Processed factor_data from get_clean_factor_and_forward_returns
        CREATE TABLE IF NOT EXISTS factor_data_results (
            analysis_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            asset VARCHAR NOT NULL,
            factor_value DOUBLE,
            factor_quantile INTEGER,
            group_name VARCHAR,
            forward_returns JSON
        );

        -- Information Coefficient per date per period
        CREATE TABLE IF NOT EXISTS ic_results (
            analysis_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            period VARCHAR NOT NULL,
            ic_value DOUBLE
        );

        -- Mean return by quantile
        CREATE TABLE IF NOT EXISTS mean_return_by_quantile (
            analysis_id VARCHAR NOT NULL,
            factor_quantile INTEGER NOT NULL,
            group_name VARCHAR,
            period VARCHAR NOT NULL,
            mean_return DOUBLE,
            std_return DOUBLE
        );

        -- Mean return spread (top - bottom quantile)
        CREATE TABLE IF NOT EXISTS mean_return_spread (
            analysis_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            period VARCHAR NOT NULL,
            spread DOUBLE,
            std_error DOUBLE
        );

        -- Factor portfolio returns
        CREATE TABLE IF NOT EXISTS factor_returns_results (
            analysis_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            period VARCHAR NOT NULL,
            return_value DOUBLE
        );

        -- Alpha and Beta from OLS
        CREATE TABLE IF NOT EXISTS alpha_beta_results (
            analysis_id VARCHAR NOT NULL,
            metric VARCHAR NOT NULL,
            period VARCHAR NOT NULL,
            value DOUBLE
        );

        -- Quantile turnover
        CREATE TABLE IF NOT EXISTS quantile_turnover_results (
            analysis_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            period VARCHAR NOT NULL,
            quantile INTEGER NOT NULL,
            turnover DOUBLE
        );

        -- Factor rank autocorrelation
        CREATE TABLE IF NOT EXISTS factor_rank_autocorrelation_results (
            analysis_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            period VARCHAR NOT NULL,
            autocorrelation DOUBLE
        );

        -- Cumulative returns
        CREATE TABLE IF NOT EXISTS cumulative_returns_results (
            analysis_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            period VARCHAR NOT NULL,
            cumulative_return DOUBLE
        );

        -- Average cumulative return by quantile (event study)
        CREATE TABLE IF NOT EXISTS avg_cumulative_return_results (
            analysis_id VARCHAR NOT NULL,
            factor_quantile INTEGER NOT NULL,
            group_name VARCHAR,
            stat_type VARCHAR NOT NULL,
            period_offset INTEGER NOT NULL,
            value DOUBLE
        );

        -- Generated chart metadata
        CREATE TABLE IF NOT EXISTS chart_files (
            chart_id VARCHAR PRIMARY KEY,
            analysis_id VARCHAR NOT NULL,
            chart_type VARCHAR NOT NULL,
            format VARCHAR DEFAULT 'png',
            base64_data VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Persistent task progress (fallback for Redis)
        CREATE TABLE IF NOT EXISTS task_progress (
            task_id VARCHAR PRIMARY KEY,
            analysis_id VARCHAR,
            status VARCHAR,
            current_stage VARCHAR,
            progress_pct INTEGER DEFAULT 0,
            message VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self._conn.execute(schema)

    # ============================================================
    # Connection lifecycle
    # ============================================================

    def _get_raw_data_dir(self) -> str:
        """Get the raw data directory path."""
        return settings.RAW_DATA_DIR

    def close(self):
        """Close the DuckDB connection."""
        if self._conn:
            self._conn.close()

    @property
    def conn(self):
        return self._conn

    # ============================================================
    # Session operations
    # ============================================================

    def create_session(self, name: Optional[str] = None,
                       description: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO sessions (session_id, name, description) VALUES (?, ?, ?)",
            [session_id, name, description]
        )
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        result = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", [session_id]
        ).fetchdf()
        if result.empty:
            return None
        row = result.iloc[0].to_dict()
        row["analysis_count"] = self._conn.execute(
            "SELECT COUNT(*) FROM analysis_runs WHERE session_id = ?", [session_id]
        ).fetchone()[0]
        return row

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = self._conn.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC"
        ).fetchdf()
        result = []
        for _, row in sessions.iterrows():
            s = row.to_dict()
            s["analysis_count"] = self._conn.execute(
                "SELECT COUNT(*) FROM analysis_runs WHERE session_id = ?",
                [s["session_id"]]
            ).fetchone()[0]
            result.append(s)
        return result

    def update_session_stats(self, session_id: str, row_count_factor: int,
                              row_count_prices: int, date_range_start: date,
                              date_range_end: date, asset_count: int):
        self._conn.execute(
            """UPDATE sessions SET
               row_count_factor = ?, row_count_prices = ?,
               date_range_start = ?, date_range_end = ?,
               asset_count = ?
               WHERE session_id = ?""",
            [row_count_factor, row_count_prices,
             date_range_start, date_range_end, asset_count, session_id]
        )

    def delete_session(self, session_id: str):
        """Delete a session and all related data from DuckDB."""
        tables = [
            "factor_values", "price_data", "group_mappings",
            "analysis_runs", "analysis_configs",
            "factor_data_results", "ic_results", "mean_return_by_quantile",
            "mean_return_spread", "factor_returns_results", "alpha_beta_results",
            "quantile_turnover_results", "factor_rank_autocorrelation_results",
            "cumulative_returns_results", "avg_cumulative_return_results",
            "chart_files"
        ]
        for table in tables:
            # Only delete if the column exists (analysis_runs, analysis_configs use analysis_id not session_id)
            if table in ("analysis_runs", "analysis_configs",
                          "factor_data_results", "ic_results",
                          "mean_return_by_quantile", "mean_return_spread",
                          "factor_returns_results", "alpha_beta_results",
                          "quantile_turnover_results",
                          "factor_rank_autocorrelation_results",
                          "cumulative_returns_results",
                          "avg_cumulative_return_results", "chart_files"):
                # These tables reference session via analysis_runs
                self._conn.execute(
                    f"DELETE FROM {table} WHERE analysis_id IN "
                    f"(SELECT analysis_id FROM analysis_runs WHERE session_id = ?)",
                    [session_id]
                )
            else:
                self._conn.execute(
                    f"DELETE FROM {table} WHERE session_id = ?", [session_id]
                )
        self._conn.execute(
            "DELETE FROM sessions WHERE session_id = ?", [session_id]
        )

    # ============================================================
    # Raw file operations
    # ============================================================

    def save_raw_file(self, session_id: str, file_type: str,
                       original_filename: str, storage_path: str,
                       file_size_bytes: int, row_count: int,
                       column_count: int) -> str:
        file_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO raw_files (file_id, session_id, file_type,
               original_filename, storage_path, file_size_bytes,
               row_count, column_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [file_id, session_id, file_type, original_filename,
             storage_path, file_size_bytes, row_count, column_count]
        )
        return file_id

    def get_session_files(self, session_id: str) -> List[Dict[str, Any]]:
        result = self._conn.execute(
            "SELECT * FROM raw_files WHERE session_id = ? ORDER BY uploaded_at",
            [session_id]
        ).fetchdf()
        return result.to_dict("records") if not result.empty else []

    # ============================================================
    # Raw data ingestion
    # ============================================================

    def ingest_factor_csv(self, session_id: str, df: pd.DataFrame) -> int:
        """Ingest factor data from a parsed CSV into DuckDB.

        Expects df with columns: date, asset, factor_value (or similar).
        """
        required = {"date", "asset"}
        if not required.issubset(df.columns.str.lower()):
            raise ValueError(
                f"Factor CSV must contain 'date' and 'asset' columns. Got: {list(df.columns)}"
            )
        # Normalize column names
        df = df.rename(columns=str.lower)
        factor_col = [c for c in df.columns if c not in ("date", "asset")][0]
        df = df.rename(columns={factor_col: "factor_value"})
        df["session_id"] = session_id
        self._conn.execute(
            "INSERT INTO factor_values SELECT session_id, date, asset, factor_value FROM df",
        )
        return len(df)

    def ingest_prices_csv(self, session_id: str, df: pd.DataFrame) -> Tuple[int, int]:
        """Ingest price data from a parsed CSV. Prices are typically wide format
        (date column + asset columns). Melts to long format for storage.

        Returns (row_count, asset_count).
        """
        date_col = df.columns[0]
        melted = df.melt(id_vars=[date_col], var_name="asset", value_name="price")
        melted.columns = ["date", "asset", "price"]
        melted = melted.dropna(subset=["price"])
        melted["session_id"] = session_id
        self._conn.execute(
            "INSERT INTO price_data SELECT session_id, date, asset, price FROM melted",
        )
        asset_count = melted["asset"].nunique()
        return len(melted), asset_count

    def ingest_groups_csv(self, session_id: str, df: pd.DataFrame):
        """Ingest group mapping data."""
        # Expects columns: asset, group_name
        df = df.rename(columns=str.lower)
        df = df.rename(columns={df.columns[1]: "group_name"})
        df["session_id"] = session_id
        self._conn.execute(
            "INSERT INTO group_mappings SELECT session_id, asset, group_name FROM df",
        )

    # ============================================================
    # Load data for alphalens (reconstruct pandas objects)
    # ============================================================

    def get_factor_df(self, session_id: str) -> pd.Series:
        """Reconstruct MultiIndex factor Series for alphalens."""
        result = self._conn.execute(
            "SELECT date, asset, factor_value FROM factor_values WHERE session_id = ?",
            [session_id]
        ).fetchdf()
        if result.empty:
            raise ValueError(f"No factor data found for session {session_id}")
        result = result.set_index(["date", "asset"]).squeeze()
        result.name = "factor"
        return result

    def get_prices_df(self, session_id: str) -> pd.DataFrame:
        """Reconstruct wide-format prices DataFrame for alphalens."""
        result = self._conn.execute(
            "SELECT date, asset, price FROM price_data "
            "WHERE session_id = ? ORDER BY date, asset",
            [session_id]
        ).fetchdf()
        if result.empty:
            raise ValueError(f"No price data found for session {session_id}")
        return result.pivot(index="date", columns="asset", values="price")

    def get_group_mappings(self, session_id: str) -> Optional[pd.Series]:
        """Get group mappings as a Series (asset -> group_name)."""
        result = self._conn.execute(
            "SELECT asset, group_name FROM group_mappings WHERE session_id = ?",
            [session_id]
        ).fetchdf()
        if result.empty:
            return None
        return result.set_index("asset").squeeze()

    # ============================================================
    # Analysis run management
    # ============================================================

    def create_analysis_run(self, session_id: str, task_id: Optional[str] = None) -> str:
        analysis_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO analysis_runs (analysis_id, session_id, task_id) VALUES (?, ?, ?)",
            [analysis_id, session_id, task_id]
        )
        return analysis_id

    def link_task(self, analysis_id: str, task_id: str):
        self._conn.execute(
            "UPDATE analysis_runs SET task_id = ? WHERE analysis_id = ?",
            [task_id, analysis_id]
        )

    def update_analysis_status(self, analysis_id: str, status: str,
                                 error_message: Optional[str] = None):
        if status == "completed":
            self._conn.execute(
                "UPDATE analysis_runs SET status = ?, completed_at = CURRENT_TIMESTAMP "
                "WHERE analysis_id = ?",
                [status, analysis_id]
            )
        elif status == "failed":
            self._conn.execute(
                "UPDATE analysis_runs SET status = ?, completed_at = CURRENT_TIMESTAMP, "
                "error_message = ? WHERE analysis_id = ?",
                [status, error_message, analysis_id]
            )
        else:
            self._conn.execute(
                "UPDATE analysis_runs SET status = ? WHERE analysis_id = ?",
                [status, analysis_id]
            )

    def get_analysis_run(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        result = self._conn.execute(
            "SELECT * FROM analysis_runs WHERE analysis_id = ?", [analysis_id]
        ).fetchdf()
        if result.empty:
            return None
        return result.iloc[0].to_dict()

    def save_analysis_config(self, analysis_id: str, config: Dict[str, Any]):
        periods = config.get("periods", [1, 5, 10])
        self._conn.execute(
            """INSERT INTO analysis_configs (analysis_id, periods, quantiles, bins,
               filter_zscore, max_loss, zero_aware, cumulative_returns,
               long_short, group_neutral, by_group)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [analysis_id, periods, config.get("quantiles"),
             config.get("bins"), config.get("filter_zscore"),
             config.get("max_loss"), config.get("zero_aware"),
             config.get("cumulative_returns"), config.get("long_short"),
             config.get("group_neutral"), config.get("by_group")]
        )

    def get_analysis_config(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        result = self._conn.execute(
            "SELECT * FROM analysis_configs WHERE analysis_id = ?", [analysis_id]
        ).fetchdf()
        if result.empty:
            return None
        row = result.iloc[0].to_dict()
        # Convert periods from list to proper Python list
        periods = row.get("periods")
        row["periods"] = list(periods) if periods is not None else [1, 5, 10]
        return row

    # ============================================================
    # Save computation results
    # ============================================================

    def save_factor_data(self, analysis_id: str, factor_data: pd.DataFrame):
        """Save the main factor_data MultiIndex DataFrame.

        factor_data has MultiIndex (date, asset) and columns including
        forward returns (named by period like '1D', '5D'), 'factor',
        'group', 'factor_quantile'.
        """
        records = []
        period_cols = [c for c in factor_data.columns
                       if c not in ("factor", "group", "factor_quantile")]
        for (dt, asset), row in factor_data.iterrows():
            forward_rets = {p: row[p] for p in period_cols
                           if pd.notna(row[p])}
            records.append({
                "analysis_id": analysis_id,
                "date": dt,
                "asset": asset,
                "factor_value": row.get("factor"),
                "factor_quantile": row.get("factor_quantile"),
                "group_name": row.get("group"),
                "forward_returns": json.dumps(forward_rets),
            })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute(
                "INSERT INTO factor_data_results SELECT * FROM df",
            )

    def save_ic_results(self, analysis_id: str, ic: pd.DataFrame):
        """Save IC results. ic has date index, period columns."""
        records = []
        for dt, row in ic.iterrows():
            for col in ic.columns:
                if pd.notna(row[col]):
                    records.append({
                        "analysis_id": analysis_id,
                        "date": dt,
                        "period": str(col),
                        "ic_value": row[col],
                    })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute("INSERT INTO ic_results SELECT * FROM df")

    def save_mean_return_by_quantile(self, analysis_id: str,
                                      mean_ret: pd.DataFrame,
                                      std_err: Optional[pd.DataFrame] = None):
        """Save mean return by quantile."""
        records = []
        for idx, row in mean_ret.iterrows():
            if mean_ret.index.nlevels > 1:
                q_val, grp = idx
            else:
                q_val, grp = idx, None
            for col in mean_ret.columns:
                std_val = None
                if std_err is not None:
                    try:
                        std_val = std_err.loc[(q_val, grp), col] if grp else std_err.loc[q_val, col]
                    except (KeyError, TypeError):
                        pass
                records.append({
                    "analysis_id": analysis_id,
                    "factor_quantile": int(q_val),
                    "group_name": str(grp) if grp and grp == grp else None,
                    "period": str(col),
                    "mean_return": row[col],
                    "std_return": std_val,
                })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute("INSERT INTO mean_return_by_quantile SELECT * FROM df")

    def save_mean_return_spread(self, analysis_id: str,
                                  spread: pd.DataFrame,
                                  spread_std: Optional[pd.DataFrame] = None):
        records = []
        for dt, row in spread.iterrows():
            for col in spread.columns:
                std_val = None
                if spread_std is not None:
                    try:
                        std_val = spread_std.loc[dt, col]
                    except KeyError:
                        pass
                records.append({
                    "analysis_id": analysis_id,
                    "date": dt,
                    "period": str(col),
                    "spread": row[col],
                    "std_error": std_val,
                })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute("INSERT INTO mean_return_spread SELECT * FROM df")

    def save_factor_returns(self, analysis_id: str, returns: pd.DataFrame):
        records = []
        for dt, row in returns.iterrows():
            for col in returns.columns:
                if pd.notna(row[col]):
                    records.append({
                        "analysis_id": analysis_id,
                        "date": dt,
                        "period": str(col),
                        "return_value": row[col],
                    })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute("INSERT INTO factor_returns_results SELECT * FROM df")

    def save_alpha_beta(self, analysis_id: str, alpha_beta: pd.DataFrame):
        """Save alpha/beta results. alpha_beta has metric index, period columns."""
        records = []
        for metric, row in alpha_beta.iterrows():
            for col in alpha_beta.columns:
                if pd.notna(row[col]):
                    records.append({
                        "analysis_id": analysis_id,
                        "metric": str(metric),
                        "period": str(col),
                        "value": row[col],
                    })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute("INSERT INTO alpha_beta_results SELECT * FROM df")

    def save_quantile_turnover(self, analysis_id: str,
                                turnover_dict: Dict[int, pd.Series]):
        records = []
        for quantile, series in turnover_dict.items():
            for dt, val in series.items():
                if pd.notna(val):
                    records.append({
                        "analysis_id": analysis_id,
                        "date": dt,
                        "period": "1",
                        "quantile": int(quantile),
                        "turnover": val,
                    })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute("INSERT INTO quantile_turnover_results SELECT * FROM df")

    def save_autocorrelation(self, analysis_id: str,
                               autocorr: pd.Series):
        records = []
        for dt, val in autocorr.items():
            if pd.notna(val):
                records.append({
                    "analysis_id": analysis_id,
                    "date": dt,
                    "period": "1",
                    "autocorrelation": val,
                })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute(
                "INSERT INTO factor_rank_autocorrelation_results SELECT * FROM df"
            )

    def save_cumulative_returns(self, analysis_id: str,
                                  cum_ret: pd.Series):
        records = []
        for dt, val in cum_ret.items():
            if pd.notna(val):
                records.append({
                    "analysis_id": analysis_id,
                    "date": dt,
                    "period": "1",
                    "cumulative_return": val,
                })
        if records:
            df = pd.DataFrame(records)
            self._conn.execute("INSERT INTO cumulative_returns_results SELECT * FROM df")

    # ============================================================
    # Chart storage
    # ============================================================

    def save_chart(self, analysis_id: str, chart_type: str, base64_data: str):
        chart_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO chart_files (chart_id, analysis_id, chart_type, base64_data) "
            "VALUES (?, ?, ?, ?)",
            [chart_id, analysis_id, chart_type, base64_data]
        )

    def get_chart(self, analysis_id: str, chart_type: str) -> Optional[str]:
        result = self._conn.execute(
            "SELECT base64_data FROM chart_files "
            "WHERE analysis_id = ? AND chart_type = ? "
            "ORDER BY created_at DESC LIMIT 1",
            [analysis_id, chart_type]
        ).fetchone()
        return result[0] if result else None

    def get_all_charts(self, analysis_id: str) -> Dict[str, str]:
        result = self._conn.execute(
            "SELECT chart_type, base64_data FROM chart_files "
            "WHERE analysis_id = ? ORDER BY chart_type",
            [analysis_id]
        ).fetchdf()
        if result.empty:
            return {}
        return dict(zip(result["chart_type"], result["base64_data"]))

    # ============================================================
    # Task progress (persistent fallback)
    # ============================================================

    def update_task_progress(self, task_id: str, analysis_id: str,
                              status: str, current_stage: str,
                              progress_pct: int, message: Optional[str] = None):
        self._conn.execute(
            """INSERT OR REPLACE INTO task_progress
               (task_id, analysis_id, status, current_stage, progress_pct, message, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            [task_id, analysis_id, status, current_stage, progress_pct, message]
        )

    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        result = self._conn.execute(
            "SELECT * FROM task_progress WHERE task_id = ?", [task_id]
        ).fetchdf()
        if result.empty:
            return None
        return result.iloc[0].to_dict()

    # ============================================================
    # Fetch results for API
    # ============================================================

    def get_ic_results(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT date, period, ic_value FROM ic_results "
            "WHERE analysis_id = ? ORDER BY date, period",
            [analysis_id]
        ).fetchdf()

    def get_returns_by_quantile(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT factor_quantile, group_name, period, mean_return, std_return "
            "FROM mean_return_by_quantile WHERE analysis_id = ? ORDER BY period, factor_quantile",
            [analysis_id]
        ).fetchdf()

    def get_factor_returns(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT date, period, return_value FROM factor_returns_results "
            "WHERE analysis_id = ? ORDER BY date, period",
            [analysis_id]
        ).fetchdf()

    def get_alpha_beta(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT metric, period, value FROM alpha_beta_results "
            "WHERE analysis_id = ? ORDER BY period, metric",
            [analysis_id]
        ).fetchdf()

    def get_turnover_results(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT date, period, quantile, turnover FROM quantile_turnover_results "
            "WHERE analysis_id = ? ORDER BY date, period, quantile",
            [analysis_id]
        ).fetchdf()

    def get_autocorrelation_results(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT date, period, autocorrelation FROM factor_rank_autocorrelation_results "
            "WHERE analysis_id = ? ORDER BY date",
            [analysis_id]
        ).fetchdf()

    def get_cumulative_returns(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT date, period, cumulative_return FROM cumulative_returns_results "
            "WHERE analysis_id = ? ORDER BY date",
            [analysis_id]
        ).fetchdf()

    def get_factor_data(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT date, asset, factor_value, factor_quantile, group_name, forward_returns "
            "FROM factor_data_results WHERE analysis_id = ? ORDER BY date, asset",
            [analysis_id]
        ).fetchdf()

    def get_mean_return_spread(self, analysis_id: str) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT date, period, spread, std_error FROM mean_return_spread "
            "WHERE analysis_id = ? ORDER BY date, period",
            [analysis_id]
        ).fetchdf()
