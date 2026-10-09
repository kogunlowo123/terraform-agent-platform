"""IaC runner abstraction: one interface over Terraform and OpenTofu."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ScanFinding(BaseModel):
    """One security-scan finding attached to a plan (Checkov/tfsec/Trivy)."""

    scanner: str = Field(description="checkov | tfsec | trivy | terrascan")
    rule_id: str
    severity: str = Field(description="critical | high | medium | low | info")
    resource: str | None = None
    message: str
    file: str | None = None
    line: int | None = None


class PlanResult(BaseModel):
    """Typed outcome of a plan operation."""

    succeeded: bool
    has_changes: bool = False
    plan_artifact_path: str | None = Field(
        default=None, description="Local path of the binary plan file (uploaded as the run artifact)."
    )
    plan_json: dict[str, Any] = Field(
        default_factory=dict, description="`show -json` representation of the plan."
    )
    resource_changes: int = 0
    cost_delta_usd: float | None = Field(
        default=None, description="Estimated monthly cost delta, when estimation ran."
    )
    scan_findings: list[ScanFinding] = Field(default_factory=list)
    stderr: str | None = None


class ApplyResult(BaseModel):
    """Typed outcome of apply/destroy."""

    succeeded: bool
    resources_added: int = 0
    resources_changed: int = 0
    resources_destroyed: int = 0
    new_state_serial: int | None = None
    stderr: str | None = None


class IaCRunner(ABC):
    """Abstract IaC engine driver executed inside an ephemeral runner pod.

    Implementations wrap the engine CLI with ``-json`` streaming output and
    never persist credentials: cloud access arrives as short-lived OIDC
    tokens injected into the job environment.
    """

    #: engine identifier used in workspaces.engine ("terraform" / "opentofu")
    engine: str

    def __init__(self, working_dir: Path, env: dict[str, str] | None = None) -> None:
        self.working_dir = working_dir
        self.env = env or {}

    @abstractmethod
    async def init(self, backend_config: dict[str, str] | None = None) -> None:
        """Run ``<engine> init`` with generated backend configuration."""

    @abstractmethod
    async def plan(
        self,
        *,
        variables: dict[str, Any] | None = None,
        destroy: bool = False,
        refresh_only: bool = False,
        out_file: str = "plan.out",
    ) -> PlanResult:
        """Produce a plan artifact + machine-readable plan JSON (via show)."""

    @abstractmethod
    async def apply(self, plan_file: str) -> ApplyResult:
        """Apply a **previously produced plan artifact** — never a fresh plan.

        The governed-run saga guarantees this file is exactly the artifact
        that policy evaluated (TOCTOU invariant).
        """

    @abstractmethod
    async def destroy(self, *, variables: dict[str, Any] | None = None) -> ApplyResult:
        """Destroy all managed resources (always human-approved upstream)."""

    @abstractmethod
    async def show(self, plan_file: str) -> dict[str, Any]:
        """Return the JSON representation of a plan artifact (``show -json``)."""
