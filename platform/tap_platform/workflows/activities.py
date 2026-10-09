"""Temporal activities invoked by TAP workflows.

Activities are the only place side effects happen; workflows stay
deterministic. All dataclasses are serialized by Temporal's default
pydantic-compatible converter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from temporalio import activity


@dataclass
class RunnerJobRequest:
    """Request to schedule one ephemeral runner job (plan or apply)."""

    run_id: str
    tenant_id: str
    workspace_id: str
    engine: str  # terraform | opentofu
    command: str  # plan | apply | destroy | show
    plan_artifact_uri: str | None = None  # required for apply: the evaluated artifact
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunnerJobResult:
    """Outcome of a runner job."""

    succeeded: bool
    plan_artifact_uri: str | None = None
    plan_json: dict[str, Any] = field(default_factory=dict)
    cost_delta_usd: float | None = None
    scan_findings: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class PolicyDecision:
    """Aggregated OPA decision for a plan."""

    allowed: bool
    enforcement_level: str  # hard_fail | soft_fail | advisory
    violations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ApprovalRequest:
    """Approval gate opened for a run."""

    run_id: str
    tenant_id: str
    reason: str
    sla_seconds: int = 24 * 3600


@dataclass
class CostEstimate:
    """Cost delta derived from a plan."""

    monthly_delta_usd: float
    currency: str = "USD"
    breakdown: list[dict[str, Any]] = field(default_factory=list)


@activity.defn
async def schedule_runner_job(request: RunnerJobRequest) -> RunnerJobResult:
    """Launch an ephemeral K8s runner Job and await its result.

    Contract: build the Job spec via
    :class:`tap_platform.runner.k8s_job_launcher.K8sJobLauncher`, submit it,
    heartbeat while polling, and translate the terminal pod state + uploaded
    artifacts into a :class:`RunnerJobResult`. For ``command == "apply"`` the
    job MUST execute the exact ``plan_artifact_uri`` produced by the plan
    stage (no re-plan; TOCTOU invariant).
    """
    raise NotImplementedError("K8s Job submit + poll + artifact collection")


@activity.defn
async def evaluate_policy(run_id: str, plan_json: dict[str, Any]) -> PolicyDecision:
    """Evaluate the plan JSON via PolicyService/OPA and persist policy_results."""
    raise NotImplementedError("delegate to PolicyService.evaluate_plan")


@activity.defn
async def request_approval(request: ApprovalRequest) -> str:
    """Create the approvals row, notify approvers (ChatOps), return approval_id.

    The decision itself arrives as a workflow signal, not an activity result.
    """
    raise NotImplementedError("INSERT approvals + notifier fan-out")


@activity.defn
async def record_audit(
    tenant_id: str,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append one immutable audit row (delegates to AuditService.record)."""
    raise NotImplementedError("delegate to AuditService.record")


@activity.defn
async def cost_estimate(plan_json: dict[str, Any]) -> CostEstimate:
    """Estimate the monthly cost delta of a plan (Infracost-style pricing)."""
    raise NotImplementedError("map resource changes to price book; sum monthly delta")
