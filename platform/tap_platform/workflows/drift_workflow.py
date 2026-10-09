"""DriftWorkflow: scheduled drift detection per workspace.

Deployed on a Temporal Schedule (default: every 6 hours per workspace). A
drift run executes a refresh-only plan in an ephemeral runner; a non-empty
plan means live infrastructure diverged from state. Detected drift emits
``tap.{tenant}.run.drift_detected`` and may (per workspace policy) open a
remediation RunWorkflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from tap_platform.workflows.activities import (
        RunnerJobRequest,
        RunnerJobResult,
        record_audit,
        schedule_runner_job,
    )

_RUNNER_TIMEOUT = timedelta(minutes=30)
_RETRY = RetryPolicy(maximum_attempts=3, backoff_coefficient=2.0)


@dataclass
class DriftInput:
    """Workflow input for one scheduled drift check."""

    tenant_id: str
    workspace_id: str
    engine: str = "terraform"
    auto_remediate: bool = False  # open a remediation run when drift is found


@dataclass
class DriftOutput:
    """Result of one drift check."""

    workspace_id: str
    drift_detected: bool
    drifted_resources: list[str] = field(default_factory=list)
    remediation_run_id: str | None = None


@workflow.defn
class DriftWorkflow:
    """Scheduled drift detection over one workspace."""

    @workflow.run
    async def run(self, input: DriftInput) -> DriftOutput:
        """Run a refresh-only plan; report (and optionally remediate) drift."""
        drift_run_id = f"drift-{input.workspace_id}-{workflow.info().start_time.isoformat()}"

        result: RunnerJobResult = await workflow.execute_activity(
            schedule_runner_job,
            RunnerJobRequest(
                run_id=drift_run_id,
                tenant_id=input.tenant_id,
                workspace_id=input.workspace_id,
                engine=input.engine,
                command="plan",  # runner adds -refresh-only -detailed-exitcode
            ),
            start_to_close_timeout=_RUNNER_TIMEOUT,
            retry_policy=_RETRY,
        )
        if not result.succeeded:
            return DriftOutput(input.workspace_id, drift_detected=False)

        drifted = _drifted_resource_addresses(result)
        if not drifted:
            return DriftOutput(input.workspace_id, drift_detected=False)

        await workflow.execute_activity(
            record_audit,
            args=[
                input.tenant_id,
                "drift-detector",
                "run.drift_detected",
                "workspace",
                input.workspace_id,
                {"resources": drifted},
            ],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=_RETRY,
        )

        remediation_run_id: str | None = None
        if input.auto_remediate:
            # Child workflow: a full governed run (policy + approval still apply).
            remediation_run_id = await self._start_remediation(input)

        return DriftOutput(
            input.workspace_id,
            drift_detected=True,
            drifted_resources=drifted,
            remediation_run_id=remediation_run_id,
        )

    async def _start_remediation(self, input: DriftInput) -> str:
        """Start a child RunWorkflow to re-converge the workspace.

        Contract: start ``RunWorkflow`` as a child with action='apply' and
        auto_apply=False so the standard policy + approval gates govern the
        remediation; return its workflow id.
        """
        raise NotImplementedError("start child RunWorkflow(action='apply') for remediation")


def _drifted_resource_addresses(result: "RunnerJobResult") -> list[str]:
    """Extract drifted resource addresses from the plan JSON's resource_drift."""
    drift = result.plan_json.get("resource_drift", [])
    return [entry.get("address", "<unknown>") for entry in drift]
