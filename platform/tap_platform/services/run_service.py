"""Run service: starts and manages governed runs via Temporal.

Starting a run = persist the ``runs`` row (status ``pending``), then
``start_workflow(RunWorkflow, ...)`` on the ``tap-runs`` task queue with
workflow id ``run-{run_id}`` (idempotent per run). Approval decisions are
delivered to the workflow as signals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from temporalio.client import Client as TemporalClient

from tap_platform.config import Settings, get_settings

if TYPE_CHECKING:  # avoid import cycles with the router modules
    from tap_platform.api.approvals import Approval, ApprovalStatus
    from tap_platform.api.common import CursorPage, PageParams
    from tap_platform.api.runs import Run, RunCreate, RunEvent, RunStatus


class RunService:
    """Lifecycle operations for governed runs."""

    def __init__(self, temporal: TemporalClient | None, settings: Settings) -> None:
        self._temporal = temporal
        self._settings = settings

    @classmethod
    def from_app_state(cls, state: Any) -> Self:
        """Build from FastAPI ``app.state`` (temporal client wired in lifespan)."""
        return cls(getattr(state, "temporal", None), getattr(state, "settings", get_settings()))

    async def start_run(self, body: "RunCreate", *, idempotency_key: str | None = None) -> "Run":
        """Persist the run row and start ``RunWorkflow`` on Temporal.

        Contract: INSERT runs(status='pending'), emit run.created event, then
        ``temporal.start_workflow(RunWorkflow.run, RunInput(...), id=f"run-{run_id}",
        task_queue=settings.temporal_task_queue)``. Idempotency-Key replays
        return the originally created Run.
        """
        raise NotImplementedError("persist run row + start Temporal RunWorkflow (see docstring)")

    async def get_run(self, run_id: str) -> "Run":
        """Fetch one run within the caller's tenant (RLS enforced)."""
        raise NotImplementedError("SELECT from runs with RLS; 404 problem+json when absent")

    async def list_runs(
        self,
        page: "PageParams",
        *,
        workspace_id: str | None = None,
        status: "RunStatus | None" = None,
    ) -> "CursorPage[Run]":
        """Cursor-paginated run listing, newest first."""
        raise NotImplementedError("keyset-paginate runs by (created_at, id) desc")

    async def list_run_events(self, run_id: str, page: "PageParams") -> "CursorPage[RunEvent]":
        """Paginated immutable run timeline."""
        raise NotImplementedError("paginate run_events by sequence asc")

    async def cancel_run(self, run_id: str) -> "Run":
        """Request Temporal workflow cancellation; compensation handles partial applies."""
        raise NotImplementedError("temporal handle.cancel() + status transition to 'cancelled'")

    # --- approvals ---------------------------------------------------------

    async def list_approvals(
        self, page: "PageParams", *, status: "ApprovalStatus | None" = None
    ) -> "CursorPage[Approval]":
        """List approval gates for the tenant."""
        raise NotImplementedError("paginate approvals, optional status filter")

    async def get_approval(self, approval_id: str) -> "Approval":
        """Fetch one approval."""
        raise NotImplementedError("SELECT approvals with RLS")

    async def decide_approval(
        self,
        approval_id: str,
        *,
        approve: bool,
        comment: str | None = None,
        idempotency_key: str | None = None,
    ) -> "Approval":
        """Record the decision and signal the waiting workflow.

        Contract: UPDATE approvals SET status, decided_by (OIDC subject),
        decided_at; append audit row; then
        ``temporal.get_workflow_handle(f"run-{run_id}").signal("approval_decision", ...)``.
        """
        raise NotImplementedError("record decision + signal RunWorkflow 'approval_decision'")
