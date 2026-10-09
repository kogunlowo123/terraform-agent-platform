"""TAP v1 API routers.

Each module exposes a FastAPI ``router`` with pydantic request/response
models. Shared conventions (cursor pagination, RFC 7807 problem+json errors,
Idempotency-Key support on POST) live in :mod:`tap_platform.api.common`.
"""

from __future__ import annotations

__all__ = [
    "agents",
    "approvals",
    "audit",
    "common",
    "marketplace",
    "policies",
    "runs",
    "workspaces",
]
