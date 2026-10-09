"""Guardrails: the agent containment layer (ARCHITECTURE.md §12).

Enforced on *every mutating edge* of an agent graph:
* scope allowlists (resource types, regions);
* mutation budget (max resources changed per run);
* mandatory ``policy_check`` before any mutating tool call;
* dry-run by default.
"""

from __future__ import annotations

from typing import Any

from tap_sdk.manifest import GuardrailsConfig

#: Platform tools that mutate infrastructure and therefore pass every gate.
MUTATING_TOOLS: frozenset[str] = frozenset(
    {"terraform_apply", "terraform_destroy"}
)


class GuardrailViolation(Exception):
    """Raised when an agent action violates its containment limits."""

    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(f"guardrail violation [{rule}]: {detail}")


class Guardrails:
    """Runtime enforcement of a manifest's GuardrailsConfig."""

    def __init__(self, config: GuardrailsConfig) -> None:
        self.config = config
        self._resources_changed = 0
        self._policy_checked = False

    @classmethod
    def from_config(cls, config: GuardrailsConfig) -> "Guardrails":
        """Build from the manifest's guardrails section."""
        return cls(config)

    @property
    def dry_run(self) -> bool:
        """Whether mutating tools should run in dry-run mode (default True)."""
        return self.config.dry_run_default

    def record_policy_check(self, allowed: bool) -> None:
        """Mark that a policy_check ran for the pending mutation."""
        self._policy_checked = allowed

    def check_scope(self, resource_type: str, region: str | None = None) -> None:
        """Validate a resource against the allowlists; raise on violation."""
        allowed_types = self.config.allowed_resource_types
        if resource_type not in allowed_types:
            raise GuardrailViolation(
                "scope.resource_type",
                f"{resource_type!r} is not in the agent's allowlist {allowed_types}",
            )
        if region is not None and self.config.allowed_regions and region not in self.config.allowed_regions:
            raise GuardrailViolation(
                "scope.region",
                f"{region!r} is not in the agent's allowed regions {self.config.allowed_regions}",
            )

    def check_mutation_budget(self, resources_in_change: int) -> None:
        """Validate the cumulative mutation budget for this run."""
        budget = self.config.max_resources_changed_per_run
        if self._resources_changed + resources_in_change > budget:
            raise GuardrailViolation(
                "mutation_budget",
                f"change of {resources_in_change} resources exceeds remaining budget "
                f"({budget - self._resources_changed} of {budget})",
            )
        self._resources_changed += resources_in_change

    def check_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Gate every tool invocation; mutating tools require a prior policy_check.

        Called by the ``@tool`` wrapper before dispatch. Raises
        :class:`GuardrailViolation` when:
        * the tool mutates and ``require_policy_check_before_mutation`` is set
          but no passing policy_check was recorded for this step;
        * the tool mutates and dry-run is in force without an explicit,
          approved override (``arguments["approval_token"]``).
        """
        if tool_name not in MUTATING_TOOLS:
            return
        if self.config.require_policy_check_before_mutation and not self._policy_checked:
            raise GuardrailViolation(
                "policy_precheck",
                f"{tool_name} called without a passing policy_check for this change",
            )
        if self.dry_run and not arguments.get("approval_token"):
            raise GuardrailViolation(
                "dry_run",
                f"{tool_name} blocked: dry_run default is on and no approval_token supplied",
            )
        # One policy check authorizes exactly one mutation.
        self._policy_checked = False
