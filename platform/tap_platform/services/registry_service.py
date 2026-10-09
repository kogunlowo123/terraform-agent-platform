"""Registry service: workspaces + agent registry (manifests, versions, discovery)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from tap_platform.config import Settings, get_settings

if TYPE_CHECKING:
    from tap_platform.api.agents import Agent, AgentDomain, AgentRegister, AgentVersion
    from tap_platform.api.common import CursorPage, PageParams
    from tap_platform.api.workspaces import Workspace, WorkspaceCreate, WorkspaceUpdate


class RegistryService:
    """CRUD + discovery for workspaces and registered agents."""

    def __init__(self, db: Any, settings: Settings) -> None:
        self._db = db  # async SQLAlchemy engine/sessionmaker from app state
        self._settings = settings

    @classmethod
    def from_app_state(cls, state: Any) -> Self:
        """Build from FastAPI ``app.state``."""
        return cls(getattr(state, "db", None), getattr(state, "settings", get_settings()))

    # --- workspaces ---------------------------------------------------------

    async def create_workspace(
        self, body: "WorkspaceCreate", *, idempotency_key: str | None = None
    ) -> "Workspace":
        """Create a workspace under the caller's tenant (unique name per project)."""
        raise NotImplementedError("INSERT workspaces; enforce (project_id, name) uniqueness")

    async def get_workspace(self, workspace_id: str) -> "Workspace":
        """Fetch one workspace."""
        raise NotImplementedError("SELECT workspaces with RLS")

    async def list_workspaces(
        self,
        page: "PageParams",
        *,
        project_id: str | None = None,
        environment: str | None = None,
    ) -> "CursorPage[Workspace]":
        """Cursor-paginated workspace listing."""
        raise NotImplementedError("keyset-paginate workspaces")

    async def update_workspace(self, workspace_id: str, body: "WorkspaceUpdate") -> "Workspace":
        """Apply a partial update; engine/version changes are audited."""
        raise NotImplementedError("UPDATE workspaces with set of non-None fields + audit row")

    async def set_workspace_lock(self, workspace_id: str, *, locked: bool) -> "Workspace":
        """Acquire/release the state lock (Postgres advisory lock keyed by workspace UUID)."""
        raise NotImplementedError("pg_advisory_lock/unlock + workspaces.locked flag")

    # --- agent registry -------------------------------------------------------

    async def register_agent(
        self, body: "AgentRegister", *, idempotency_key: str | None = None
    ) -> "Agent":
        """Validate manifest against SDK schema, upsert agent, insert agent_version."""
        raise NotImplementedError("upsert agents + INSERT agent_versions (semver-unique)")

    async def get_agent(self, agent_id: str) -> "Agent":
        """Fetch one agent."""
        raise NotImplementedError("SELECT agents with RLS")

    async def list_agents(
        self,
        page: "PageParams",
        *,
        domain: "AgentDomain | None" = None,
        capability: str | None = None,
    ) -> "CursorPage[Agent]":
        """Discover agents by domain/capability (capability matched in manifest JSONB)."""
        raise NotImplementedError("paginate agents; capability filter uses JSONB containment")

    async def list_agent_versions(self, agent_id: str, page: "PageParams") -> "CursorPage[AgentVersion]":
        """List published versions of one agent, newest first."""
        raise NotImplementedError("paginate agent_versions by semver desc")
