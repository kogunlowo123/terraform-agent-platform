# NetOps Agent

Network design and provisioning: CIDR/subnet planning, VPC/VPN topology,
load balancers, DNS, and routing.

## Responsibilities

- Plan CIDRs with real subnet math (`cidr_plan` is implemented locally:
  largest-first allocation per AZ, collision checks against existing tenant
  address space, coalesced free-block reporting).
- Design and provision VPC/VPN/route topologies via governed Terraform runs.
- Manage DNS records and load balancer configuration under policy.
- Hard rules: production-zone DNS changes, default-route changes and
  deletes always escalate; 0.0.0.0/0 ingress on non-public tiers is denied.

## Capabilities

`network.cidr.plan`, `network.topology.design`, `network.dns.manage`,
`network.lb.configure`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `cidr_plan` | no | Subnet math: carve base CIDR across AZs |
| `dns_record_manage` | yes | Governed DNS change (deletes escalate) |
| `lb_configure` | yes | LB listeners/target groups/TLS policy |
| built-ins | mixed | `terraform_plan`, `terraform_apply`, `policy_check` |

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.netops.graph import NetOpsAgent

agent = NetOpsAgent.from_manifest("agents/netops/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

out = app.invoke(
    {
        "task": "design a three-AZ VPC address plan for payments",
        "context": {
            "workspace": "net-payments",
            "base_cidr": "10.20.0.0/16",
            "subnets": [
                {"name": "app", "hosts": 500, "tier": "private"},
                {"name": "db", "hosts": 50, "tier": "isolated"},
                {"name": "edge", "hosts": 30, "tier": "public"},
            ],
            "existing_cidrs": ["10.10.0.0/16"],
        },
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    {"configurable": {"thread_id": "demo-1"}},
)
print(out["results"]["cidr_plan"])
```
