"""TAP multi-agent supervisor (LangGraph supervisor pattern).

Routes an incoming task to domain agents by capability (resolved against the
Agent Registry), delegates over NATS request/reply, and aggregates results
into a single output-contract response.

The orchestrator is itself a LangGraph graph so that routing decisions are
checkpointed and resumable, and so human-in-the-loop interrupts compose with
the domain agents' own approval interrupts.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

import httpx
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

REGISTRY_URL = os.environ.get("TAP_REGISTRY_URL", "http://localhost:8080/v1/agents")
NATS_REQUEST_TIMEOUT_S = float(os.environ.get("TAP_AGENT_REQUEST_TIMEOUT", "60"))
MAX_PARALLEL_DELEGATIONS = int(os.environ.get("TAP_MAX_PARALLEL_DELEGATIONS", "4"))


class Delegation(TypedDict):
    """One routed unit of work."""

    agent: str
    capability: str
    subtask: str
    context: dict[str, Any]
    status: Literal["pending", "dispatched", "completed", "failed", "escalated"]
    result: dict[str, Any] | None


class SupervisorState(TypedDict, total=False):
    """State carried through the supervisor graph."""

    task: str
    context: dict[str, Any]
    tenant_id: str
    trace_id: str
    delegations: list[Delegation]
    results: list[dict[str, Any]]
    errors: list[str]
    requires_approval: bool
    summary: dict[str, Any]


@dataclass
class RegistryClient:
    """Thin client for the Agent Registry capability index."""

    base_url: str = REGISTRY_URL
    _http: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=10.0))

    def find_by_capability(self, capability: str, tenant_id: str) -> list[dict[str, Any]]:
        """Return registered agent manifests advertising ``capability``.

        Contract: GET {base_url}?capability=<cap>&tenant=<id> -> 200
        [{"name", "version", "capabilities", "subject"}].
        """
        resp = self._http.get(
            self.base_url, params={"capability": capability, "tenant": tenant_id}
        )
        resp.raise_for_status()
        return list(resp.json().get("agents", []))


class NatsDelegator:
    """Request/reply delegation to domain agents over NATS JetStream.

    Lazy-connects so unit tests can run without a broker. Subject convention:
    ``agent.<name>.request`` with the agent's output-contract JSON as reply.
    """

    def __init__(self, servers: str | None = None) -> None:
        self._servers = servers or os.environ.get("NATS_URL", "nats://localhost:4222")
        self._nc: Any | None = None

    async def _conn(self) -> Any:
        if self._nc is None:
            import nats  # defer import: optional at test time

            self._nc = await nats.connect(self._servers)
        return self._nc

    async def request(self, agent: str, payload: dict[str, Any]) -> dict[str, Any]:
        nc = await self._conn()
        msg = await nc.request(
            f"agent.{agent}.request",
            json.dumps(payload).encode("utf-8"),
            timeout=NATS_REQUEST_TIMEOUT_S,
        )
        return dict(json.loads(msg.data.decode("utf-8")))


class Orchestrator:
    """Supervisor that decomposes a task and routes it across domain agents."""

    def __init__(
        self,
        registry: RegistryClient | None = None,
        delegator: NatsDelegator | None = None,
    ) -> None:
        self.registry = registry or RegistryClient()
        self.delegator = delegator or NatsDelegator()

    # -- nodes ---------------------------------------------------------------

    def route(self, state: SupervisorState) -> dict[str, Any]:
        """Decompose the task into capability-addressed delegations.

        Capability extraction is intent classification via the AI Gateway;
        here we accept pre-classified capabilities from context or fall back
        to a single ``infrastructure.provision`` delegation.
        """
        capabilities: list[dict[str, str]] = state.get("context", {}).get(
            "capabilities",
            [{"capability": "infrastructure.provision", "subtask": state["task"]}],
        )
        delegations: list[Delegation] = []
        errors = list(state.get("errors", []))
        for item in capabilities:
            matches = self.registry.find_by_capability(
                item["capability"], state.get("tenant_id", "default")
            )
            if not matches:
                errors.append(f"no registered agent for capability {item['capability']}")
                continue
            delegations.append(
                Delegation(
                    agent=matches[0]["name"],
                    capability=item["capability"],
                    subtask=item.get("subtask", state["task"]),
                    context=dict(state.get("context", {})),
                    status="pending",
                    result=None,
                )
            )
        return {"delegations": delegations, "errors": errors}

    async def delegate(self, state: SupervisorState) -> dict[str, Any]:
        """Fan out pending delegations over NATS request/reply."""
        delegations = [dict(d) for d in state.get("delegations", [])]
        results = list(state.get("results", []))
        errors = list(state.get("errors", []))
        requires_approval = bool(state.get("requires_approval", False))
        for d in delegations:
            if d["status"] != "pending":
                continue
            payload = {
                "task": d["subtask"],
                "context": d["context"],
                "trace_id": state.get("trace_id", str(uuid.uuid4())),
                "tenant_id": state.get("tenant_id", "default"),
            }
            try:
                reply = await self.delegator.request(d["agent"], payload)
                d["result"] = reply
                d["status"] = reply.get("status", "completed")  # type: ignore[typeddict-item]
                results.append(reply)
                requires_approval = requires_approval or bool(
                    reply.get("requires_approval")
                )
            except Exception as exc:  # noqa: BLE001 - aggregate, never crash the run
                d["status"] = "failed"
                errors.append(f"{d['agent']}: {exc}")
        return {
            "delegations": delegations,
            "results": results,
            "errors": errors,
            "requires_approval": requires_approval,
        }

    def aggregate(self, state: SupervisorState) -> dict[str, Any]:
        """Merge delegate replies into one output-contract summary."""
        delegations = state.get("delegations", [])
        failed = [d for d in delegations if d["status"] in ("failed", "escalated")]
        summary = {
            "status": "escalated"
            if state.get("requires_approval")
            else ("failed" if failed else "completed"),
            "task": state.get("task", ""),
            "agents": [d["agent"] for d in delegations],
            "results": state.get("results", []),
            "errors": state.get("errors", []),
            "requires_approval": bool(state.get("requires_approval", False)),
        }
        return {"summary": summary}

    @staticmethod
    def _after_route(state: SupervisorState) -> str:
        return "delegate" if state.get("delegations") else "aggregate"

    # -- graph ---------------------------------------------------------------

    def build_graph(
        self, checkpointer: BaseCheckpointSaver | None = None
    ) -> Any:
        """Compile the supervisor graph.

        ``route -> delegate -> aggregate``; routing failures (no matching
        agent) skip straight to aggregation so the caller always gets a
        contract-shaped answer.
        """
        graph = StateGraph(SupervisorState)
        graph.add_node("route", self.route)
        graph.add_node("delegate", self.delegate)
        graph.add_node("aggregate", self.aggregate)
        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route", self._after_route, {"delegate": "delegate", "aggregate": "aggregate"}
        )
        graph.add_edge("delegate", "aggregate")
        graph.add_edge("aggregate", END)
        return graph.compile(checkpointer=checkpointer)
