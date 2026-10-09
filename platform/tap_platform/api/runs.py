"""/v1/runs — governed run lifecycle (plan/apply/destroy/drift/cost/compliance).

POST /runs starts a Temporal ``RunWorkflow`` (plan -> policy -> approval ->
apply -> verify, with compensation). See ARCHITECTURE.md §5.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from tap_platform.api.common import CursorPage, PageParams, idempotency_key, page_params
from tap_platform.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


class RunAction(StrEnum):
    """What the run does to the workspace."""

    PLAN = "plan"
    APPLY = "apply"
    DESTROY = "destroy"
    DRIFT = "drift"
    COST = "cost"
    COMPLIANCE = "compliance"


class RunStatus(StrEnum):
    """Run lifecycle states (mirrors the ``runs.status`` CHECK constraint)."""

    PENDING = "pending"
    PLANNING = "planning"
    POLICY_CHECK = "policy_check"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLYING = "applying"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATED = "compensated"


class RunCreate(BaseModel):
    """Request body for POST /v1/runs."""

    workspace_id: str = Field(description="UUID of the target workspace.")
    action: RunAction = RunAction.PLAN
    engine: str = Field(default="terraform", description="terraform | opentofu")
    variables: dict[str, Any] = Field(default_factory=dict, description="Run-scoped TF variables.")
    message: str | None = Field(default=None, description="Operator-supplied reason/annotation.")
    auto_apply: bool = Field(
        default=False,
        description="Apply without human approval when policy result is pass (never for destroy).",
    )


class Run(BaseModel):
    """Run resource representation."""

    id: str
    tenant_id: str
    workspace_id: str
    action: RunAction
    status: RunStatus
    engine: str
    message: str | None = None
    plan_artifact_uri: str | None = Field(
        default=None, description="URI of the evaluated plan artifact that apply must reuse."
    )
    cost_delta_usd: float | None = None
    created_at: str = Field(description="UTC ISO 8601.")
    updated_at: str = Field(description="UTC ISO 8601.")


class RunEvent(BaseModel):
    """Immutable run timeline event."""

    id: str
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


def _service(request: Request) -> RunService:
    """Resolve the run service from app state (wired in main lifespan)."""
    return RunService.from_app_state(request.app.state)


@router.post("", response_model=Run, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    body: RunCreate,
    request: Request,
    idem_key: Annotated[str | None, Depends(idempotency_key)] = None,
) -> Run:
    """Start a governed run; returns 202 with the pending Run resource."""
    return await _service(request).start_run(body, idempotency_key=idem_key)


@router.get("", response_model=CursorPage[Run])
async def list_runs(
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
    workspace_id: str | None = None,
    run_status: RunStatus | None = None,
) -> CursorPage[Run]:
    """List runs for the caller's tenant, newest first."""
    return await _service(request).list_runs(page, workspace_id=workspace_id, status=run_status)


@router.get("/{run_id}", response_model=Run)
async def get_run(run_id: str, request: Request) -> Run:
    """Fetch a single run (404 problem+json when absent or cross-tenant)."""
    return await _service(request).get_run(run_id)


@router.get("/{run_id}/events", response_model=CursorPage[RunEvent])
async def list_run_events(
    run_id: str,
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
) -> CursorPage[RunEvent]:
    """Stream-friendly timeline of run events (also published on NATS)."""
    return await _service(request).list_run_events(run_id, page)


@router.post("/{run_id}/cancel", response_model=Run)
async def cancel_run(run_id: str, request: Request) -> Run:
    """Cancel a run; triggers Temporal cancellation + compensation if applying."""
    return await _service(request).cancel_run(run_id)
