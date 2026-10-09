"""Episodic memory: durable execution history + LangGraph checkpoints in Postgres.

Backed by the ``agent_executions`` and ``checkpoints`` tables (see
``platform/db/schema.sql``); RLS scopes every query to the current tenant.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Episode(BaseModel):
    """One recorded agent execution."""

    id: str
    tenant_id: str
    agent_version_id: str
    run_id: str | None = None
    task: str
    outcome: str = Field(description="succeeded | failed | cancelled")
    summary: str | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    started_at: str
    finished_at: str | None = None


class Checkpoint(BaseModel):
    """One serialized LangGraph checkpoint for resumable executions."""

    id: str
    agent_execution_id: str
    sequence: int
    state: dict[str, Any] = Field(description="Serialized AgentState snapshot.")
    created_at: str


class EpisodicMemory:
    """Postgres-backed episodic store (tier 2 of the 3-tier memory)."""

    def __init__(self, db: Any) -> None:
        self._db = db  # async SQLAlchemy sessionmaker

    async def start_episode(
        self, tenant_id: str, agent_version_id: str, task: str, run_id: str | None = None
    ) -> Episode:
        """INSERT an agent_executions row at execution start."""
        raise NotImplementedError("INSERT agent_executions(status='running')")

    async def finish_episode(
        self,
        episode_id: str,
        *,
        outcome: str,
        summary: str | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> Episode:
        """Close the episode with its outcome and usage accounting."""
        raise NotImplementedError("UPDATE agent_executions SET outcome, finished_at, ...")

    async def save_checkpoint(self, episode_id: str, sequence: int, state: dict[str, Any]) -> Checkpoint:
        """Append a checkpoint snapshot (monotonic sequence per episode)."""
        raise NotImplementedError("INSERT checkpoints(sequence unique per execution)")

    async def latest_checkpoint(self, episode_id: str) -> Checkpoint | None:
        """Fetch the newest checkpoint for resume-after-interrupt."""
        raise NotImplementedError("SELECT checkpoints ORDER BY sequence DESC LIMIT 1")

    async def recent_episodes(
        self, tenant_id: str, agent_version_id: str, *, limit: int = 20
    ) -> list[Episode]:
        """Most recent episodes for an agent (context for the next task)."""
        raise NotImplementedError("SELECT agent_executions ORDER BY started_at DESC")
