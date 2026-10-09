"""Client facade for the 3-tier agent memory against the platform API.

working  — short-lived scratch (Redis behind the platform)
episodic — execution history + checkpoints (Postgres)
semantic — vector recall (Qdrant/Pinecone), namespaced per tenant+agent
"""

from __future__ import annotations

from typing import Any

import httpx

DEFAULT_BASE_URL = "http://localhost:8080/v1"


class MemoryClient:
    """One client, three tiers. All ids are UUID strings; timestamps UTC ISO 8601."""

    def __init__(
        self,
        agent_name: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
    ) -> None:
        self.agent_name = agent_name
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._http = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30)

    async def aclose(self) -> None:
        """Release the underlying HTTP client."""
        await self._http.aclose()

    # --- working (TTL scratch) -------------------------------------------------

    async def working_set(self, execution_id: str, key: str, value: Any, *, ttl_seconds: int = 3600) -> None:
        """Store a JSON value in working memory for this execution."""
        raise NotImplementedError("PUT /v1/memory/working/{execution_id}/{key}")

    async def working_get(self, execution_id: str, key: str) -> Any | None:
        """Fetch a working-memory value; None when missing/expired."""
        raise NotImplementedError("GET /v1/memory/working/{execution_id}/{key}")

    # --- episodic (history + checkpoints) ----------------------------------------

    async def recall_episodes(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch this agent's most recent execution summaries."""
        raise NotImplementedError("GET /v1/memory/episodes?agent={name}&limit=...")

    async def save_checkpoint(self, execution_id: str, sequence: int, state: dict[str, Any]) -> None:
        """Persist a LangGraph checkpoint snapshot."""
        raise NotImplementedError("POST /v1/memory/episodes/{execution_id}/checkpoints")

    async def latest_checkpoint(self, execution_id: str) -> dict[str, Any] | None:
        """Fetch the newest checkpoint for resume."""
        raise NotImplementedError("GET /v1/memory/episodes/{execution_id}/checkpoints/latest")

    # --- semantic (vector recall) ---------------------------------------------------

    async def remember(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Embed and store a memory; returns the new record id."""
        raise NotImplementedError("POST /v1/memory/semantic {agent, text, metadata}")

    async def recall(
        self, query: str, *, limit: int = 10, metadata_filter: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Similarity-search this agent's semantic memory."""
        raise NotImplementedError("POST /v1/memory/semantic/search {agent, query, limit, filter}")
