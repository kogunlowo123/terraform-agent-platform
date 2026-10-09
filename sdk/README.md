# TAP SDK — Build an Agent

The TAP SDK turns a LangGraph graph into a governed platform agent: a typed
manifest (`agent.yaml`), platform tools, three-tier memory, and guardrails
that gate every mutating step.

```bash
pip install -e ./sdk
```

## Concepts in 30 seconds

| Piece | What it is |
|---|---|
| `AgentManifest` | Validated `agent.yaml`: name, semver, domain, capabilities, tools, memory, guardrails, model budget |
| `BaseAgent` | ABC — you implement `build_graph()`, the SDK runs it with OTel + checkpointing |
| `AgentState` | Standard TypedDict flowing through the graph: `task, context, plan, actions, results, errors, requires_approval` |
| `@tool` | Decorator turning typed async functions into LLM/MCP tool definitions |
| `Guardrails` | Scope allowlists, mutation budget, mandatory `policy_check`, dry-run default — raises `GuardrailViolation` |
| `MemoryClient` | working (TTL) / episodic (history) / semantic (vector) memory via the platform API |
| `AgentTestHarness` | Run graphs with mocked tools; assert on calls and state transitions |

## Walkthrough: a VPC provisioning agent

### 1. Write the manifest — `agent.yaml`

```yaml
name: vpc-provisioner
version: 0.1.0
domain: netops
description: Provisions baseline VPCs from approved modules.
capabilities:
  - provision_vpc
required_tools:
  - module_search
  - terraform_plan
  - policy_check
  - cost_estimate
  - terraform_apply
memory:
  working_ttl_seconds: 1800
  semantic_enabled: true
guardrails:
  allowed_resource_types:
    - aws_vpc
    - aws_subnet
    - aws_route_table
    - aws_internet_gateway
  allowed_regions: [eu-west-1, eu-central-1]
  max_resources_changed_per_run: 25
  require_policy_check_before_mutation: true
  dry_run_default: true
model:
  provider: anthropic
  model: claude-sonnet-4-5
  max_tokens: 8192
  budget_usd_per_run: 2.50
```

### 2. Implement the agent

```python
# vpc_agent.py
from langgraph.graph import END, StateGraph

from tap_sdk import AgentManifest, AgentState, BaseAgent
from tap_sdk.tools import cost_estimate, module_search, policy_check, terraform_apply, terraform_plan


class VpcProvisionerAgent(BaseAgent):
    """Plans a VPC from approved modules; applies only behind an approval token."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def plan(state: AgentState) -> AgentState:
            modules = await module_search("baseline vpc", provider="aws")
            state["plan"] = [{"step": "terraform_plan", "module": modules[0]["source"]}]
            return state

        async def act(state: AgentState) -> AgentState:
            run = await terraform_plan(state["context"]["workspace_id"])
            state["results"]["plan_run"] = run
            return state

        async def verify(state: AgentState) -> AgentState:
            decision = await policy_check(
                state["context"]["workspace_id"],
                state["results"]["plan_run"].get("plan_json", {}),
            )
            state["requires_approval"] = not decision["allowed"]
            return state

        async def report(state: AgentState) -> AgentState:
            estimate = await cost_estimate(state["results"]["plan_run"]["id"])
            state["results"]["cost"] = estimate
            return state

        graph.add_node("plan", plan)
        graph.add_node("act", act)
        graph.add_node("verify", verify)
        graph.add_node("report", report)
        graph.set_entry_point("plan")
        graph.add_edge("plan", "act")
        graph.add_edge("act", "verify")
        graph.add_edge("verify", "report")
        graph.add_edge("report", END)
        return graph


def load() -> VpcProvisionerAgent:
    return VpcProvisionerAgent(AgentManifest.from_yaml("agent.yaml"))
```

The apply path is intentionally absent from the happy graph: `terraform_apply`
is a mutating tool, so Guardrails blocks it unless a passing `policy_check`
preceded it **and** an `approval_token` (from the platform's human approval
gate) is supplied — dry-run is the default posture.

### 3. Test it

```python
# test_vpc_agent.py
import pytest

from tap_sdk.testing import AgentTestHarness
from vpc_agent import load


@pytest.mark.asyncio
async def test_plans_and_checks_policy() -> None:
    harness = AgentTestHarness(load())
    harness.mock_tool("module_search", returns=[{"source": "tap/vpc/aws", "version": "2.1.0"}])
    harness.mock_tool("terraform_plan", returns={"id": "run-1", "status": "succeeded", "plan_json": {}})
    harness.mock_tool("policy_check", returns={"allowed": True, "violations": []})
    harness.mock_tool("cost_estimate", returns={"monthly_delta_usd": 12.40})

    final = await harness.run("create a dev vpc", context={"workspace_id": "ws-1"})

    harness.assert_tool_called("policy_check", times=1)
    harness.assert_tool_not_called("terraform_apply")
    harness.assert_state(final, requires_approval=False)
```

### 4. Register and publish

```bash
# register with your tenant's registry
curl -X POST https://tap.example.com/v1/agents \
  -H "Authorization: Bearer $TOKEN" -H "Idempotency-Key: $(uuidgen)" \
  -d @<(python -c "import json,yaml;print(json.dumps({
        'name':'vpc-provisioner','version':'0.1.0','domain':'netops',
        'manifest': yaml.safe_load(open('agent.yaml'))}))")

# or package as a signed OCI artifact for the marketplace
cosign sign ghcr.io/you/vpc-provisioner:0.1.0
curl -X POST https://tap.example.com/v1/marketplace/listings \
  -d '{"artifact_uri": "ghcr.io/you/vpc-provisioner:0.1.0", "tier": "internal"}'
```

## Rules the platform will hold you to

1. Mutations only through governed runs — agents never hold cloud credentials.
2. `policy_check` before every mutating tool call (Guardrails enforces it).
3. Destroy always requires human approval, whatever the policy verdict.
4. Stay inside your manifest's scope allowlist and mutation budget.
5. All ids are UUID strings; all timestamps UTC ISO 8601; fields snake_case.
