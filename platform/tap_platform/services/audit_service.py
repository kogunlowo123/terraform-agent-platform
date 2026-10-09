"""Audit service: append-only writes + filtered reads of the audit trail.

Audit rows are immutable (no UPDATE/DELETE grants; enforced in schema.sql).
Every state transition in the platform calls :meth:`AuditService.record`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from tap_platform.config import Settings, get_settings

if TYPE_CHECKING:
    from tap_platform.api.audit import AuditEntry
    from tap_platform.api.common import CursorPage, PageParams


class AuditService:
    """Write and query the immutable audit log."""

    def __init__(self, db: Any, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    @classmethod
    def from_app_state(cls, state: Any) -> Self:
        """Build from FastAPI ``app.state``."""
        return cls(getattr(state, "db", None), getattr(state, "settings", get_settings()))

    async def record(
        self,
        *,
        tenant_id: str,
        actor: str,
        actor_type: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> "AuditEntry":
        """Append one audit row and publish ``tap.{tenant}.audit.recorded``.

        Contract: single INSERT into audit_log inside the caller's
        transaction where possible, so audit and state change commit together.
        """
        raise NotImplementedError("INSERT audit_log + event publish")

    async def query(
        self,
        page: "PageParams",
        *,
        actor: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> "CursorPage[AuditEntry]":
        """Filtered, cursor-paginated audit reads (newest first)."""
        raise NotImplementedError("keyset-paginate audit_log with filters")
