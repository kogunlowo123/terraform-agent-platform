"""/v1/policies — policy sets (OPA bundles) and ad-hoc evaluation."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from tap_platform.api.common import CursorPage, PageParams, idempotency_key, page_params
from tap_platform.services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["policies"])


class EnforcementLevel(StrEnum):
    """How a policy set gates a run (ARCHITECTURE.md 'Policy Gate')."""

    HARD_FAIL = "hard_fail"
    SOFT_FAIL = "soft_fail"  # approval-required
    ADVISORY = "advisory"


class PolicySetCreate(BaseModel):
    """Request body for POST /v1/policies."""

    name: str = Field(min_length=1, max_length=120)
    enforcement_level: EnforcementLevel = EnforcementLevel.HARD_FAIL
    bundle_uri: str = Field(description="OCI/HTTP URI of the Rego bundle served to OPA.")
    description: str | None = None
    workspace_ids: list[str] = Field(default_factory=list, description="Workspaces bound to this set.")


class PolicySet(BaseModel):
    """Policy set resource."""

    id: str
    tenant_id: str
    name: str
    enforcement_level: EnforcementLevel
    bundle_uri: str
    description: str | None = None
    workspace_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class PolicyEvalRequest(BaseModel):
    """Ad-hoc evaluation of a plan JSON against the tenant's policy sets."""

    workspace_id: str
    plan_json: dict[str, Any] = Field(description="`terraform show -json` plan representation.")


class PolicyEvalResult(BaseModel):
    """Aggregated OPA decision."""

    allowed: bool
    enforcement_level: EnforcementLevel
    violations: list[dict[str, Any]] = Field(default_factory=list)
    evaluated_at: str = Field(description="UTC ISO 8601.")


def _service(request: Request) -> PolicyService:
    return PolicyService.from_app_state(request.app.state)


@router.post("", response_model=PolicySet, status_code=status.HTTP_201_CREATED)
async def create_policy_set(
    body: PolicySetCreate,
    request: Request,
    idem_key: Annotated[str | None, Depends(idempotency_key)] = None,
) -> PolicySet:
    """Create a policy set and register its bundle with OPA."""
    return await _service(request).create_policy_set(body, idempotency_key=idem_key)


@router.get("", response_model=CursorPage[PolicySet])
async def list_policy_sets(
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
) -> CursorPage[PolicySet]:
    """List the tenant's policy sets."""
    return await _service(request).list_policy_sets(page)


@router.get("/{policy_set_id}", response_model=PolicySet)
async def get_policy_set(policy_set_id: str, request: Request) -> PolicySet:
    """Fetch one policy set."""
    return await _service(request).get_policy_set(policy_set_id)


@router.post("/evaluate", response_model=PolicyEvalResult)
async def evaluate(body: PolicyEvalRequest, request: Request) -> PolicyEvalResult:
    """Evaluate a plan JSON against applicable policy sets without starting a run."""
    return await _service(request).evaluate_plan(body.workspace_id, body.plan_json)
