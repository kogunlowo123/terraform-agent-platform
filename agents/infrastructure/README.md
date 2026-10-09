# Infrastructure Agent

Terraform generation, module selection from the registry, governed
provisioning, and validation. The workhorse agent most other domains
delegate to.

## Responsibilities

- Generate HCL from intent, composing registry modules first (raw resources
  require a written justification).
- Select modules via registry ranking with provider/compliance constraints.
- Validate (terraform validate + fmt), scan (Checkov, tfsec), plan, cost and
  apply through governed runs. Apply only ever executes the previously
  evaluated plan artifact.
- State surgery (import/mv/rm) always escalates to a human.

## Capabilities

`infrastructure.generate`, `infrastructure.provision`,
`infrastructure.validate`, `module.select`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `hcl_generate` | no | Compose configuration bundle from modules |
| `module_select` | no | Rank registry modules for a requirement |
| `terraform_validate` | no | Ephemeral-runner validate + fmt |
| built-ins | mixed | `terraform_plan`, `terraform_apply`, `module_search`, `cost_estimate`, `policy_check`, `scan_checkov`, `scan_tfsec` |

## Graph

Standard flow. `act` sequences generate -> validate -> scans -> plan -> cost
(-> apply when authorized); apply is skipped outright if no evaluated plan
artifact exists in state.

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.infrastructure.graph import InfrastructureAgent

agent = InfrastructureAgent.from_manifest("agents/infrastructure/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

out = app.invoke(
    {
        "task": "generate a three-AZ VPC with private subnets for payments",
        "context": {"workspace": "net-payments", "provider": "aws",
                    "constraints": {"compliance": "cis"}},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    {"configurable": {"thread_id": "demo-1"}},
)
print(out["results"]["report"])
```
