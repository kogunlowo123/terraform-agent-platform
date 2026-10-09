"""/v1/workspaces — unit of infrastructure state + variables + RBAC."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from tap_platform.api.common import CursorPage, PageParams, idempotency_key, page_params
from tap_platform.services.registry_service import RegistryService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class ExecutionEngine(StrEnum):
    TERRAFORM = "terraform"
    OPENTOFU = "opentofu"


class WorkspaceCreate(BaseModel):
    """Request body for POST /v1/workspaces."""

    project_id: str = Field(description="UUID of the owning project.")
    name: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-_]*$")
    environment: str = Field(default="dev", description="dev | staging | prod | ...")
    engine: ExecutionEngine = ExecutionEngine.TERRAFORM
    engine_version: str = Field(default="1.9.0", description="Pinned terraform/tofu version.")
    vcs_repo: str | None = Field(default=None, description="e.g. github.com/org/repo//envs/dev")
    working_directory: str = "."
    variables: dict[str, Any] = Field(default_factory=dict)
    auto_apply: bool = False


class WorkspaceUpdate(BaseModel):
    """PATCH body; all fields optional."""

    engine: ExecutionEngine | None = None
    engine_version: str | None = None
    vcs_repo: str | None = None
    working_directory: str | None = None
    variables: dict[str, Any] | None = None
    auto_apply: bool | None = None


class Workspace(BaseModel):
    """Workspace resource representation."""

    id: str
    tenant_id: str
    project_id: str
    name: str
    environment: str
    engine: ExecutionEngine
    engine_version: str
    vcs_repo: str | None = None
    working_directory: str = "."
    auto_apply: bool = False
    locked: bool = False
    current_state_version_id: str | None = None
    created_at: str
    updated_at: str


def _service(request: Request) -> RegistryService:
    return RegistryService.from_app_state(request.app.state)


@router.post("", response_model=Workspace, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    request: Request,
    idem_key: Annotated[str | None, Depends(idempotency_key)] = None,
) -> Workspace:
    """Create a workspace bound to the caller's tenant."""
    return await _service(request).create_workspace(body, idempotency_key=idem_key)


@router.get("", response_model=CursorPage[Workspace])
async def list_workspaces(
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
    project_id: str | None = None,
    environment: str | None = None,
) -> CursorPage[Workspace]:
    """List workspaces visible to the caller."""
    return await _service(request).list_workspaces(page, project_id=project_id, environment=environment)


@router.get("/{workspace_id}", response_model=Workspace)
async def get_workspace(workspace_id: str, request: Request) -> Workspace:
    """Fetch one workspace."""
    return await _service(request).get_workspace(workspace_id)


@router.patch("/{workspace_id}", response_model=Workspace)
async def update_workspace(workspace_id: str, body: WorkspaceUpdate, request: Request) -> Workspace:
    """Partially update a workspace."""
    return await _service(request).update_workspace(workspace_id, body)


@router.post("/{workspace_id}/lock", response_model=Workspace)
async def lock_workspace(workspace_id: str, request: Request) -> Workspace:
    """Take the workspace state lock (Postgres advisory lock + flag)."""
    return await _service(request).set_workspace_lock(workspace_id, locked=True)


@router.post("/{workspace_id}/unlock", response_model=Workspace)
async def unlock_workspace(workspace_id: str, request: Request) -> Workspace:
    """Release the workspace state lock."""
    return await _service(request).set_workspace_lock(workspace_id, locked=False)
