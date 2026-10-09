"""SecOps agent graph. Standard flow plus a `severity_gate` node after `act`:
CRITICAL findings always escalate to a human and are never auto-remediated."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import AgentState, BaseAgent, policy_check, scan_checkov, scan_tfsec, scan_trivy

from .tools import FindingTriageInput, RemediationPrInput, finding_triage, remediation_pr

MAX_ACT_RETRIES = 1
MUTATING_TOOLS = {"remediation_pr"}


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class SecOpsAgent(BaseAgent):
    """Scan orchestration, OPA validation, finding triage, remediation PRs."""

    def analyze(self, state: AgentState) -> dict[str, Any]:
        """Determine scan targets and whether remediation PRs are requested."""
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        ctx["remediate"] = "remediat" in task or "fix" in task
        ctx.setdefault("scanners", ["checkov", "tfsec", "trivy"])
        return {"context": ctx}

    def plan(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        steps = [f"scan_{s}" for s in ctx.get("scanners", [])]
        steps += ["policy_check", "finding_triage"]
        if ctx.get("remediate"):
            steps.append("remediation_pr")
        dry_run = bool(ctx.get("dry_run", True))
        mutating = any(s in MUTATING_TOOLS for s in steps)
        return {"plan": steps, "requires_approval": mutating and not dry_run}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        requires_approval = bool(state.get("requires_approval", False))
        try:
            verdict = policy_check(
                {"agent": "secops", "plan": state.get("plan", []), "context": state.get("context", {})}
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
        target = {"workspace": ctx.get("workspace", ""), "dir": ctx.get("dir", ".")}

        def _triaged_remediable() -> list[Any]:
            triage = results.get("finding_triage")
            triaged = getattr(triage, "triaged", []) if triage is not None else []
            return [t for t in triaged if getattr(t, "disposition", "") == "remediate"]

        dispatch = {
            "scan_checkov": lambda: scan_checkov(target),
            "scan_tfsec": lambda: scan_tfsec(target),
            "scan_trivy": lambda: scan_trivy(target),
            "policy_check": lambda: policy_check({"agent": "secops", "target": target}),
            "finding_triage": lambda: finding_triage(
                FindingTriageInput(
                    findings=[
                        f
                        for key in ("scan_checkov", "scan_tfsec", "scan_trivy")
                        for f in getattr(results.get(key), "findings", []) or []
                    ],
                    workspace=ctx.get("workspace", ""),
                )
            ),
            "remediation_pr": lambda: remediation_pr(
                RemediationPrInput(
                    repo=ctx.get("repo", ""),
                    workspace=ctx.get("workspace", ""),
                    findings=_triaged_remediable(),
                )
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

    def severity_gate(self, state: AgentState) -> dict[str, Any]:
        """Domain-specific gate: CRITICAL findings always escalate to a human.

        Runs after `act` so the gate sees real triage output. Any critical
        forces requires_approval and strips criticals from auto-remediation.
        """
        results = dict(state.get("results", {}))
        triage = results.get("finding_triage")
        criticals = int(getattr(triage, "critical_count", 0)) if triage is not None else 0
        requires_approval = bool(state.get("requires_approval", False))
        if criticals > 0:
            requires_approval = True
            results["severity_gate"] = {
                "verdict": "escalate",
                "critical_count": criticals,
                "reason": "CRITICAL findings are never auto-remediated",
            }
        else:
            results["severity_gate"] = {"verdict": "pass", "critical_count": 0}
        return {"results": results, "requires_approval": requires_approval}

    def verify(self, state: AgentState) -> dict[str, Any]:
        ctx = dict(state.get("context", {}))
        errors = list(state.get("errors", []))
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
        results = dict(state.get("results", {}))
        gate = results.get("severity_gate", {})
        status = "failed" if errors else "completed"
        if state.get("requires_approval") or gate.get("verdict") == "escalate":
            status = "escalated"
        results["report"] = {
            "status": status,
            "task": state.get("task", ""),
            "plan": state.get("plan", []),
            "actions": state.get("actions", []),
            "errors": errors,
            "requires_approval": bool(state.get("requires_approval", False)),
            "severity_gate": gate,
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
        graph.add_node("severity_gate", self.severity_gate)
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
        graph.add_edge("act", "severity_gate")
        graph.add_edge("severity_gate", "verify")
        graph.add_conditional_edges("verify", self._after_verify, {"act": "act", "report": "report"})
        graph.add_edge("report", END)
        return graph.compile(checkpointer=checkpointer, interrupt_before=["approval"])
