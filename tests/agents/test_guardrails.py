"""Guardrail violation contract tests.

The guardrail layer (docs/architecture/ARCHITECTURE.md §4, §12) sits on every
mutating edge of an agent graph and enforces:

  * scope allowlists    — an agent may only touch resource types/workspaces it
                          is scoped to;
  * mutation budgets    — a hard cap on mutating tool calls per execution;
  * policy pre-check    — mutating tool calls require a prior passing policy
                          evaluation for the same plan artifact;
  * destroy approval    — destroy is NEVER autonomous, regardless of policy;
  * dry-run default     — mutation without an explicit live flag is a dry run.

The reference implementation is the executable specification until
`agents.core.guardrails` lands; each violation is raised as
GuardrailViolation(rule=...) and counted, matching the
`tap_agent_guardrail_violations_total{rule=...}` metric contract.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import pytest

try:  # pragma: no cover - exercised once the agents module exists
    from agents.core.guardrails import Guardrails, GuardrailViolation, ToolCall  # type: ignore
except ImportError:  # reference implementation = executable contract

    class GuardrailViolation(Exception):
        def __init__(self, rule: str, message: str) -> None:
            super().__init__(message)
            self.rule = rule

    @dataclass(frozen=True)
    class ToolCall:
        tool: str
        resource_type: str
        workspace: str
        mutating: bool = False
        action: str = "read"
        plan_artifact: str | None = None
        live: bool = False

    @dataclass
    class Guardrails:
        scope_resource_types: set[str]
        scope_workspaces: set[str]
        mutation_budget: int
        violations: Counter = field(default_factory=Counter)
        _mutations: int = 0
        _approved_artifacts: set[str] = field(default_factory=set)
        _human_approved: set[str] = field(default_factory=set)

        def record_policy_pass(self, plan_artifact: str) -> None:
            self._approved_artifacts.add(plan_artifact)

        def record_human_approval(self, plan_artifact: str) -> None:
            self._human_approved.add(plan_artifact)

        def _violate(self, rule: str, message: str) -> None:
            self.violations[rule] += 1
            raise GuardrailViolation(rule, message)

        def check(self, call: ToolCall) -> None:
            if call.resource_type not in self.scope_resource_types:
                self._violate("scope.resource_type", f"{call.resource_type} outside agent scope")
            if call.workspace not in self.scope_workspaces:
                self._violate("scope.workspace", f"workspace {call.workspace} outside agent scope")
            if not call.mutating:
                return
            if not call.live:
                return  # dry-run default: simulated mutations are always allowed
            if self._mutations >= self.mutation_budget:
                self._violate("mutation_budget", f"mutation budget {self.mutation_budget} exhausted")
            if call.plan_artifact not in self._approved_artifacts:
                self._violate("policy_precheck", "mutating call without passing policy evaluation")
            if call.action == "destroy" and call.plan_artifact not in self._human_approved:
                self._violate("destroy_approval", "destroy requires human approval")
            self._mutations += 1


SCOPE = {"aws_s3_bucket", "aws_instance"}
WORKSPACES = {"demo-dev"}


@pytest.fixture()
def guard() -> Guardrails:
    return Guardrails(scope_resource_types=set(SCOPE), scope_workspaces=set(WORKSPACES), mutation_budget=2)


def call(**overrides) -> ToolCall:
    base = dict(
        tool="terraform_apply",
        resource_type="aws_s3_bucket",
        workspace="demo-dev",
        mutating=True,
        action="apply",
        plan_artifact="s3://plans/p1.out",
        live=True,
    )
    base.update(overrides)
    return ToolCall(**base)


def test_read_within_scope_passes(guard):
    guard.check(call(tool="module_search", mutating=False, action="read", live=False))
    assert sum(guard.violations.values()) == 0


def test_out_of_scope_resource_type_violates(guard):
    with pytest.raises(GuardrailViolation) as exc:
        guard.check(call(resource_type="aws_iam_role"))
    assert exc.value.rule == "scope.resource_type"
    assert guard.violations["scope.resource_type"] == 1


def test_out_of_scope_workspace_violates(guard):
    with pytest.raises(GuardrailViolation) as exc:
        guard.check(call(workspace="payments-prod"))
    assert exc.value.rule == "scope.workspace"


def test_mutation_without_policy_precheck_violates(guard):
    with pytest.raises(GuardrailViolation) as exc:
        guard.check(call())
    assert exc.value.rule == "policy_precheck"


def test_mutation_after_policy_pass_allowed(guard):
    guard.record_policy_pass("s3://plans/p1.out")
    guard.check(call())
    assert sum(guard.violations.values()) == 0


def test_policy_pass_is_per_artifact_not_global(guard):
    guard.record_policy_pass("s3://plans/other.out")
    with pytest.raises(GuardrailViolation) as exc:
        guard.check(call(plan_artifact="s3://plans/p1.out"))
    assert exc.value.rule == "policy_precheck"


def test_mutation_budget_exhaustion_violates(guard):
    guard.record_policy_pass("s3://plans/p1.out")
    guard.check(call())
    guard.check(call())
    with pytest.raises(GuardrailViolation) as exc:
        guard.check(call())
    assert exc.value.rule == "mutation_budget"
    assert guard.violations["mutation_budget"] == 1


def test_destroy_without_human_approval_violates_even_with_policy_pass(guard):
    guard.record_policy_pass("s3://plans/p1.out")
    with pytest.raises(GuardrailViolation) as exc:
        guard.check(call(action="destroy"))
    assert exc.value.rule == "destroy_approval"


def test_destroy_with_human_approval_allowed(guard):
    guard.record_policy_pass("s3://plans/p1.out")
    guard.record_human_approval("s3://plans/p1.out")
    guard.check(call(action="destroy"))
    assert sum(guard.violations.values()) == 0


def test_dry_run_mutation_needs_no_precheck(guard):
    # dry-run default: a simulated apply is allowed without policy pre-check
    guard.check(call(live=False))
    assert sum(guard.violations.values()) == 0


def test_violation_counter_feeds_metric_contract(guard):
    for _ in range(3):
        with pytest.raises(GuardrailViolation):
            guard.check(call(resource_type="aws_iam_role"))
    assert guard.violations == Counter({"scope.resource_type": 3})
