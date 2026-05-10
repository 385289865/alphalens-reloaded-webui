from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from backend.app.models.enums import FileType, AnalysisStatus, TaskState, SessionStatus


# ============================================================
# Upload endpoints
# ============================================================

class UploadResponse(BaseModel):
    session_id: str
    file_id: str
    file_type: str
    rows_ingested: int
    columns: List[str]


class UploadFileInfo(BaseModel):
    file_id: str
    file_type: str
    original_filename: str
    file_size_bytes: int
    row_count: int
    uploaded_at: datetime


class SessionFilesResponse(BaseModel):
    session_id: str
    files: List[UploadFileInfo]


# ============================================================
# Data endpoints
# ============================================================

class SessionSummary(BaseModel):
    session_id: str
    name: Optional[str] = None
    created_at: datetime
    status: str
    asset_count: int
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    analysis_count: int = 0


class SessionDetail(BaseModel):
    session_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    status: str
    files: List[UploadFileInfo] = []
    analysis_runs: List[str] = []
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    asset_count: int = 0


class PreviewResponse(BaseModel):
    columns: List[str]
    dtypes: Dict[str, str]
    rows: List[Dict[str, Any]]
    total_rows_preview: int = 10


class PaginatedData(BaseModel):
    session_id: str
    data: List[Dict[str, Any]]
    page: int
    page_size: int
    total_rows: int


# ============================================================
# Analysis configuration
# ============================================================

class AnalysisConfig(BaseModel):
    """Configuration for an analysis run. Mirrors alphalens parameters."""
    periods: List[int] = Field(default=[1, 5, 10], description="Forward return periods")
    quantiles: int = Field(default=5, ge=2, le=100)
    bins: Optional[int] = None
    filter_zscore: float = Field(default=20.0, ge=0.0)
    max_loss: float = Field(default=0.35, ge=0.0, le=1.0)
    zero_aware: bool = False
    cumulative_returns: bool = True
    long_short: bool = True
    group_neutral: bool = False
    by_group: bool = False
    groupby_column: Optional[str] = None


class AnalysisRunRequest(BaseModel):
    session_id: str
    config: AnalysisConfig


class AnalysisRunResponse(BaseModel):
    analysis_id: str
    task_id: str
    status: str = "pending"


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    task_id: str
    status: str
    current_stage: Optional[str] = None
    progress_pct: int = 0
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ChartResponse(BaseModel):
    chart_type: str
    image: str  # data:image/png;base64,...
    format: str = "png"


class AnalysisResultsResponse(BaseModel):
    analysis_id: str
    status: str
    config: Optional[Dict[str, Any]] = None
    ic: Optional[Dict[str, Any]] = None
    returns: Optional[Dict[str, Any]] = None
    alpha_beta: Optional[Dict[str, Any]] = None
    turnover: Optional[Dict[str, Any]] = None
    summary_tables: Optional[Dict[str, Any]] = None
    charts: Optional[Dict[str, str]] = None


# ============================================================
# Task endpoints
# ============================================================

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress_pct: Optional[int] = None
    current_stage: Optional[str] = None
    message: Optional[str] = None


class TaskSummary(BaseModel):
    task_id: str
    analysis_id: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


# ============================================================
# Health
# ============================================================

class HealthResponse(BaseModel):
    status: str
    version: str
