"""CostOps agent graph: forecasting, budget enforcement, rightsizing,
anomaly detection. Advisory/enforcing agent — mutation_budget is 0; the only
'mutation' it performs is denying over-budget runs via policy verdicts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import AgentState, BaseAgent, cost_estimate, policy_check

from .tools import (
    BudgetCheckInput,
    CostForecastInput,
    RightsizeRecommendInput,
    budget_check,
    cost_forecast,
    rightsize_recommend,
)

MUTATING_TOOLS: set[str] = set()  # costops never mutates infrastructure


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class CostOpsAgent(BaseAgent):
    """FinOps: forecast, budget enforcement, rightsizing, anomaly detection."""

    def analyze(self, state: AgentState) -> dict[str, Any]:
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        if "forecast" in task:
            ctx["intent"] = "forecast"
        elif "budget" in task or "enforce" in task or "over" in task:
            ctx["intent"] = "budget"
        elif "rightsiz" in task or "resize" in task or "saving" in task:
            ctx["intent"] = "rightsize"
        else:
            ctx["intent"] = "anomaly"
        return {"context": ctx}

    def plan(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        intent = ctx.get("intent")
        if intent == "forecast":
            steps = ["cost_forecast"]
        elif intent == "budget":
            steps = ["cost_estimate", "budget_check"]
        elif intent == "rightsize":
            steps = ["rightsize_recommend"]
        else:
            steps = ["cost_forecast", "rightsize_recommend"]  # anomaly baseline inputs
        return {"plan": steps, "requires_approval": False}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        """Read-only agent: precheck validates scope only; nothing mutates."""
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        try:
            verdict = policy_check(
                {"agent": "costops", "plan": state.get("plan", []), "context": state.get("context", {})}
            )
            results["policy_precheck"] = verdict
            decision = getattr(verdict, "decision", verdict.get("decision") if isinstance(verdict, dict) else "advisory")
            if decision == "deny":
                errors.append("policy pre-check hard deny")
        except NotImplementedError:
            pass
        return {"results": results, "errors": errors}

    def act(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        actions = list(state.get("actions", []))
        results = dict(state.get("results", {}))
        errors = list(state.get("errors", []))

        def _proposed_delta() -> float:
            est = results.get("cost_estimate")
            if est is None:
                return float(ctx.get("proposed_delta_usd", 0.0))
            return float(getattr(est, "monthly_delta_usd", ctx.get("proposed_delta_usd", 0.0)))

        dispatch = {
            "cost_forecast": lambda: cost_forecast(
                CostForecastInput(scope=ctx.get("scope", "tenant"))
            ),
            "cost_estimate": lambda: cost_estimate(
                {"workspace": ctx.get("workspace", ""), "run_id": ctx.get("run_id")}
            ),
            "budget_check": lambda: budget_check(
                BudgetCheckInput(
                    budget_id=ctx.get("budget_id", ""),
                    workspace=ctx.get("workspace", ""),
                    proposed_delta_usd=_proposed_delta(),
                )
            ),
            "rightsize_recommend": lambda: rightsize_recommend(
                RightsizeRecommendInput(
                    scope=ctx.get("scope", "tenant"),
                    min_monthly_saving_usd=float(ctx.get("noise_floor_usd", 10.0)),
                )
            ),
        }
        for step in state.get("plan", []):
            fn = dispatch.get(step)
            record = {"tool": step, "input_digest": _digest(ctx), "mutating": False}
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
        """Enforce the budget verdict: over_budget denies the associated run."""
        ctx = dict(state.get("context", {}))
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        check = results.get("budget_check")
        verdict = getattr(check, "verdict", None) if check is not None else None
        if verdict == "over_budget":
            overage = getattr(check, "overage_usd", 0.0)
            errors.append(
                f"budget {ctx.get('budget_id', '')} exceeded by ${overage:.2f}/month: run denied"
            )
            results["enforcement"] = {"verdict": "deny", "reason": "over_budget"}
        elif verdict == "requires_approval":
            results["enforcement"] = {"verdict": "approval_required"}
        ctx["_verify_failed"] = False
        return {"context": ctx, "errors": errors, "results": results}

    def report(self, state: AgentState) -> dict[str, Any]:
        results = dict(state.get("results", {}))
        errors = state.get("errors", [])
        enforcement = results.get("enforcement", {})
        if enforcement.get("verdict") == "deny":
            status = "denied"
        elif enforcement.get("verdict") == "approval_required":
            status = "escalated"
        else:
            status = "failed" if errors else "completed"
        results["report"] = {
            "status": status,
            "task": state.get("task", ""),
            "plan": state.get("plan", []),
            "actions": state.get("actions", []),
            "errors": errors,
            "requires_approval": enforcement.get("verdict") == "approval_required",
            "enforcement": enforcement,
        }
        return {"results": results}

    @staticmethod
    def _after_precheck(state: AgentState) -> str:
        return "report" if any("deny" in e for e in state.get("errors", [])) else "act"

    def build_graph(self, checkpointer: BaseCheckpointSaver | None = None) -> Any:
        graph = StateGraph(AgentState)
        graph.add_node("analyze", self.analyze)
        graph.add_node("plan", self.plan)
        graph.add_node("policy_precheck", self.policy_precheck)
        graph.add_node("act", self.act)
        graph.add_node("verify", self.verify)
        graph.add_node("report", self.report)

        graph.add_edge(START, "analyze")
        graph.add_edge("analyze", "plan")
        graph.add_edge("plan", "policy_precheck")
        graph.add_conditional_edges(
            "policy_precheck", self._after_precheck, {"act": "act", "report": "report"}
        )
        graph.add_edge("act", "verify")
        graph.add_edge("verify", "report")
        graph.add_edge("report", END)
        # No approval interrupt: this agent never mutates infrastructure.
        return graph.compile(checkpointer=checkpointer)
