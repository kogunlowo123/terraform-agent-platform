"""Pinecone implementation of the VectorStore ABC (stub).

Install the ``pinecone`` extra (``pip install tap-platform[pinecone]``) and
select it via ``TAP_VECTOR_STORE=pinecone``. Collections map to Pinecone
namespaces inside one index (``settings.pinecone_index``).
"""

from __future__ import annotations

from typing import Any

from tap_platform.config import Settings, get_settings
from tap_platform.memory.base import MemoryRecord, SearchHit, VectorStore


class PineconeVectorStore(VectorStore):
    """Semantic memory on Pinecone serverless (namespace-per-collection)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.pinecone_api_key:
            raise ValueError("TAP_PINECONE_API_KEY is required for the pinecone vector store")

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """Ensure the shared index exists; namespaces are created lazily on upsert."""
        raise NotImplementedError("pinecone.create_index if missing (serverless spec)")

    async def upsert(
        self, collection: str, records: list[MemoryRecord], vectors: list[list[float]]
    ) -> None:
        """Upsert vectors into the namespace named after the collection."""
        raise NotImplementedError("index.upsert(vectors=..., namespace=collection)")

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        limit: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Query the namespace with optional metadata filter."""
        raise NotImplementedError("index.query(..., namespace=collection, filter=...)")

    async def delete(self, collection: str, record_ids: list[str]) -> None:
        """Delete vectors by id from the namespace."""
        raise NotImplementedError("index.delete(ids=..., namespace=collection)")

    async def drop_collection(self, collection: str) -> None:
        """Delete the whole namespace."""
        raise NotImplementedError("index.delete(delete_all=True, namespace=collection)")
