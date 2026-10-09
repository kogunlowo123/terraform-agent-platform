"""LLMOps agent graph: model endpoints, RAG stacks, prompt registry, evals,
AI governance checks."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import AgentState, BaseAgent, cost_estimate, policy_check

from .tools import (
    EvalRunInput,
    ModelDeployInput,
    PromptPublishInput,
    RagProvisionInput,
    eval_run,
    model_deploy,
    prompt_publish,
    rag_provision,
)

MAX_ACT_RETRIES = 2
MUTATING_TOOLS = {"model_deploy", "rag_provision", "prompt_publish"}


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class LLMOpsAgent(BaseAgent):
    """AI infrastructure: endpoints, RAG, prompt registry, evals, governance."""

    def analyze(self, state: AgentState) -> dict[str, Any]:
        """Classify intent and run the AI governance gate up front."""
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        if "deploy" in task or "endpoint" in task:
            ctx["intent"] = "deploy"
        elif "rag" in task or "vector" in task or "ingest" in task:
            ctx["intent"] = "rag"
        elif "prompt" in task:
            ctx["intent"] = "prompt"
        else:
            ctx["intent"] = "eval"
        errors = list(state.get("errors", []))
        if ctx["intent"] == "deploy" and not ctx.get("governance_review_id"):
            errors.append("ai.governance.unreviewed: model deploy without governance_review_id")
        return {"context": ctx, "errors": errors}

    def plan(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        intent = ctx.get("intent")
        if intent == "deploy":
            steps = ["cost_estimate", "model_deploy", "eval_run"]
        elif intent == "rag":
            steps = ["cost_estimate", "rag_provision"]
        elif intent == "prompt":
            steps = ["prompt_publish"]
        else:
            steps = ["eval_run"]
        dry_run = bool(ctx.get("dry_run", True))
        mutating = any(s in MUTATING_TOOLS for s in steps)
        requires_approval = mutating and not dry_run
        # Prod endpoint changes always escalate.
        if ctx.get("environment") == "prod" and mutating:
            requires_approval = True
        return {"plan": steps, "requires_approval": requires_approval}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        requires_approval = bool(state.get("requires_approval", False))
        if errors:
            return {"results": results}
        try:
            verdict = policy_check(
                {"agent": "llmops", "plan": state.get("plan", []), "context": state.get("context", {})}
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
            "cost_estimate": lambda: cost_estimate(
                {"workspace": ctx.get("workspace", ""), "resource": ctx.get("intent")}
            ),
            "model_deploy": lambda: model_deploy(
                ModelDeployInput(
                    provider=ctx.get("provider", "bedrock"),
                    model_id=ctx.get("model_id", ""),
                    endpoint_name=ctx.get("endpoint_name", ""),
                    workspace=ctx.get("workspace", ""),
                    governance_review_id=ctx.get("governance_review_id", ""),
                    capacity=ctx.get("capacity", {}),
                )
            ),
            "rag_provision": lambda: rag_provision(
                RagProvisionInput(
                    workspace=ctx.get("workspace", ""),
                    vector_db=ctx.get("vector_db", "qdrant"),
                    collection=ctx.get("collection", ""),
                    embedding_model=ctx.get("embedding_model", ""),
                    ingestion_sources=ctx.get("ingestion_sources", []),
                )
            ),
            "prompt_publish": lambda: prompt_publish(
                PromptPublishInput(
                    registry_path=ctx.get("registry_path", ""),
                    template=ctx.get("template", ""),
                    changelog=ctx.get("changelog", state.get("task", "")),
                )
            ),
            "eval_run": lambda: eval_run(
                EvalRunInput(
                    endpoint_name=ctx.get("endpoint_name", ""),
                    suite=ctx.get("suite", "default"),
                    baseline_version=ctx.get("baseline_version"),
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
        """Post-conditions: eval gate for deploys; no failed mutations."""
        ctx = dict(state.get("context", {}))
        errors = list(state.get("errors", []))
        results = state.get("results", {})
        eval_out = results.get("eval_run")
        if (
            ctx.get("intent") == "deploy"
            and eval_out is not None
            and getattr(eval_out, "passed", True) is False
        ):
            errors.append(
                "eval gate failed: " + "; ".join(getattr(eval_out, "regressions", []))
            )
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
        eval_out = results.get("eval_run")
        results["report"] = {
            "status": status,
            "task": state.get("task", ""),
            "plan": state.get("plan", []),
            "actions": state.get("actions", []),
            "errors": errors,
            "requires_approval": bool(state.get("requires_approval", False)),
            "evidence": (
                [f"eval_run:{getattr(eval_out, 'eval_run_id', '')}"] if eval_out is not None else []
            ),
        }
        return {"results": results}

    @staticmethod
    def _after_precheck(state: AgentState) -> str:
        if any("deny" in e or "unreviewed" in e for e in state.get("errors", [])):
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
