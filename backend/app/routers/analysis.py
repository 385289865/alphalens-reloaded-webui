"""Analysis router - trigger analysis and fetch results."""

import numpy as np
from typing import Dict, Any, Optional, List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from celery.result import AsyncResult

from backend.app.models.schemas import (
    AnalysisConfig, AnalysisRunRequest, AnalysisRunResponse,
    AnalysisStatusResponse, AnalysisResultsResponse, ChartResponse,
)
from backend.app.services.data_service import DataService
from backend.app.services.chart_service import ChartService
from backend.app.dependencies import get_data_service
from backend.app.celery_app import celery_app
from backend.app.config import settings

router = APIRouter()


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert DataFrame to records list, replacing NaN with None for JSON safety."""
    if df.empty:
        return []
    records = df.to_dict("records")
    for record in records:
        for k, v in record.items():
            if isinstance(v, float) and (v != v or v == float("inf") or v == -float("inf")):
                record[k] = None
            elif isinstance(v, (np.integer,)):
                record[k] = int(v)
            elif isinstance(v, (np.floating,)):
                record[k] = float(v) if not (v != v) else None
    return records


def _sanitize_config(config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert numpy types to native Python types in config dict."""
    if config is None:
        return None
    clean = {}
    for k, v in config.items():
        if isinstance(v, dict):
            clean[k] = _sanitize_config(v)
        elif isinstance(v, list):
            clean[k] = [
                int(x) if isinstance(x, (np.integer,)) else
                float(x) if isinstance(x, (np.floating,)) else x
                for x in v
            ]
        elif isinstance(v, (np.integer,)):
            clean[k] = int(v)
        elif isinstance(v, (np.floating,)):
            clean[k] = float(v)
        elif isinstance(v, np.ndarray):
            clean[k] = v.tolist()
        else:
            clean[k] = v
    return clean


@router.post("/run", response_model=AnalysisRunResponse, status_code=202)
async def run_analysis(
    request: AnalysisRunRequest,
    data_service: DataService = Depends(get_data_service),
):
    """Trigger a full analysis pipeline. Returns immediately with task_id.

    The analysis runs asynchronously via Celery. Poll the status endpoint
    to track progress.
    """
    # Verify session exists
    session = data_service.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create analysis run record
    analysis_id = data_service.create_analysis_run(
        session_id=request.session_id,
    )

    # Dispatch Celery task
    from backend.tasks.analysis_tasks import run_analysis as run_analysis_task
    task = run_analysis_task.delay(
        analysis_id=analysis_id,
        session_id=request.session_id,
        config=request.config.model_dump(),
    )

    # Link task ID
    data_service.link_task(analysis_id, task.id)

    return AnalysisRunResponse(
        analysis_id=analysis_id,
        task_id=task.id,
        status="pending",
    )


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get analysis and task status with progress information."""
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Try to get detailed task progress from Celery
    task_id = run.get("task_id")
    current_stage = None
    progress_pct = 0
    message = None

    if task_id:
        try:
            async_result = AsyncResult(task_id, app=celery_app)
            if async_result.state == "PROGRESS":
                meta = async_result.info or {}
                current_stage = meta.get("stage")
                progress_pct = meta.get("progress_pct", 0)
                message = meta.get("message")
            elif async_result.state == "PENDING":
                progress_pct = 0
                current_stage = "queued"
                message = "Task is queued"
            elif async_result.state == "STARTED":
                progress_pct = 0
                current_stage = "starting"
                message = "Task is starting"
            elif async_result.state == "SUCCESS":
                progress_pct = 100
                current_stage = "completed"
                message = "Analysis completed"
            elif async_result.state == "FAILURE":
                progress_pct = 0
                current_stage = "failed"
                message = str(async_result.info) if async_result.info else "Unknown error"
        except Exception:
            # Fall back to DuckDB task_progress
            if task_id:
                tp = data_service.get_task_progress(task_id)
                if tp:
                    current_stage = tp.get("current_stage")
                    progress_pct = tp.get("progress_pct", 0)
                    message = tp.get("message")

    return AnalysisStatusResponse(
        analysis_id=analysis_id,
        task_id=task_id or "",
        status=run["status"],
        current_stage=current_stage,
        progress_pct=progress_pct,
        message=message,
        started_at=run.get("created_at"),
        completed_at=run.get("completed_at"),
        error_message=run.get("error_message"),
    )


@router.get("/{analysis_id}/results", response_model=AnalysisResultsResponse)
async def get_all_results(
    analysis_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get all analysis results as JSON."""
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if run["status"] not in ("completed",):
        raise HTTPException(
            status_code=400,
            detail=f"Analysis status is '{run['status']}', not 'completed'",
        )

    # Build response from DuckDB
    config = _sanitize_config(data_service.get_analysis_config(analysis_id))
    charts = data_service.get_all_charts(analysis_id)

    # IC results
    ic_df = data_service.get_ic_results(analysis_id)
    ic_data = _df_to_records(ic_df)

    return AnalysisResultsResponse(
        analysis_id=analysis_id,
        status=run["status"],
        config=config,
        ic={"data": ic_data} if ic_data else None,
        charts=charts if charts else None,
    )


@router.get("/{analysis_id}/results/ic")
async def get_ic_results(
    analysis_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get IC analysis results."""
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    ic_df = data_service.get_ic_results(analysis_id)
    if ic_df.empty:
        return {"analysis_id": analysis_id, "data": []}

    # Pivot to wide format for easier consumption
    try:
        wide = ic_df.pivot(index="date", columns="period", values="ic_value")
        wide.index = wide.index.astype(str)
        data = _df_to_records(wide.reset_index())
    except Exception:
        data = _df_to_records(ic_df)

    return {
        "analysis_id": analysis_id,
        "data": data,
    }


@router.get("/{analysis_id}/results/returns")
async def get_returns_results(
    analysis_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get returns analysis results."""
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    factor_returns = data_service.get_factor_returns(analysis_id)
    returns_by_q = data_service.get_returns_by_quantile(analysis_id)
    cum_returns = data_service.get_cumulative_returns(analysis_id)

    return {
        "analysis_id": analysis_id,
        "factor_returns": _df_to_records(factor_returns),
        "returns_by_quantile": _df_to_records(returns_by_q),
        "cumulative_returns": _df_to_records(cum_returns),
    }


@router.get("/{analysis_id}/results/alpha-beta")
async def get_alpha_beta(
    analysis_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get alpha/beta analysis results."""
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    ab = data_service.get_alpha_beta(analysis_id)
    return {
        "analysis_id": analysis_id,
        "data": _df_to_records(ab),
    }


@router.get("/{analysis_id}/results/turnover")
async def get_turnover_results(
    analysis_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get turnover analysis results."""
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    turnover = data_service.get_turnover_results(analysis_id)
    autocorr = data_service.get_autocorrelation_results(analysis_id)

    return {
        "analysis_id": analysis_id,
        "turnover": _df_to_records(turnover),
        "autocorrelation": _df_to_records(autocorr),
    }


@router.get("/{analysis_id}/results/summary-tables")
async def get_summary_tables(
    analysis_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get summary statistics tables."""
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    ab = data_service.get_alpha_beta(analysis_id)
    returns_by_q = data_service.get_returns_by_quantile(analysis_id)
    ic_df = data_service.get_ic_results(analysis_id)

    return {
        "analysis_id": analysis_id,
        "alpha_beta": _df_to_records(ab),
        "returns_by_quantile": _df_to_records(returns_by_q),
        "ic": _df_to_records(ic_df),
    }


@router.get("/{analysis_id}/results/charts/{chart_type}", response_model=ChartResponse)
async def get_chart(
    analysis_id: str,
    chart_type: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get a specific chart for an analysis.

    Chart types: ic_time_series, ic_histogram, ic_qq_plot,
    quantile_returns_bar, cumulative_returns, mean_quantile_spread,
    quantile_turnover, rank_autocorrelation
    """
    run = data_service.get_analysis_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Try to get from DB first
    base64_data = data_service.get_chart(analysis_id, chart_type)

    # Generate on-demand if not cached
    if not base64_data:
        chart_service = ChartService(data_service)
        generators = {
            "ic_time_series": chart_service.generate_ic_time_series,
            "ic_histogram": chart_service.generate_ic_hist,
            "ic_qq_plot": chart_service.generate_ic_qq,
            "quantile_returns_bar": chart_service.generate_quantile_returns_bar,
            "cumulative_returns": chart_service.generate_cumulative_returns,
            "mean_quantile_spread": chart_service.generate_mean_quantile_spread,
            "quantile_turnover": chart_service.generate_quantile_turnover,
            "rank_autocorrelation": chart_service.generate_autocorrelation,
        }
        gen = generators.get(chart_type)
        if not gen:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown chart type: {chart_type}. "
                       f"Available: {list(generators.keys())}",
            )
        base64_data = gen(analysis_id)
        if base64_data:
            data_service.save_chart(analysis_id, chart_type, base64_data)

    if not base64_data:
        raise HTTPException(
            status_code=404,
            detail=f"Chart '{chart_type}' could not be generated",
        )

    return ChartResponse(
        chart_type=chart_type,
        image=base64_data,
        format="png",
    )
