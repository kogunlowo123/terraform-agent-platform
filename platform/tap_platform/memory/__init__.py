"""Three-tier agent memory backends.

working  -> Redis with TTL (:mod:`redis_working`)
episodic -> Postgres agent_executions + checkpoints (:mod:`episodic`)
semantic -> vector store, Qdrant default (:mod:`qdrant_store`), Pinecone stub.

Vector stores are discovered via the ``tap.vector_stores`` entry-point group.
"""

from __future__ import annotations

__all__ = ["base", "episodic", "pinecone_store", "qdrant_store", "redis_working"]
