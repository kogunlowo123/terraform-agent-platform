"""Event bus ABC (plugin group ``tap.event_buses``)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Envelope for every TAP event."""

    id: str = Field(description="UUID as str; used for consumer dedupe.")
    subject: str = Field(description="e.g. tap.{tenant_id}.run.plan_finished")
    tenant_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: str = Field(description="UTC ISO 8601.")


EventHandler = Callable[[Event], Awaitable[None]]


def subject(tenant_id: str, domain: str, event: str) -> str:
    """Build the canonical subject ``tap.{tenant}.{domain}.{event}``.

    domains: run | agent | policy | cost | audit | marketplace
    """
    return f"tap.{tenant_id}.{domain}.{event}"


class EventBus(ABC):
    """Abstract publish/subscribe transport."""

    @abstractmethod
    async def connect(self) -> None:
        """Open the connection and ensure streams/topics exist."""

    @abstractmethod
    async def close(self) -> None:
        """Flush and close."""

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish one event at-least-once (consumers dedupe by event id)."""

    @abstractmethod
    async def subscribe(
        self, subject_filter: str, handler: EventHandler, *, durable_name: str | None = None
    ) -> None:
        """Subscribe a handler to a subject filter (wildcards allowed).

        ``durable_name`` requests a durable consumer so delivery resumes after
        restarts; handlers acking successfully advance the cursor.
        """
