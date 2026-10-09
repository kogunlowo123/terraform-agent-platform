"""Working memory: short-lived per-execution scratch space on Redis.

Keys: ``tap:wm:{tenant_id}:{agent_execution_id}:{key}`` with a default TTL.
Working memory is a convenience cache — losing it must never corrupt a run
(durable state lives in Postgres checkpoints).
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from tap_platform.config import Settings, get_settings

DEFAULT_TTL_SECONDS = 3600


class RedisWorkingMemory:
    """TTL'd key/value scratch space for one agent execution."""

    def __init__(self, redis: Redis | None = None, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._redis: Redis = redis or Redis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def _key(tenant_id: str, execution_id: str, key: str) -> str:
        return f"tap:wm:{tenant_id}:{execution_id}:{key}"

    async def set(
        self,
        tenant_id: str,
        execution_id: str,
        key: str,
        value: Any,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        """Store a JSON-serializable value with TTL."""
        await self._redis.set(
            self._key(tenant_id, execution_id, key), json.dumps(value), ex=ttl_seconds
        )

    async def get(self, tenant_id: str, execution_id: str, key: str) -> Any | None:
        """Fetch a value; None when missing/expired."""
        raw = await self._redis.get(self._key(tenant_id, execution_id, key))
        return None if raw is None else json.loads(raw)

    async def delete(self, tenant_id: str, execution_id: str, key: str) -> None:
        """Remove one key."""
        await self._redis.delete(self._key(tenant_id, execution_id, key))

    async def clear_execution(self, tenant_id: str, execution_id: str) -> int:
        """Drop all working memory for an execution; returns keys removed."""
        pattern = self._key(tenant_id, execution_id, "*")
        removed = 0
        async for key in self._redis.scan_iter(match=pattern):
            await self._redis.delete(key)
            removed += 1
        return removed
