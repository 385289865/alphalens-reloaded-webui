"""Celery task definitions for alphalens analysis pipeline."""

from celery import Task

from backend.app.celery_app import celery_app
from backend.app.services.data_service import DataService
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.chart_service import ChartService
from backend.app.config import settings
from backend.app.models.schemas import AnalysisConfig


class AnalysisTask(Task):
    """Base task with service initialization for each worker process."""
    _data_service = None
    _analysis_service = None
    _chart_service = None

    @property
    def data_service(self):
        if self._data_service is None:
            self._data_service = DataService(settings.DB_PATH)
        return self._data_service

    @property
    def analysis_service(self):
        if self._analysis_service is None:
            self._analysis_service = AnalysisService(self.data_service)
        return self._analysis_service

    @property
    def chart_service(self):
        if self._chart_service is None:
            self._chart_service = ChartService(self.data_service)
        return self._chart_service


@celery_app.task(
    bind=True,
    base=AnalysisTask,
    name="run_analysis",
    track_started=True,
)
def run_analysis(self, analysis_id: str, session_id: str, config: dict):
    """Celery task that runs the full alphalens analysis pipeline.

    State progression:
    PENDING → RECEIVED → STARTED → PROGRESS → SUCCESS/FAILURE
    """
    def progress_callback(stage: str, pct: int):
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": stage,
                "progress_pct": pct,
                "message": f"Stage: {stage} ({pct}%)",
                "analysis_id": analysis_id,
            }
        )
        # Persistent fallback in DuckDB
        self.data_service.update_task_progress(
            task_id=self.request.id,
            analysis_id=analysis_id,
            status="running",
            current_stage=stage,
            progress_pct=pct,
        )

    try:
        # Mark analysis as running
        self.data_service.update_analysis_status(analysis_id, "running")
        self.data_service.link_task(analysis_id, self.request.id)

        # Parse config
        analysis_config = AnalysisConfig(**config)

        # Run the analysis pipeline
        self.analysis_service.run_full_analysis(
            analysis_id=analysis_id,
            session_id=session_id,
            config=analysis_config,
            progress_callback=progress_callback,
        )

        # Generate all charts
        progress_callback("generating_charts", 95)
        charts = self.chart_service.generate_all_charts(analysis_id)
        for chart_type, base64_data in charts.items():
            if base64_data:
                self.data_service.save_chart(analysis_id, chart_type, base64_data)

        # Mark as completed
        self.data_service.update_analysis_status(analysis_id, "completed")
        self.data_service.update_task_progress(
            task_id=self.request.id,
            analysis_id=analysis_id,
            status="completed",
            current_stage="completed",
            progress_pct=100,
            message="Analysis completed successfully",
        )

        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "charts_generated": list(charts.keys()),
        }

    except Exception as exc:
        error_msg = str(exc)
        self.data_service.update_analysis_status(analysis_id, "failed", error_msg)
        self.data_service.update_task_progress(
            task_id=self.request.id,
            analysis_id=analysis_id,
            status="failed",
            current_stage="error",
            progress_pct=0,
            message=error_msg,
        )
        raise


@celery_app.task(
    bind=True,
    base=AnalysisTask,
    name="generate_charts_only",
    track_started=True,
)
def generate_charts_only(self, analysis_id: str):
    """Task to only generate charts for a previously completed analysis."""
    charts = self.chart_service.generate_all_charts(analysis_id)
    for chart_type, base64_data in charts.items():
        if base64_data:
            self.data_service.save_chart(analysis_id, chart_type, base64_data)
    return {
        "analysis_id": analysis_id,
        "status": "completed",
        "charts_generated": list(charts.keys()),
    }
