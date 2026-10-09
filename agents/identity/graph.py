"""Identity agent graph. Guardrail override: EVERY mutation requires human
approval — there is no auto-apply path in this domain, regardless of policy
result or dry_run flags."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import AgentState, BaseAgent, policy_check, terraform_apply, terraform_plan

from .tools import (
    AccessReviewInput,
    EntitlementDiffInput,
    IamPolicyGenerateInput,
    access_review,
    entitlement_diff,
    iam_policy_generate,
)

MAX_ACT_RETRIES = 1
MUTATING_TOOLS = {"terraform_apply"}


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class IdentityAgent(BaseAgent):
    """IAM policy generation, least-privilege analysis, access reviews,
    RBAC sync, federation setup."""

    def analyze(self, state: AgentState) -> dict[str, Any]:
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        if "review" in task:
            ctx["intent"] = "review"
        elif "diff" in task or "least" in task or "unused" in task:
            ctx["intent"] = "diff"
        elif "federat" in task or "rbac" in task or "sync" in task or "attach" in task or "apply" in task:
            ctx["intent"] = "mutate"
        else:
            ctx["intent"] = "generate"
        return {"context": ctx}

    def plan(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        intent = ctx.get("intent")
        if intent == "review":
            steps = ["access_review"]
        elif intent == "diff":
            steps = ["entitlement_diff"]
        elif intent == "mutate":
            steps = ["entitlement_diff", "iam_policy_generate", "terraform_plan", "terraform_apply"]
        else:
            steps = ["entitlement_diff", "iam_policy_generate"]
        # Guardrail override: ANY mutating step forces approval, always.
        # dry_run and policy verdicts cannot relax this in the identity domain.
        requires_approval = any(s in MUTATING_TOOLS for s in steps)
        return {"plan": steps, "requires_approval": requires_approval}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        # Approval requirement is sticky: never downgraded by policy result.
        requires_approval = bool(state.get("requires_approval", False))
        try:
            verdict = policy_check(
                {"agent": "identity", "plan": state.get("plan", []), "context": state.get("context", {})}
            )
            results["policy_precheck"] = verdict
            decision = getattr(verdict, "decision", verdict.get("decision") if isinstance(verdict, dict) else "advisory")
            if decision == "deny":
                errors.append("policy pre-check hard deny")
        except NotImplementedError:
            pass
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

        def _required_access() -> list[str]:
            diff = results.get("entitlement_diff")
            used = getattr(diff, "used", None) if diff is not None else None
            missing = getattr(diff, "missing", []) if diff is not None else []
            return (used or ctx.get("required_access", [])) + list(missing)

        dispatch = {
            "entitlement_diff": lambda: entitlement_diff(
                EntitlementDiffInput(
                    principal=ctx.get("principal", ""),
                    provider=ctx.get("provider", "aws"),
                )
            ),
            "iam_policy_generate": lambda: iam_policy_generate(
                IamPolicyGenerateInput(
                    provider=ctx.get("provider", "aws"),
                    principal=ctx.get("principal", ""),
                    required_access=_required_access(),
                )
            ),
            "access_review": lambda: access_review(
                AccessReviewInput(scope=ctx.get("scope", ctx.get("workspace", "")))
            ),
            "terraform_plan": lambda: terraform_plan(
                {"workspace": ctx.get("workspace", ""),
                 "policy_document": getattr(results.get("iam_policy_generate"), "policy_document", None)}
            ),
            "terraform_apply": lambda: terraform_apply(
                {"workspace": ctx.get("workspace", ""), "plan_artifact": results.get("terraform_plan")}
            ),
        }
        for step in state.get("plan", []):
            fn = dispatch.get(step)
            record = {"tool": step, "input_digest": _digest(ctx), "mutating": step in MUTATING_TOOLS}
            if fn is None:
                record["outcome"] = "skipped"
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
        """Post-conditions: generated policies carry no unacknowledged risky
        constructs; no failed mutations."""
        ctx = dict(state.get("context", {}))
        errors = list(state.get("errors", []))
        gen = state.get("results", {}).get("iam_policy_generate")
        warnings = list(getattr(gen, "warnings", [])) if gen is not None else []
        if warnings:
            # Risky constructs are reported as critical, even when requested.
            ctx["critical_policy_warnings"] = warnings
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
            "critical_policy_warnings": state.get("context", {}).get(
                "critical_policy_warnings", []
            ),
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
