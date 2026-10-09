"""BaseAgent: the abstract LangGraph agent every TAP agent derives from.

Subclasses implement :meth:`BaseAgent.build_graph` returning a LangGraph
``StateGraph`` over :class:`AgentState`; :meth:`BaseAgent.run` wires telemetry
and checkpointing around graph execution (plan -> act -> verify -> report).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict

from langgraph.graph import StateGraph
from opentelemetry import trace

from tap_sdk.guardrails import Guardrails
from tap_sdk.manifest import AgentManifest

_tracer = trace.get_tracer("tap_sdk.agent")


class AgentState(TypedDict, total=False):
    """Standard state flowing through every TAP agent graph.

    Keys:
        task: the natural-language or structured task the agent was given.
        context: retrieved memory + workspace facts assembled before planning.
        plan: the agent's structured plan (list of intended actions).
        actions: tool invocations performed so far (name, args, started_at).
        results: tool results keyed by action index.
        errors: accumulated error strings (non-fatal unless terminal).
        requires_approval: set when a mutating step needs a human gate.
    """

    task: str
    context: dict[str, Any]
    plan: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    results: dict[str, Any]
    errors: list[str]
    requires_approval: bool


class BaseAgent(ABC):
    """Abstract TAP agent: manifest + graph + governed run entry point."""

    def __init__(self, manifest: AgentManifest, guardrails: Guardrails | None = None) -> None:
        self.manifest = manifest
        self.guardrails = guardrails or Guardrails.from_config(manifest.guardrails)
        self._compiled_graph: Any | None = None

    @classmethod
    def from_manifest(cls, path: str, guardrails: Guardrails | None = None) -> "BaseAgent":
        """Instantiate the agent from an ``agent.yaml`` manifest file."""
        return cls(AgentManifest.from_yaml(path), guardrails=guardrails)

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Construct the agent's LangGraph StateGraph over :class:`AgentState`.

        Convention: nodes ``plan`` -> ``act`` -> ``verify`` -> ``report`` with
        a conditional edge from ``verify`` back to ``plan`` on recoverable
        failure, and an interrupt before any node that mutates infrastructure.
        """

    async def run(
        self,
        task: str,
        *,
        context: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> AgentState:
        """Execute the agent graph with telemetry and checkpointing.

        Contract: open an OTel span named ``agent.run`` carrying agent
        name/version/domain; compile the graph once with a checkpointer bound
        to the platform's episodic store (resume via ``execution_id``);
        ``ainvoke`` the graph with the initial state; persist the terminal
        checkpoint; return the final :class:`AgentState`.
        """
        with _tracer.start_as_current_span("agent.run") as span:
            span.set_attribute("tap.agent.name", self.manifest.name)
            span.set_attribute("tap.agent.version", self.manifest.version)
            span.set_attribute("tap.agent.domain", self.manifest.domain.value)
            raise NotImplementedError(
                "compile graph with platform checkpointer, ainvoke with initial "
                "AgentState(task=..., context=...), persist final checkpoint"
            )

    def initial_state(self, task: str, context: dict[str, Any] | None = None) -> AgentState:
        """Build the canonical initial state for a task."""
        return AgentState(
            task=task,
            context=context or {},
            plan=[],
            actions=[],
            results={},
            errors=[],
            requires_approval=False,
        )
