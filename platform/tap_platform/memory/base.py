"""Vector store abstraction for agent semantic memory.

Collections are namespaced ``tenant:{tenant_id}:agent:{agent_name}`` so
tenant isolation holds even in pooled deployments (ARCHITECTURE.md §6/§8).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    """One stored semantic-memory item."""

    id: str = Field(description="UUID as str.")
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(description="UTC ISO 8601.")


class SearchHit(BaseModel):
    """One similarity-search result."""

    record: MemoryRecord
    score: float = Field(description="Similarity score; higher is closer.")


class VectorStore(ABC):
    """Abstract semantic-memory backend (plugin group ``tap.vector_stores``)."""

    @staticmethod
    def collection_name(tenant_id: str, agent_name: str) -> str:
        """Canonical per-tenant, per-agent collection name."""
        return f"tenant:{tenant_id}:agent:{agent_name}"

    @abstractmethod
    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """Create the collection if it does not exist (idempotent)."""

    @abstractmethod
    async def upsert(
        self, collection: str, records: list[MemoryRecord], vectors: list[list[float]]
    ) -> None:
        """Insert or update records with their embedding vectors (1:1 by index)."""

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        limit: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Similarity search with optional exact-match metadata filtering."""

    @abstractmethod
    async def delete(self, collection: str, record_ids: list[str]) -> None:
        """Delete records by id."""

    @abstractmethod
    async def drop_collection(self, collection: str) -> None:
        """Drop an entire collection (tenant offboarding)."""
