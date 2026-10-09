"""/v1/agents — Agent Registry: manifests, versions, capability discovery."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from tap_platform.api.common import CursorPage, PageParams, idempotency_key, page_params
from tap_platform.services.registry_service import RegistryService

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentDomain(StrEnum):
    """Agent operational domain (matches sdk AgentManifest.domain)."""

    APPOPS = "appops"
    DEVOPS = "devops"
    SECOPS = "secops"
    NETOPS = "netops"
    DATAOPS = "dataops"
    LLMOPS = "llmops"
    IDENTITY = "identity"
    COSTOPS = "costops"


class AgentRegister(BaseModel):
    """Request body for POST /v1/agents — register (or add a version to) an agent."""

    name: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-_]*$")
    version: str = Field(description="Semver, e.g. 1.2.0")
    domain: AgentDomain
    manifest: dict[str, Any] = Field(description="Full agent.yaml manifest (validated by SDK schema).")
    artifact_uri: str | None = Field(
        default=None, description="OCI reference of the signed agent artifact."
    )


class AgentVersion(BaseModel):
    """One published version of an agent."""

    id: str
    agent_id: str
    version: str
    manifest: dict[str, Any]
    artifact_uri: str | None = None
    signature_verified: bool = False
    created_at: str


class Agent(BaseModel):
    """Agent registry entry."""

    id: str
    tenant_id: str
    name: str
    domain: AgentDomain
    latest_version: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    enabled: bool = True
    created_at: str
    updated_at: str


def _service(request: Request) -> RegistryService:
    return RegistryService.from_app_state(request.app.state)


@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def register_agent(
    body: AgentRegister,
    request: Request,
    idem_key: Annotated[str | None, Depends(idempotency_key)] = None,
) -> Agent:
    """Register a new agent or publish a new version of an existing one."""
    return await _service(request).register_agent(body, idempotency_key=idem_key)


@router.get("", response_model=CursorPage[Agent])
async def list_agents(
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
    domain: AgentDomain | None = None,
    capability: str | None = None,
) -> CursorPage[Agent]:
    """Discover agents, optionally filtered by domain or capability."""
    return await _service(request).list_agents(page, domain=domain, capability=capability)


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, request: Request) -> Agent:
    """Fetch one agent."""
    return await _service(request).get_agent(agent_id)


@router.get("/{agent_id}/versions", response_model=CursorPage[AgentVersion])
async def list_agent_versions(
    agent_id: str,
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
) -> CursorPage[AgentVersion]:
    """List published versions for an agent, newest first."""
    return await _service(request).list_agent_versions(agent_id, page)
