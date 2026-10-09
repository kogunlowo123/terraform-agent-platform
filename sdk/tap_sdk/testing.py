"""AgentTestHarness: run an agent graph with mocked tools and assert on state.

Typical use::

    harness = AgentTestHarness(MyAgent(manifest))
    harness.mock_tool("terraform_plan", returns={"status": "succeeded", ...})
    final = await harness.run("create a dev VPC")
    harness.assert_tool_called("policy_check")
    harness.assert_state(final, requires_approval=False)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tap_sdk.agent import AgentState, BaseAgent


@dataclass
class ToolCallRecord:
    """One recorded (mocked) tool invocation."""

    name: str
    arguments: dict[str, Any]
    result: Any = None
    error: str | None = None


@dataclass
class MockedTool:
    """A mocked tool: canned return value or raised exception."""

    name: str
    returns: Any = None
    raises: Exception | None = None
    calls: list[ToolCallRecord] = field(default_factory=list)


class AgentTestHarness:
    """Deterministic test runner for TAP agents (no network, no LLM)."""

    def __init__(self, agent: BaseAgent) -> None:
        self.agent = agent
        self._mocks: dict[str, MockedTool] = {}
        self._transitions: list[AgentState] = []

    def mock_tool(self, name: str, *, returns: Any = None, raises: Exception | None = None) -> None:
        """Replace a tool with a canned result (or exception) for this run."""
        self._mocks[name] = MockedTool(name=name, returns=returns, raises=raises)

    async def run(self, task: str, *, context: dict[str, Any] | None = None) -> AgentState:
        """Compile and invoke the agent graph with mocked tools.

        Contract: compile ``agent.build_graph()`` with an in-memory
        checkpointer; intercept every tool node so calls resolve against
        ``self._mocks`` (unmocked tool -> AssertionError); record each state
        transition into ``self._transitions``; return the final state.
        """
        raise NotImplementedError("compile graph with tool interception + in-memory checkpointer")

    # --- assertions ---------------------------------------------------------

    @property
    def transitions(self) -> list[AgentState]:
        """Every intermediate state observed during the run, in order."""
        return list(self._transitions)

    def tool_calls(self, name: str) -> list[ToolCallRecord]:
        """All recorded invocations of one tool."""
        mock = self._mocks.get(name)
        return list(mock.calls) if mock else []

    def assert_tool_called(self, name: str, *, times: int | None = None) -> None:
        """Fail unless the tool was called (optionally exactly ``times``)."""
        calls = self.tool_calls(name)
        if not calls:
            raise AssertionError(f"expected tool {name!r} to be called, but it was not")
        if times is not None and len(calls) != times:
            raise AssertionError(f"expected {times} calls to {name!r}, got {len(calls)}")

    def assert_tool_not_called(self, name: str) -> None:
        """Fail if the tool was invoked."""
        if self.tool_calls(name):
            raise AssertionError(f"expected tool {name!r} not to be called")

    @staticmethod
    def assert_state(state: AgentState, **expected: Any) -> None:
        """Fail unless each expected key/value matches the state."""
        for key, value in expected.items():
            actual = state.get(key)  # type: ignore[union-attr]
            if actual != value:
                raise AssertionError(f"state[{key!r}] == {actual!r}, expected {value!r}")
