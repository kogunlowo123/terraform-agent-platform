"""DevOps agent graph: pipeline generation, GitOps commits, promotion PRs."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import AgentState, BaseAgent, policy_check, scan_checkov

from .tools import (
    GitopsCommitInput,
    PipelineGenerateInput,
    PromotionPrInput,
    gitops_commit,
    pipeline_generate,
    promotion_pr,
)

MAX_ACT_RETRIES = 2
MUTATING_TOOLS = {"gitops_commit", "promotion_pr"}


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class DevOpsAgent(BaseAgent):
    """CI/CD + GitOps: pipelines, ArgoCD manifests, promotion PRs."""

    def analyze(self, state: AgentState) -> dict[str, Any]:
        """Classify intent (pipeline | gitops | promotion) and check repo scope."""
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        if "promot" in task:
            ctx["intent"] = "promotion"
        elif "pipeline" in task or "ci" in task or "workflow" in task:
            ctx["intent"] = "pipeline"
        else:
            ctx["intent"] = "gitops"
        errors = list(state.get("errors", []))
        repo = ctx.get("repo", "")
        if not (repo.startswith("platform/") or repo.startswith("apps/")):
            errors.append(f"repo '{repo}' outside devops scope allowlist")
        return {"context": ctx, "errors": errors}

    def plan(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        intent = ctx.get("intent")
        if intent == "pipeline":
            steps = ["pipeline_generate", "scan_checkov", "gitops_commit"]
        elif intent == "promotion":
            steps = ["promotion_pr"]
        else:
            steps = ["gitops_commit"]
        dry_run = bool(ctx.get("dry_run", True))
        mutating = any(s in MUTATING_TOOLS for s in steps)
        return {"plan": steps, "requires_approval": mutating and not dry_run}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        requires_approval = bool(state.get("requires_approval", False))
        if errors:
            return {"results": results}
        try:
            verdict = policy_check(
                {"agent": "devops", "plan": state.get("plan", []), "context": state.get("context", {})}
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
        dispatch = {
            "pipeline_generate": lambda: pipeline_generate(
                PipelineGenerateInput(
                    repo=ctx.get("repo", ""),
                    platform=ctx.get("platform", "github_actions"),
                    stack=ctx.get("stack", "python-fastapi"),
                )
            ),
            "scan_checkov": lambda: scan_checkov({"files": results.get("pipeline_generate", {})}),
            "gitops_commit": lambda: gitops_commit(
                GitopsCommitInput(
                    repo=ctx.get("repo", ""),
                    branch=ctx.get("branch", "tap/devops-change"),
                    files=getattr(results.get("pipeline_generate"), "files", ctx.get("files", {})),
                    message=ctx.get("message", "chore(tap): generated pipeline"),
                )
            ),
            "promotion_pr": lambda: promotion_pr(
                PromotionPrInput(
                    repo=ctx.get("repo", ""),
                    application=ctx.get("application", ""),
                    artifact_digest=ctx.get("artifact_digest", ""),
                    from_environment=ctx.get("from_environment", "dev"),
                    to_environment=ctx.get("to_environment", "staging"),
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
        if any("deny" in e or "scope" in e for e in state.get("errors", [])):
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
