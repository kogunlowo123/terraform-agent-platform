"""TAP control plane package.

The Terraform Agent Platform (TAP) control plane exposes the governed-run API
(FastAPI), orchestrates durable run lifecycles (Temporal), evaluates policy
(OPA), schedules ephemeral IaC runners, and persists multi-tenant state
(PostgreSQL with row-level security).

Subpackages
-----------
api        FastAPI routers (mounted under ``/v1``).
services   Business logic delegated to by the API layer.
workflows  Temporal workflows and activities (plan -> policy -> approve -> apply saga).
runner     Dual Terraform/OpenTofu runner abstraction + ephemeral K8s job launcher.
memory     Three-tier agent memory backends (working/episodic/semantic).
events     Event bus abstraction (NATS JetStream default, Kafka adapter).
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
