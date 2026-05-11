"""Translates frontend requests into WorkflowDefinition instances."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.app.flow_builder.models import (
    WorkflowDefinition, WorkflowStep, AtomicStepType,
)
from backend.app.flow_builder.templates import TEMPLATES


def create_workflow_from_template(
    template_id: str,
    session_id: str,
    parameters: Dict[str, Any],
) -> WorkflowDefinition:
    """Instantiate a template with user-provided parameters."""
    template = TEMPLATES.get(template_id)
    if not template:
        raise ValueError(f"Unknown template: {template_id}")

    _validate_parameters(template["configurable_params"], parameters)

    workflow_id = str(uuid.uuid4())
    steps = []

    for idx, step_def in enumerate(template["steps"]):
        step_params = dict(step_def.get("parameters", {}))
        _inject_params(step_def["step_type"], step_params, parameters)

        steps.append(WorkflowStep(
            step_type=AtomicStepType(step_def["step_type"]),
            order=idx,
            depends_on=list(step_def.get("depends_on", [])),
            parameters=step_params,
            output_key=step_def["output_key"],
        ))

    return WorkflowDefinition(
        workflow_id=workflow_id,
        template_id=template_id,
        session_id=session_id,
        parameters=parameters,
        steps=steps,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _validate_parameters(
    configurable_params: List[Dict], provided: Dict[str, Any],
):
    """Check that provided parameters match configurable params schema."""
    known_params = {p["name"] for p in configurable_params}
    for key in provided:
        if key not in known_params:
            raise ValueError(f"Unknown parameter '{key}'. Known: {known_params}")


def _inject_params(
    step_type: str, target: Dict[str, Any], user_params: Dict[str, Any],
):
    """Map user-level params to individual step params.

    Maps user-facing parameter names to alphalens function parameter names
    for each step type.
    """
    param_mapping = {
        "get_clean_factor_and_forward_returns": {
            "periods": "periods",
            "quantiles": "quantiles",
            "bins": "bins",
            "filter_zscore": "filter_zscore",
            "max_loss": "max_loss",
            "zero_aware": "zero_aware",
            "cumulative_returns": "cumulative_returns",
            "by_group": "by_group",
        },
        "factor_returns": {
            "long_short": "demeaned",
            "group_neutral": "group_adjust",
        },
        "factor_alpha_beta": {
            "long_short": "demeaned",
            "group_neutral": "group_adjust",
        },
        "factor_information_coefficient": {
            "group_neutral": "group_adjust",
        },
        "mean_information_coefficient": {
            "group_neutral": "group_adjust",
        },
        "mean_return_by_quantile": {
            "long_short": "demeaned",
            "group_neutral": "group_adjust",
        },
        "average_cumulative_return_by_quantile": {
            "long_short": "demeaned",
            "group_neutral": "group_adjust",
        },
    }
    mapping = param_mapping.get(step_type, {})
    for user_key, step_key in mapping.items():
        if user_key in user_params:
            target[step_key] = user_params[user_key]
