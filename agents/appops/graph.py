"""AppOps agent graph: analyze -> plan -> policy_precheck -> (approval) ->
act -> verify -> report, with the standard requires_approval interrupt."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import AgentState, BaseAgent, cost_estimate, policy_check, terraform_plan

from .tools import (
    EnvProvisionInput,
    ReleasePromoteInput,
    TemplateRenderInput,
    env_provision,
    release_promote,
    template_render,
)

MAX_ACT_RETRIES = 2

MUTATING_TOOLS = {"env_provision", "release_promote", "terraform_apply"}


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class AppOpsAgent(BaseAgent):
    """Application lifecycle: env provisioning, releases, self-service."""

    # -- nodes -----------------------------------------------------------

    def analyze(self, state: AgentState) -> dict[str, Any]:
        """Classify the request (provision | promote | selfservice) and
        resolve the target workspace against the scope allowlist."""
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        if "promot" in task or "release" in task:
            intent = "promote"
        elif "provision" in task or "environment" in task or "env" in task:
            intent = "provision"
        else:
            intent = "selfservice"
        ctx["intent"] = intent
        errors = list(state.get("errors", []))
        workspace = ctx.get("workspace", "")
        if not workspace.startswith("app-"):
            errors.append(f"workspace '{workspace}' outside appops scope allowlist")
        return {"context": ctx, "errors": errors}

    def plan(self, state: AgentState) -> dict[str, Any]:
        """Produce the ordered tool-call plan for the classified intent."""
        ctx = state.get("context", {})
        intent = ctx.get("intent", "selfservice")
        if intent == "provision":
            steps = ["template_render", "terraform_plan", "cost_estimate", "env_provision"]
        elif intent == "promote":
            steps = ["release_promote"]
        else:
            steps = ["template_render", "terraform_plan", "cost_estimate"]
        mutating = any(s in MUTATING_TOOLS for s in steps)
        dry_run = bool(ctx.get("dry_run", True))
        return {"plan": steps, "requires_approval": mutating and not dry_run}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        """Evaluate the intended plan against OPA before acting."""
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        requires_approval = bool(state.get("requires_approval", False))
        if errors:  # scope violations already end the run
            return {"requires_approval": False, "results": results}
        try:
            verdict = policy_check(
                {"agent": "appops", "plan": state.get("plan", []), "context": state.get("context", {})}
            )
            results["policy_precheck"] = verdict
            decision = getattr(verdict, "decision", verdict.get("decision") if isinstance(verdict, dict) else "advisory")
            if decision == "deny":
                errors.append("policy pre-check hard deny")
            elif decision == "approval_required":
                requires_approval = True
        except NotImplementedError:
            # Harness mode: no policy service bound; mutations still gate on approval.
            requires_approval = requires_approval or any(
                s in MUTATING_TOOLS for s in state.get("plan", [])
            )
        return {"results": results, "errors": errors, "requires_approval": requires_approval}

    def approval(self, state: AgentState) -> dict[str, Any]:
        """Interrupt point. The orchestrator resumes this thread only after a
        recorded human approval; the node itself just annotates state."""
        actions = list(state.get("actions", []))
        actions.append(
            {"tool": "human_approval", "input_digest": _digest(state.get("plan", [])),
             "mutating": False, "outcome": "ok"}
        )
        return {"actions": actions, "requires_approval": False}

    def act(self, state: AgentState) -> dict[str, Any]:
        """Execute the planned tool calls under guardrails."""
        ctx = state.get("context", {})
        actions = list(state.get("actions", []))
        results = dict(state.get("results", {}))
        errors = list(state.get("errors", []))
        dispatch = {
            "template_render": lambda: template_render(
                TemplateRenderInput(
                    template_id=ctx.get("template_id", "catalog/web-service"),
                    parameters=ctx.get("parameters", {}),
                    workspace=ctx.get("workspace", ""),
                )
            ),
            "terraform_plan": lambda: terraform_plan(
                {"workspace": ctx.get("workspace", ""), "dir": results.get("template_render", {})}
            ),
            "cost_estimate": lambda: cost_estimate({"workspace": ctx.get("workspace", "")}),
            "env_provision": lambda: env_provision(
                EnvProvisionInput(
                    workspace=ctx.get("workspace", ""),
                    environment=ctx.get("environment", "dev"),
                    rendered_dir=str(results.get("template_render", "")),
                    ttl_hours=ctx.get("ttl_hours"),
                )
            ),
            "release_promote": lambda: release_promote(
                ReleasePromoteInput(
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
        """Post-conditions: every planned step has an action record and no
        mutating step errored."""
        ctx = dict(state.get("context", {}))
        errors = list(state.get("errors", []))
        failed = [
            a for a in state.get("actions", [])
            if a.get("outcome") == "error" and a.get("mutating")
        ]
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
        """Emit the output-contract JSON (see core/prompts/system_base.md)."""
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

    # -- routing ---------------------------------------------------------

    @staticmethod
    def _after_precheck(state: AgentState) -> str:
        if any("deny" in e or "scope" in e for e in state.get("errors", [])):
            return "report"
        if state.get("requires_approval"):
            return "approval"
        return "act"

    @staticmethod
    def _after_verify(state: AgentState) -> str:
        return "act" if state.get("context", {}).get("_verify_failed") else "report"

    # -- graph -----------------------------------------------------------

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
        graph.add_conditional_edges(
            "verify", self._after_verify, {"act": "act", "report": "report"}
        )
        graph.add_edge("report", END)
        return graph.compile(checkpointer=checkpointer, interrupt_before=["approval"])
