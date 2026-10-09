"""Infrastructure agent graph: generate -> validate -> plan -> policy ->
(approval) -> apply -> verify -> report."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import (
    AgentState,
    BaseAgent,
    cost_estimate,
    module_search,
    policy_check,
    scan_checkov,
    scan_tfsec,
    terraform_apply,
    terraform_plan,
)

from .tools import (
    HclGenerateInput,
    ModuleSelectInput,
    TerraformValidateInput,
    hcl_generate,
    module_select,
    terraform_validate,
)

MAX_ACT_RETRIES = 2
MUTATING_TOOLS = {"terraform_apply"}
STATE_SURGERY_MARKERS = ("import", "state mv", "state rm")


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class InfrastructureAgent(BaseAgent):
    """Terraform generation, module selection, provisioning, validation."""

    def analyze(self, state: AgentState) -> dict[str, Any]:
        """Classify intent and flag state surgery (always escalates)."""
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        ctx["intent"] = "provision" if ("apply" in task or "provision" in task) else "generate"
        requires_approval = bool(state.get("requires_approval", False))
        if any(marker in task for marker in STATE_SURGERY_MARKERS):
            ctx["state_surgery"] = True
            requires_approval = True
        return {"context": ctx, "requires_approval": requires_approval}

    def plan(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        steps = [
            "module_select",
            "hcl_generate",
            "terraform_validate",
            "scan_checkov",
            "scan_tfsec",
            "terraform_plan",
            "cost_estimate",
        ]
        if ctx.get("intent") == "provision":
            steps.append("terraform_apply")
        dry_run = bool(ctx.get("dry_run", True))
        mutating = any(s in MUTATING_TOOLS for s in steps)
        requires_approval = bool(state.get("requires_approval", False)) or (mutating and not dry_run)
        return {"plan": steps, "requires_approval": requires_approval}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        requires_approval = bool(state.get("requires_approval", False))
        try:
            verdict = policy_check(
                {"agent": "infrastructure", "plan": state.get("plan", []), "context": state.get("context", {})}
            )
            results["policy_precheck"] = verdict
            decision = getattr(verdict, "decision", verdict.get("decision") if isinstance(verdict, dict) else "advisory")
            if decision == "deny":
                errors.append("policy pre-check hard deny")
            elif decision == "approval_required":
                requires_approval = True
        except NotImplementedError:
            requires_approval = requires_approval or any(
                s in MUTATING_TOOLS for s in state.get("plan", [])
            )
        return {"results": results, "errors": errors, "requires_approval": requires_approval}

    def approval(self, state: AgentState) -> dict[str, Any]:
        actions = list(state.get("actions", []))
        actions.append(
            {"tool": "human_approval", "input_digest": _digest(state.get("plan", [])),
             "mutating": False, "outcome": "ok"}
        )
        return {"actions": actions, "requires_approval": False}

    def act(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        actions = list(state.get("actions", []))
        results = dict(state.get("results", {}))
        errors = list(state.get("errors", []))

        def _gen_dir() -> str:
            out = results.get("hcl_generate")
            return getattr(out, "dir", "") if out is not None else ""

        dispatch = {
            "module_select": lambda: module_select(
                ModuleSelectInput(
                    requirement=state.get("task", ""),
                    provider=ctx.get("provider", "aws"),
                    constraints=ctx.get("constraints", {}),
                )
            ),
            "hcl_generate": lambda: hcl_generate(
                HclGenerateInput(
                    workspace=ctx.get("workspace", ""),
                    provider=ctx.get("provider", "aws"),
                    intent=state.get("task", ""),
                    modules=[
                        getattr(getattr(results.get("module_select"), "selected", None), "module_id", "")
                    ]
                    if results.get("module_select")
                    else [],
                    variables=ctx.get("variables", {}),
                )
            ),
            "terraform_validate": lambda: terraform_validate(
                TerraformValidateInput(dir=_gen_dir(), workspace=ctx.get("workspace", ""))
            ),
            "scan_checkov": lambda: scan_checkov({"dir": _gen_dir()}),
            "scan_tfsec": lambda: scan_tfsec({"dir": _gen_dir()}),
            "terraform_plan": lambda: terraform_plan(
                {"workspace": ctx.get("workspace", ""), "dir": _gen_dir()}
            ),
            "cost_estimate": lambda: cost_estimate(
                {"workspace": ctx.get("workspace", ""), "plan": results.get("terraform_plan")}
            ),
            "terraform_apply": lambda: terraform_apply(
                # Apply only the previously evaluated plan artifact (no TOCTOU).
                {"workspace": ctx.get("workspace", ""), "plan_artifact": results.get("terraform_plan")}
            ),
        }
        for step in state.get("plan", []):
            fn = dispatch.get(step)
            record = {"tool": step, "input_digest": _digest(ctx), "mutating": step in MUTATING_TOOLS}
            if fn is None:
                record["outcome"] = "skipped"
            elif step == "terraform_apply" and results.get("terraform_plan") is None:
                record["outcome"] = "skipped"
                errors.append("terraform_apply skipped: no evaluated plan artifact")
            else:
                try:
                    results[step] = fn()
                    record["outcome"] = "ok"
                except NotImplementedError as exc:
                    record["outcome"] = "skipped"
                    results[step] = {"stub": str(exc)}
                except Exception as exc:  # noqa: BLE001
                    record["outcome"] = "error"
                    errors.append(f"{step}: {exc}")
            actions.append(record)
        return {"actions": actions, "results": results, "errors": errors}

    def verify(self, state: AgentState) -> dict[str, Any]:
        """Post-conditions: validation passed and no mutating step errored;
        post-apply this is where the drift re-check hooks in."""
        ctx = dict(state.get("context", {}))
        errors = list(state.get("errors", []))
        validate_out = state.get("results", {}).get("terraform_validate")
        if validate_out is not None and getattr(validate_out, "valid", True) is False:
            errors.append("terraform validate failed: " + "; ".join(getattr(validate_out, "diagnostics", [])))
        failed = [a for a in state.get("actions", []) if a.get("outcome") == "error" and a.get("mutating")]
        retries = int(ctx.get("_act_retries", 0))
        if failed and retries < MAX_ACT_RETRIES:
            ctx["_act_retries"] = retries + 1
            ctx["_verify_failed"] = True
        else:
            ctx["_verify_failed"] = False
            if failed:
                errors.append("mutating steps failed after retry budget")
        return {"context": ctx, "errors": errors}

    def report(self, state: AgentState) -> dict[str, Any]:
        errors = state.get("errors", [])
        status = "failed" if errors else "completed"
        if state.get("requires_approval"):
            status = "escalated"
        results = dict(state.get("results", {}))
        results["report"] = {
            "status": status,
            "task": state.get("task", ""),
            "plan": state.get("plan", []),
            "actions": state.get("actions", []),
            "errors": errors,
            "requires_approval": bool(state.get("requires_approval", False)),
        }
        return {"results": results}

    @staticmethod
    def _after_precheck(state: AgentState) -> str:
        if any("deny" in e for e in state.get("errors", [])):
            return "report"
        return "approval" if state.get("requires_approval") else "act"

    @staticmethod
    def _after_verify(state: AgentState) -> str:
        return "act" if state.get("context", {}).get("_verify_failed") else "report"

    def build_graph(self, checkpointer: BaseCheckpointSaver | None = None) -> Any:
        graph = StateGraph(AgentState)
        graph.add_node("analyze", self.analyze)
        graph.add_node("plan", self.plan)
        graph.add_node("policy_precheck", self.policy_precheck)
        graph.add_node("approval", self.approval)
        graph.add_node("act", self.act)
        graph.add_node("verify", self.verify)
        graph.add_node("report", self.report)

        graph.add_edge(START, "analyze")
        graph.add_edge("analyze", "plan")
        graph.add_edge("plan", "policy_precheck")
        graph.add_conditional_edges(
            "policy_precheck", self._after_precheck,
            {"approval": "approval", "act": "act", "report": "report"},
        )
        graph.add_edge("approval", "act")
        graph.add_edge("act", "verify")
        graph.add_conditional_edges("verify", self._after_verify, {"act": "act", "report": "report"})
        graph.add_edge("report", END)
        return graph.compile(checkpointer=checkpointer, interrupt_before=["approval"])
