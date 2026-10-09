# CostOps Agent

FinOps: cost forecasting, budget enforcement (blocking over-budget runs via
policy), rightsizing recommendations, and anomaly detection.

## Responsibilities

- Forecast spend per tenant/project/workspace, folding in pending plan deltas.
- Enforce budgets: `budget_check` verdicts are authoritative — an
  `over_budget` verdict denies the associated run (status `denied`, overage
  and budget id cited); the agent never suggests workarounds.
- Recommend rightsizing with mandatory utilization evidence and observation
  window; savings below the tenant noise floor are not emitted. Execution of
  accepted recommendations is delegated to the infrastructure agent.
- Detect anomalies against forecast baselines (baseline, deviation, driving
  resource ids in the report).

## Capabilities

`cost.forecast`, `cost.budget.enforce`, `cost.rightsize.recommend`,
`cost.anomaly.detect`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `cost_forecast` | no | Spend forecast with drivers + confidence |
| `budget_check` | no (enforcing) | Authoritative budget verdict for a run |
| `rightsize_recommend` | no | Evidence-backed sizing recommendations |
| built-ins | no | `cost_estimate`, `policy_check` |

This agent's `mutation_budget` is 0 and its graph compiles without an
approval interrupt — it never mutates infrastructure.

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.costops.graph import CostOpsAgent

agent = CostOpsAgent.from_manifest("agents/costops/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

out = app.invoke(
    {
        "task": "check run cost against the platform budget",
        "context": {"workspace": "app-checkout", "budget_id": "bud-platform-q4",
                    "proposed_delta_usd": 420.0},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    {"configurable": {"thread_id": "demo-1"}},
)
print(out["results"]["report"])  # status == "denied" when over budget
```
