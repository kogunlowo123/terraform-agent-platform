"""Qdrant implementation of the VectorStore ABC (TAP default)."""

from __future__ import annotations

from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from tap_platform.config import Settings, get_settings
from tap_platform.memory.base import MemoryRecord, SearchHit, VectorStore


class QdrantVectorStore(VectorStore):
    """Semantic memory on Qdrant (cosine distance)."""

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """Create the collection with cosine vectors if missing (idempotent)."""
        if not await self._client.collection_exists(collection):
            await self._client.create_collection(
                collection_name=collection,
                vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
            )

    async def upsert(
        self, collection: str, records: list[MemoryRecord], vectors: list[list[float]]
    ) -> None:
        """Upsert points; payload carries text + metadata + created_at."""
        points = [
            qm.PointStruct(
                id=record.id,
                vector=vector,
                payload={
                    "text": record.text,
                    "created_at": record.created_at,
                    **record.metadata,
                },
            )
            for record, vector in zip(records, vectors, strict=True)
        ]
        await self._client.upsert(collection_name=collection, points=points)

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        limit: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Cosine similarity search with exact-match payload filters."""
        query_filter = None
        if metadata_filter:
            query_filter = qm.Filter(
                must=[
                    qm.FieldCondition(key=key, match=qm.MatchValue(value=value))
                    for key, value in metadata_filter.items()
                ]
            )
        response = await self._client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        hits: list[SearchHit] = []
        for point in response.points:
            payload = dict(point.payload or {})
            text = str(payload.pop("text", ""))
            created_at = str(payload.pop("created_at", ""))
            hits.append(
                SearchHit(
                    record=MemoryRecord(
                        id=str(point.id), text=text, metadata=payload, created_at=created_at
                    ),
                    score=float(point.score),
                )
            )
        return hits

    async def delete(self, collection: str, record_ids: list[str]) -> None:
        """Delete points by id."""
        await self._client.delete(
            collection_name=collection,
            points_selector=qm.PointIdsList(points=list(record_ids)),
        )

    async def drop_collection(self, collection: str) -> None:
        """Drop the whole collection (tenant offboarding)."""
        await self._client.delete_collection(collection_name=collection)
