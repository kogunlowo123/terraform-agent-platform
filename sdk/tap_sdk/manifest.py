"""AgentManifest: the typed contract behind every agent's ``agent.yaml``.

The manifest is validated at registration time by the platform registry and at
load time by the SDK. Semver is enforced; domain is a closed enum.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class AgentDomain(StrEnum):
    """Operational domain the agent belongs to."""

    APPOPS = "appops"
    DEVOPS = "devops"
    SECOPS = "secops"
    NETOPS = "netops"
    DATAOPS = "dataops"
    LLMOPS = "llmops"
    IDENTITY = "identity"
    COSTOPS = "costops"


class MemoryConfig(BaseModel):
    """Three-tier memory configuration."""

    working_ttl_seconds: int = Field(default=3600, ge=60)
    episodic_enabled: bool = True
    semantic_enabled: bool = True
    semantic_collection_suffix: str | None = Field(
        default=None, description="Optional suffix appended to the default collection name."
    )
    embedding_model: str = "text-embedding-3-small"


class GuardrailsConfig(BaseModel):
    """Containment limits enforced by tap_sdk.guardrails.Guardrails."""

    allowed_resource_types: list[str] = Field(
        default_factory=list, description="Terraform resource types the agent may touch; empty = none."
    )
    allowed_regions: list[str] = Field(default_factory=list)
    max_resources_changed_per_run: int = Field(default=10, ge=0)
    require_policy_check_before_mutation: bool = True
    dry_run_default: bool = True


class ModelConfig(BaseModel):
    """LLM configuration routed through the AI Gateway."""

    provider: str = Field(default="anthropic", description="anthropic | azure-openai | bedrock | vertex | mistral")
    model: str = "claude-sonnet-4-5"
    max_tokens: int = Field(default=8192, ge=1)
    budget_usd_per_run: float = Field(default=5.0, ge=0)
    temperature: float = Field(default=0.0, ge=0, le=2)


class AgentManifest(BaseModel):
    """The agent.yaml contract."""

    name: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-_]*$")
    version: str = Field(description="Semver, e.g. 1.2.0")
    domain: AgentDomain
    description: str | None = None
    capabilities: list[str] = Field(
        default_factory=list,
        description="Discoverable capability tags, e.g. 'provision_vpc', 'rotate_iam_keys'.",
    )
    required_tools: list[str] = Field(
        default_factory=list,
        description="Platform tool names the agent needs (terraform_plan, policy_check, ...).",
    )
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)

    @field_validator("version")
    @classmethod
    def _validate_semver(cls, value: str) -> str:
        if not _SEMVER_RE.match(value):
            raise ValueError(f"version {value!r} is not valid semver")
        return value

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AgentManifest":
        """Load and validate an ``agent.yaml`` file."""
        raw: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.model_validate(raw)

    def to_yaml(self, path: str | Path) -> None:
        """Serialize back to agent.yaml (round-trip safe)."""
        Path(path).write_text(
            yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )
