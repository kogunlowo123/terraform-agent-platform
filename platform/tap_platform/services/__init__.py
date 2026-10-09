"""Service layer: business logic the API routers delegate to.

Every service exposes ``from_app_state(state)`` so routers stay free of
construction details; shared clients (DB engine, Temporal, Redis, event bus)
are created in the app lifespan and resolved here.
"""

from __future__ import annotations

__all__ = [
    "audit_service",
    "marketplace_service",
    "policy_service",
    "registry_service",
    "run_service",
]
