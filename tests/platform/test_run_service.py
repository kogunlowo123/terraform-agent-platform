"""Contract tests for the Run service.

These tests pin the externally observable contract of the control plane's run
lifecycle against fully mocked dependencies (workflow engine, policy service,
event bus, repository). The reference implementation below is the executable
specification: when `tap_platform.services.run_service` lands, it replaces the
local import and MUST keep these tests green.

Contract under test (see docs/architecture/ARCHITECTURE.md §5):
  * create_run persists the run, starts a workflow, emits `run.created`.
  * Apply only ever executes a previously evaluated plan artifact.
  * Policy hard-fail moves the run to `policy_failed` and never applies.
  * Policy soft-fail parks the run in `awaiting_approval`; approval resumes it.
  * Destroy actions require approval regardless of policy result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock

import pytest

try:  # pragma: no cover - exercised once the platform module exists
    from tap_platform.services.run_service import Run, RunService  # type: ignore
except ImportError:  # reference implementation = executable contract

    @dataclass
    class Run:
        run_id: str
        workspace_id: str
        action: str
        state: str = "pending"
        plan_artifact: str | None = None

    @dataclass
    class RunService:
        repo: Any
        workflows: Any
        policy: Any
        bus: Any
        _seq: int = field(default=0)

        async def create_run(self, workspace_id: str, action: str) -> Run:
            if action not in {"plan", "apply", "destroy", "drift"}:
                raise ValueError(f"unsupported action: {action}")
            self._seq += 1
            run = Run(run_id=f"run-{self._seq}", workspace_id=workspace_id, action=action)
            await self.repo.save(run)
            await self.workflows.start("RunWorkflow", run.run_id)
            await self.bus.publish("run.created", {"run_id": run.run_id, "action": action})
            return run

        async def on_plan_complete(self, run: Run, plan_artifact: str) -> Run:
            run.plan_artifact = plan_artifact
            decision = await self.policy.evaluate(plan_artifact)
            if decision["deny"]:
                run.state = "policy_failed"
                await self.bus.publish("run.policy_failed", {"run_id": run.run_id, "messages": decision["deny"]})
            elif decision["soft_fail"] or run.action == "destroy":
                run.state = "awaiting_approval"
                await self.bus.publish("run.awaiting_approval", {"run_id": run.run_id})
            else:
                run.state = "ready_to_apply"
            await self.repo.save(run)
            return run

        async def approve(self, run: Run, approver: str) -> Run:
            if run.state != "awaiting_approval":
                raise ValueError("run is not awaiting approval")
            run.state = "ready_to_apply"
            await self.repo.save(run)
            await self.bus.publish("run.approved", {"run_id": run.run_id, "approver": approver})
            return run

        async def apply(self, run: Run) -> Run:
            if run.state != "ready_to_apply":
                raise ValueError("run is not ready to apply")
            if not run.plan_artifact:
                raise ValueError("no evaluated plan artifact")  # no-TOCTOU invariant
            await self.workflows.signal(run.run_id, "apply", run.plan_artifact)
            run.state = "applying"
            await self.repo.save(run)
            return run


@pytest.fixture()
def deps() -> dict[str, AsyncMock]:
    policy = AsyncMock()
    policy.evaluate.return_value = {"deny": [], "soft_fail": [], "advisory": []}
    return {
        "repo": AsyncMock(),
        "workflows": AsyncMock(),
        "policy": policy,
        "bus": AsyncMock(),
    }


@pytest.fixture()
def service(deps: dict[str, AsyncMock]) -> RunService:
    return RunService(**deps)


@pytest.mark.asyncio
async def test_create_run_persists_starts_workflow_and_emits_event(service, deps):
    run = await service.create_run("ws-1", "plan")

    assert run.state == "pending"
    deps["repo"].save.assert_awaited_once_with(run)
    deps["workflows"].start.assert_awaited_once_with("RunWorkflow", run.run_id)
    deps["bus"].publish.assert_awaited_once()
    subject, payload = deps["bus"].publish.await_args.args
    assert subject == "run.created"
    assert payload["run_id"] == run.run_id


@pytest.mark.asyncio
async def test_unknown_action_rejected(service):
    with pytest.raises(ValueError):
        await service.create_run("ws-1", "yolo")


@pytest.mark.asyncio
async def test_clean_policy_result_makes_run_ready(service):
    run = await service.create_run("ws-1", "apply")
    run = await service.on_plan_complete(run, "s3://plans/run-1.out")
    assert run.state == "ready_to_apply"
    assert run.plan_artifact == "s3://plans/run-1.out"


@pytest.mark.asyncio
async def test_policy_hard_fail_blocks_run(service, deps):
    deps["policy"].evaluate.return_value = {
        "deny": ["aws_s3_bucket.x: public ACL"],
        "soft_fail": [],
        "advisory": [],
    }
    run = await service.create_run("ws-1", "apply")
    run = await service.on_plan_complete(run, "s3://plans/run-1.out")

    assert run.state == "policy_failed"
    with pytest.raises(ValueError):
        await service.apply(run)


@pytest.mark.asyncio
async def test_policy_soft_fail_requires_approval(service, deps):
    deps["policy"].evaluate.return_value = {
        "deny": [],
        "soft_fail": ["cost over budget"],
        "advisory": [],
    }
    run = await service.create_run("ws-1", "apply")
    run = await service.on_plan_complete(run, "s3://plans/run-1.out")
    assert run.state == "awaiting_approval"

    run = await service.approve(run, approver="sec-lead@example.com")
    assert run.state == "ready_to_apply"


@pytest.mark.asyncio
async def test_destroy_always_requires_approval_even_when_policy_clean(service):
    run = await service.create_run("ws-1", "destroy")
    run = await service.on_plan_complete(run, "s3://plans/run-1.out")
    assert run.state == "awaiting_approval"


@pytest.mark.asyncio
async def test_apply_signals_workflow_with_evaluated_plan_artifact(service, deps):
    run = await service.create_run("ws-1", "apply")
    run = await service.on_plan_complete(run, "s3://plans/run-1.out")
    run = await service.apply(run)

    assert run.state == "applying"
    deps["workflows"].signal.assert_awaited_once_with(run.run_id, "apply", "s3://plans/run-1.out")


@pytest.mark.asyncio
async def test_apply_without_plan_artifact_rejected(service):
    run = await service.create_run("ws-1", "apply")
    run.state = "ready_to_apply"  # corrupt state on purpose: artifact missing
    with pytest.raises(ValueError, match="plan artifact"):
        await service.apply(run)
