"""FastAPI router for flow_builder endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from backend.app.flow_builder.models import (
    TemplateListResponse,
    TemplateDetailResponse,
    WorkflowCreateRequest,
    WorkflowCreateResponse,
)
from backend.app.flow_builder.templates import TEMPLATES
from backend.app.flow_builder.parser import create_workflow_from_template
from backend.app.services.data_service import DataService
from backend.app.dependencies import get_data_service
from backend.app.perfact.metadata_db import MetadataDB
from backend.app.perfact.executor import SerialExecutor
from backend.app.config import settings

router = APIRouter(prefix="/api/v1/flow-builder", tags=["flow-builder"])


@router.get("/templates", response_model=List[TemplateListResponse])
def list_templates():
    """Return all available workflow templates."""
    return [
        TemplateListResponse(
            template_id=t["template_id"],
            name=t["name"],
            description=t["description"],
            configurable_params=t["configurable_params"],
        )
        for t in TEMPLATES.values()
    ]


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
def get_template(template_id: str):
    """Get full template detail with all step definitions."""
    t = TEMPLATES.get(template_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return TemplateDetailResponse(**t)


@router.post("/workflows", response_model=WorkflowCreateResponse, status_code=201)
def create_workflow(
    request: WorkflowCreateRequest,
    data_service: DataService = Depends(get_data_service),
):
    """Instantiate a template as a workflow and execute it via perfact."""
    # Verify session exists
    session = data_service.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create the workflow definition
    try:
        workflow = create_workflow_from_template(
            template_id=request.template_id,
            session_id=request.session_id,
            parameters=request.parameters,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Execute via perfact
    metadata_db = MetadataDB(settings.METADATA_DB_PATH)
    executor = SerialExecutor(metadata_db, data_service, settings.JOBS_DB_DIR)
    job = executor.run_job(workflow, request.session_id)

    return WorkflowCreateResponse(
        workflow_id=workflow.workflow_id,
        template_id=request.template_id,
        job_id=job.job_id,
        step_count=len(workflow.steps),
        status=job.status.value,
    )
