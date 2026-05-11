"""Flow builder models — templates, workflow steps, and definitions."""

from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from enum import Enum


class AtomicStepType(str, Enum):
    """All supported atomic step types."""
    # Data preparation
    GET_CLEAN_FACTOR = "get_clean_factor_and_forward_returns"

    # IC computations
    FACTOR_INFORMATION_COEFFICIENT = "factor_information_coefficient"
    MEAN_INFORMATION_COEFFICIENT = "mean_information_coefficient"

    # Returns analysis
    FACTOR_RETURNS = "factor_returns"
    FACTOR_ALPHA_BETA = "factor_alpha_beta"
    MEAN_RETURN_BY_QUANTILE = "mean_return_by_quantile"
    COMPUTE_MEAN_RETURNS_SPREAD = "compute_mean_returns_spread"

    # Turnover / stability
    QUANTILE_TURNOVER = "quantile_turnover"
    FACTOR_RANK_AUTOCORRELATION = "factor_rank_autocorrelation"

    # Event study
    AVERAGE_CUMULATIVE_RETURN = "average_cumulative_return_by_quantile"

    # Charts
    CHART_IC_TIME_SERIES = "chart_ic_time_series"
    CHART_IC_HISTOGRAM = "chart_ic_histogram"
    CHART_IC_QQ = "chart_ic_qq"
    CHART_QUANTILE_RETURNS_BAR = "chart_quantile_returns_bar"
    CHART_CUMULATIVE_RETURNS = "chart_cumulative_returns"
    CHART_MEAN_QUANTILE_SPREAD = "chart_mean_quantile_spread"
    CHART_QUANTILE_TURNOVER = "chart_quantile_turnover"
    CHART_RANK_AUTOCORRELATION = "chart_rank_autocorrelation"


class WorkflowStep(BaseModel):
    """A single step in a workflow instance."""
    step_type: AtomicStepType
    order: int
    depends_on: List[str] = []
    parameters: Dict[str, Any] = {}
    output_key: str


class WorkflowTemplate(BaseModel):
    """Predefined template that frontend can select and configure."""
    template_id: str
    name: str
    description: str
    version: str = "1.0.0"
    steps: List[Dict]
    configurable_params: List[Dict]


class WorkflowDefinition(BaseModel):
    """An instantiated template with concrete parameters."""
    workflow_id: str
    template_id: str
    session_id: str
    parameters: Dict[str, Any]
    steps: List[WorkflowStep]
    status: str = "pending"
    created_at: Optional[str] = None


# --- API schemas ---

class TemplateListResponse(BaseModel):
    template_id: str
    name: str
    description: str
    configurable_params: List[Dict]


class TemplateDetailResponse(BaseModel):
    template_id: str
    name: str
    description: str
    version: str
    steps: List[Dict]
    configurable_params: List[Dict]


class WorkflowCreateRequest(BaseModel):
    template_id: str
    session_id: str
    parameters: Dict[str, Any]


class WorkflowCreateResponse(BaseModel):
    workflow_id: str
    template_id: str
    job_id: str
    step_count: int
    status: str
