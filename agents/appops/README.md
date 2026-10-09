# AppOps Agent

Application lifecycle operations: environment provisioning from catalog
templates, release orchestration along the environment chain, and developer
self-service fulfilment.

## Responsibilities

- Provision/update app environments from approved templates only (never
  ad-hoc HCL — that is the infrastructure agent's domain).
- Orchestrate release promotion dev -> staging -> prod (artifact digests,
  rolling/blue-green/canary strategies).
- Fulfil developer self-service requests within the requester's RBAC
  entitlements; TTL'd preview environments register their own teardown.

## Capabilities

`environment.provision`, `environment.teardown`, `release.orchestrate`,
`selfservice.fulfil` — discoverable via the Agent Registry.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `template_render` | no | Render catalog template to a config bundle |
| `env_provision` | yes | Governed run to provision/update an environment |
| `release_promote` | yes | Promote an artifact along the env chain |
| built-ins | mixed | `terraform_plan`, `terraform_apply`, `policy_check`, `cost_estimate` |

## Graph

Standard flow with an `approval` interrupt before `act` whenever the plan is
mutating or policy returns `approval_required`. Promotion to prod always
escalates.

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.appops.graph import AppOpsAgent

agent = AppOpsAgent.from_manifest("agents/appops/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "demo-1"}}
out = app.invoke(
    {
        "task": "provision a preview environment for service checkout",
        "context": {"workspace": "app-checkout", "environment": "preview",
                    "template_id": "catalog/web-service", "ttl_hours": 48},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    config,
)
print(out["results"]["report"])

# If the run interrupted at `approval`, resume after human sign-off:
# app.invoke(None, config)
```
