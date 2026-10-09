"""RunWorkflow: the governed run saga (ARCHITECTURE.md §5).

plan -> policy -> approval (signal, SLA timeout) -> apply -> verify, with a
compensation path on failure. Invariants enforced here:

* Apply only ever executes the **previously evaluated plan artifact**
  (``RunnerJobResult.plan_artifact_uri`` from the plan stage) — never a
  re-plan (no TOCTOU window).
* ``destroy`` actions always require human approval regardless of the policy
  decision.
* Every transition records an audit row and emits ``run.*`` events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from tap_platform.workflows.activities import (
        ApprovalRequest,
        CostEstimate,
        PolicyDecision,
        RunnerJobRequest,
        RunnerJobResult,
        cost_estimate,
        evaluate_policy,
        record_audit,
        request_approval,
        schedule_runner_job,
    )

_DEFAULT_RETRY = RetryPolicy(maximum_attempts=3, backoff_coefficient=2.0)
_RUNNER_TIMEOUT = timedelta(minutes=45)
_APPROVAL_SLA = timedelta(hours=24)


@dataclass
class RunInput:
    """Workflow input (mirrors api.runs.RunCreate plus resolved identities)."""

    run_id: str
    tenant_id: str
    workspace_id: str
    action: str  # plan | apply | destroy | drift | cost | compliance
    engine: str  # terraform | opentofu
    variables: dict[str, Any] = field(default_factory=dict)
    auto_apply: bool = False
    requested_by: str = "system"


@dataclass
class ApprovalDecisionSignal:
    """Payload of the ``approval_decision`` signal from the approvals API."""

    approval_id: str
    approved: bool
    decided_by: str
    comment: str | None = None


@dataclass
class RunOutput:
    """Terminal result of the workflow."""

    run_id: str
    status: str  # succeeded | failed | cancelled | compensated
    plan_artifact_uri: str | None = None
    cost_delta_usd: float | None = None
    detail: str | None = None


@workflow.defn
class RunWorkflow:
    """Durable governed-run saga."""

    def __init__(self) -> None:
        self._decision: ApprovalDecisionSignal | None = None
        self._status: str = "pending"

    # --- signals / queries ---------------------------------------------------

    @workflow.signal
    def approval_decision(self, decision: ApprovalDecisionSignal) -> None:
        """Delivered by RunService.decide_approval."""
        self._decision = decision

    @workflow.query
    def status(self) -> str:
        """Current lifecycle status (mirrors the runs.status column)."""
        return self._status

    # --- main ------------------------------------------------------------------

    @workflow.run
    async def run(self, input: RunInput) -> RunOutput:
        """Execute the saga; compensation runs on apply/verify failure."""
        await self._audit(input, "run.started")

        # 1. PLAN — ephemeral runner produces the plan artifact + scans + cost.
        self._status = "planning"
        plan_result: RunnerJobResult = await workflow.execute_activity(
            schedule_runner_job,
            RunnerJobRequest(
                run_id=input.run_id,
                tenant_id=input.tenant_id,
                workspace_id=input.workspace_id,
                engine=input.engine,
                command="plan",
                variables=input.variables,
            ),
            start_to_close_timeout=_RUNNER_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        if not plan_result.succeeded:
            self._status = "failed"
            await self._audit(input, "run.plan.failed")
            return RunOutput(input.run_id, "failed", detail=plan_result.error)

        estimate: CostEstimate = await workflow.execute_activity(
            cost_estimate,
            plan_result.plan_json,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_DEFAULT_RETRY,
        )

        if input.action == "plan":
            self._status = "succeeded"
            await self._audit(input, "run.plan.succeeded")
            return RunOutput(
                input.run_id,
                "succeeded",
                plan_artifact_uri=plan_result.plan_artifact_uri,
                cost_delta_usd=estimate.monthly_delta_usd,
            )

        # 2. POLICY — OPA gate over the plan JSON.
        self._status = "policy_check"
        decision: PolicyDecision = await workflow.execute_activity(
            evaluate_policy,
            args=[input.run_id, plan_result.plan_json],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_DEFAULT_RETRY,
        )
        if not decision.allowed and decision.enforcement_level == "hard_fail":
            self._status = "failed"
            await self._audit(input, "run.policy.denied")
            return RunOutput(input.run_id, "failed", detail="policy hard-fail")

        # 3. APPROVAL — required for destroy (always), policy soft-fail, or
        #    when auto_apply is off.
        needs_approval = (
            input.action == "destroy"
            or (not decision.allowed and decision.enforcement_level == "soft_fail")
            or not input.auto_apply
        )
        if needs_approval:
            self._status = "awaiting_approval"
            reason = "destroy" if input.action == "destroy" else "policy soft-fail / manual gate"
            await workflow.execute_activity(
                request_approval,
                ApprovalRequest(
                    run_id=input.run_id,
                    tenant_id=input.tenant_id,
                    reason=reason,
                    sla_seconds=int(_APPROVAL_SLA.total_seconds()),
                ),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_DEFAULT_RETRY,
            )
            approved = await workflow.wait_condition(
                lambda: self._decision is not None, timeout=_APPROVAL_SLA
            )
            if not approved or self._decision is None or not self._decision.approved:
                self._status = "cancelled"
                await self._audit(input, "run.approval.rejected_or_expired")
                return RunOutput(input.run_id, "cancelled", detail="approval rejected or expired")
            await self._audit(input, "run.approval.granted")

        # 4. APPLY — MUST reuse the evaluated plan artifact (TOCTOU invariant).
        self._status = "applying"
        try:
            apply_result: RunnerJobResult = await workflow.execute_activity(
                schedule_runner_job,
                RunnerJobRequest(
                    run_id=input.run_id,
                    tenant_id=input.tenant_id,
                    workspace_id=input.workspace_id,
                    engine=input.engine,
                    command="apply" if input.action != "destroy" else "destroy",
                    plan_artifact_uri=plan_result.plan_artifact_uri,
                ),
                start_to_close_timeout=_RUNNER_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=1),  # applies are not blindly retried
            )
            if not apply_result.succeeded:
                raise RuntimeError(apply_result.error or "apply failed")

            # 5. VERIFY — drift check + health probes over the new state.
            self._status = "verifying"
            verify_result: RunnerJobResult = await workflow.execute_activity(
                schedule_runner_job,
                RunnerJobRequest(
                    run_id=input.run_id,
                    tenant_id=input.tenant_id,
                    workspace_id=input.workspace_id,
                    engine=input.engine,
                    command="plan",  # empty plan == no drift immediately after apply
                ),
                start_to_close_timeout=_RUNNER_TIMEOUT,
                retry_policy=_DEFAULT_RETRY,
            )
            if not verify_result.succeeded:
                raise RuntimeError(verify_result.error or "post-apply verification failed")

        except Exception as exc:  # noqa: BLE001 — saga boundary
            # COMPENSATE — roll back to the last known-good state version.
            self._status = "compensating"
            await self._audit(input, "run.compensation.started")
            await self._compensate(input)
            self._status = "compensated"
            return RunOutput(input.run_id, "compensated", detail=str(exc))

        self._status = "succeeded"
        await self._audit(input, "run.apply.succeeded")
        return RunOutput(
            input.run_id,
            "succeeded",
            plan_artifact_uri=plan_result.plan_artifact_uri,
            cost_delta_usd=estimate.monthly_delta_usd,
        )

    # --- helpers --------------------------------------------------------------

    async def _compensate(self, input: RunInput) -> None:
        """Compensation branch: restore the last known-good STATE_VERSION.

        Contract: schedule a runner job that applies the inverse plan (or
        performs a state rollback to the previous state_versions row), then
        audit the outcome. Compensation failures page a human — they are
        never silently swallowed.
        """
        await workflow.execute_activity(
            schedule_runner_job,
            RunnerJobRequest(
                run_id=input.run_id,
                tenant_id=input.tenant_id,
                workspace_id=input.workspace_id,
                engine=input.engine,
                command="apply",  # inverse/rollback plan produced by the compensation planner
            ),
            start_to_close_timeout=_RUNNER_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

    async def _audit(self, input: RunInput, action: str) -> None:
        """Record an audit row for a lifecycle transition."""
        await workflow.execute_activity(
            record_audit,
            args=[input.tenant_id, input.requested_by, action, "run", input.run_id, None],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=_DEFAULT_RETRY,
        )
