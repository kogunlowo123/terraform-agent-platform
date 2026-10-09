"""/v1/approvals — human approval gates signalled back into Temporal workflows."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from tap_platform.api.common import CursorPage, PageParams, idempotency_key, page_params
from tap_platform.services.run_service import RunService

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Approval(BaseModel):
    """An approval gate attached to a run."""

    id: str
    tenant_id: str
    run_id: str
    status: ApprovalStatus
    reason: str | None = Field(default=None, description="Why approval is required (policy soft-fail, destroy, ...).")
    requested_at: str
    expires_at: str = Field(description="SLA deadline; workflow times out after this.")
    decided_by: str | None = None
    decided_at: str | None = None
    decision_comment: str | None = None


class ApprovalDecision(BaseModel):
    """Request body for POST /v1/approvals/{id}/decision."""

    approve: bool
    comment: str | None = Field(default=None, max_length=2000)


def _service(request: Request) -> RunService:
    return RunService.from_app_state(request.app.state)


@router.get("", response_model=CursorPage[Approval])
async def list_approvals(
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
    approval_status: ApprovalStatus | None = None,
) -> CursorPage[Approval]:
    """List approvals for the caller's tenant (default: all, filterable by status)."""
    return await _service(request).list_approvals(page, status=approval_status)


@router.get("/{approval_id}", response_model=Approval)
async def get_approval(approval_id: str, request: Request) -> Approval:
    """Fetch one approval."""
    return await _service(request).get_approval(approval_id)


@router.post("/{approval_id}/decision", response_model=Approval)
async def decide(
    approval_id: str,
    body: ApprovalDecision,
    request: Request,
    idem_key: Annotated[str | None, Depends(idempotency_key)] = None,
) -> Approval:
    """Record a signed decision and signal the waiting RunWorkflow."""
    return await _service(request).decide_approval(
        approval_id, approve=body.approve, comment=body.comment, idempotency_key=idem_key
    )
