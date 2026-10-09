"""NetOps agent graph: VPC/VPN/LB/DNS/route design and provisioning."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from tap_sdk import AgentState, BaseAgent, policy_check, terraform_apply, terraform_plan

from .tools import (
    CidrPlanInput,
    DnsRecordManageInput,
    LbConfigureInput,
    SubnetRequest,
    cidr_plan,
    dns_record_manage,
    lb_configure,
)

MAX_ACT_RETRIES = 2
MUTATING_TOOLS = {"dns_record_manage", "lb_configure", "terraform_apply"}
ALWAYS_ESCALATE = ("default route", "0.0.0.0/0", "delete", "prod zone")


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class NetOpsAgent(BaseAgent):
    """Network design + provisioning: CIDR, VPC, VPN, LB, DNS, routing."""

    def analyze(self, state: AgentState) -> dict[str, Any]:
        """Classify intent and flag always-escalate network changes."""
        ctx = dict(state.get("context", {}))
        task = state["task"].lower()
        if "dns" in task or "record" in task:
            ctx["intent"] = "dns"
        elif "load balancer" in task or "lb" in task or "listener" in task:
            ctx["intent"] = "lb"
        else:
            ctx["intent"] = "topology"
        requires_approval = bool(state.get("requires_approval", False))
        if any(marker in task for marker in ALWAYS_ESCALATE):
            requires_approval = True
        errors = list(state.get("errors", []))
        workspace = ctx.get("workspace", "")
        if ctx["intent"] != "dns" and not workspace.startswith("net-"):
            errors.append(f"workspace '{workspace}' outside netops scope allowlist")
        return {"context": ctx, "requires_approval": requires_approval, "errors": errors}

    def plan(self, state: AgentState) -> dict[str, Any]:
        ctx = state.get("context", {})
        intent = ctx.get("intent")
        if intent == "dns":
            steps = ["dns_record_manage"]
        elif intent == "lb":
            steps = ["lb_configure"]
        else:
            steps = ["cidr_plan", "terraform_plan"]
            if not bool(ctx.get("dry_run", True)):
                steps.append("terraform_apply")
        dry_run = bool(ctx.get("dry_run", True))
        mutating = any(s in MUTATING_TOOLS for s in steps)
        requires_approval = bool(state.get("requires_approval", False)) or (mutating and not dry_run)
        return {"plan": steps, "requires_approval": requires_approval}

    def policy_precheck(self, state: AgentState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        results = dict(state.get("results", {}))
        requires_approval = bool(state.get("requires_approval", False))
        if errors:
            return {"results": results}
        try:
            verdict = policy_check(
                {"agent": "netops", "plan": state.get("plan", []), "context": state.get("context", {})}
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
            "cidr_plan": lambda: cidr_plan(
                CidrPlanInput(
                    base_cidr=ctx.get("base_cidr", "10.0.0.0/16"),
                    availability_zones=int(ctx.get("availability_zones", 3)),
                    subnets=[SubnetRequest(**s) for s in ctx.get("subnets", [
                        {"name": "app", "hosts": 250, "tier": "private"},
                        {"name": "public", "hosts": 50, "tier": "public"},
                    ])],
                    existing_cidrs=ctx.get("existing_cidrs", []),
                )
            ),
            "terraform_plan": lambda: terraform_plan(
                {"workspace": ctx.get("workspace", ""), "cidr_plan": results.get("cidr_plan")}
            ),
            "terraform_apply": lambda: terraform_apply(
                {"workspace": ctx.get("workspace", ""), "plan_artifact": results.get("terraform_plan")}
            ),
            "dns_record_manage": lambda: dns_record_manage(
                DnsRecordManageInput(
                    zone=ctx.get("zone", ""),
                    action=ctx.get("action", "upsert"),
                    record_type=ctx.get("record_type", "A"),
                    name=ctx.get("record_name", ""),
                    values=ctx.get("values", []),
                )
            ),
            "lb_configure": lambda: lb_configure(
                LbConfigureInput(
                    workspace=ctx.get("workspace", ""),
                    lb_type=ctx.get("lb_type", "application"),
                    listeners=ctx.get("listeners", []),
                    internal=bool(ctx.get("internal", True)),
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
        """Post-conditions: no CIDR collisions, no failed mutations."""
        ctx = dict(state.get("context", {}))
        errors = list(state.get("errors", []))
        plan_out = state.get("results", {}).get("cidr_plan")
        collisions = getattr(plan_out, "collisions", []) if plan_out is not None else []
        if collisions:
            errors.append(f"CIDR collisions with tenant address space: {collisions}")
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
