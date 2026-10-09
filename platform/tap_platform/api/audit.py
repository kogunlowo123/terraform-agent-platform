"""/v1/audit — immutable, append-only audit trail (read-only API)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from tap_platform.api.common import CursorPage, PageParams, page_params
from tap_platform.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEntry(BaseModel):
    """One immutable audit row."""

    id: str
    tenant_id: str
    actor: str = Field(description="OIDC subject or agent identity that performed the action.")
    actor_type: str = Field(description="user | agent | system")
    action: str = Field(description="Dotted verb, e.g. run.apply.approved")
    resource_type: str
    resource_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(description="UTC ISO 8601.")


def _service(request: Request) -> AuditService:
    return AuditService.from_app_state(request.app.state)


@router.get("", response_model=CursorPage[AuditEntry])
async def list_audit(
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
    actor: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> CursorPage[AuditEntry]:
    """Query the tenant's audit trail (time range is UTC ISO 8601)."""
    return await _service(request).query(
        page, actor=actor, action=action, resource_type=resource_type, since=since, until=until
    )
