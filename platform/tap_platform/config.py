"""Central configuration for the TAP control plane.

Settings are loaded (highest precedence first) from environment variables
prefixed ``TAP_``, an optional ``.env`` file, and the YAML file passed via
``tap-server --config`` (see ``tap_platform.main``). All URLs/DSNs are plain
strings so they can reference external secret managers at deploy time.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VectorStoreKind(StrEnum):
    """Supported semantic-memory backends (plugin group ``tap.vector_stores``)."""

    QDRANT = "qdrant"
    PINECONE = "pinecone"


class EventBusKind(StrEnum):
    """Supported event bus backends (plugin group ``tap.event_buses``)."""

    NATS = "nats"
    KAFKA = "kafka"


class Settings(BaseSettings):
    """Runtime settings for the control plane process."""

    model_config = SettingsConfigDict(
        env_prefix="TAP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- service identity -------------------------------------------------
    service_name: str = "tap-control-plane"
    environment: str = Field(default="dev", description="dev | staging | prod")
    host: str = "0.0.0.0"
    port: int = 8080

    # --- PostgreSQL (system of record, RLS on tenant_id) -------------------
    database_url: str = Field(
        default="postgresql+asyncpg://tap:tap@localhost:5432/tap",
        description="SQLAlchemy async DSN. RLS requires `SET app.tenant_id` per session.",
    )
    database_pool_size: int = 10

    # --- Redis (sessions, locks, working memory, rate counters) ------------
    redis_url: str = "redis://localhost:6379/0"

    # --- NATS JetStream (event bus) ----------------------------------------
    nats_url: str = "nats://localhost:4222"
    event_bus: EventBusKind = EventBusKind.NATS
    kafka_bootstrap_servers: str = "localhost:9092"

    # --- Temporal (durable run lifecycle) ----------------------------------
    temporal_target: str = "localhost:7233"
    temporal_namespace: str = "tap"
    temporal_task_queue: str = "tap-runs"

    # --- OPA (policy gates) -------------------------------------------------
    opa_url: str = Field(
        default="http://localhost:8181",
        description="Base URL of the OPA server hosting TAP Rego bundles.",
    )
    opa_decision_path: str = "/v1/data/tap/terraform/decision"

    # --- OIDC (authn) --------------------------------------------------------
    oidc_issuer: str = Field(
        default="https://login.example.com/tap",
        description="OIDC issuer URL; JWKS discovered at {issuer}/.well-known/openid-configuration.",
    )
    oidc_audience: str = "tap-api"

    # --- Vector store (semantic memory) --------------------------------------
    vector_store: VectorStoreKind = VectorStoreKind.QDRANT
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    pinecone_api_key: str | None = None
    pinecone_index: str = "tap-semantic"

    # --- Runners --------------------------------------------------------------
    runner_namespace: str = Field(
        default="tap-runners", description="K8s namespace for ephemeral runner Jobs."
    )
    runner_image_terraform: str = "ghcr.io/tap/runner-terraform:1.9"
    runner_image_opentofu: str = "ghcr.io/tap/runner-opentofu:1.8"

    # --- Observability ----------------------------------------------------------
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton (env/.env resolved once)."""
    return Settings()
