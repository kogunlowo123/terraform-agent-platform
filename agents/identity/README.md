# Identity Agent

IAM policy generation with least-privilege analysis, access reviews, RBAC
sync, and federation setup.

## Guardrail override

**Every mutation in this domain requires human approval.** The manifest sets
`approval_required_for_all_mutations: true` and the graph enforces it: any
plan containing a mutating step sets `requires_approval = True` in `plan`,
and `policy_precheck` never downgrades it — a passing policy verdict or
`dry_run: false` cannot bypass the approval interrupt.

## Responsibilities

- Generate least-privilege IAM policies from observed usage
  (`entitlement_diff` first, never from `*` actions).
- Run access reviews (unused entitlements, revocation candidates).
- Diff granted vs. exercised entitlements per principal.
- RBAC sync and federation setup via governed Terraform runs (approved,
  always).
- Risky constructs (wildcard principals, unconditioned `iam:PassRole`,
  trust-policy changes) surface as `critical_policy_warnings` in the report
  even when explicitly requested.

## Capabilities

`iam.policy.generate`, `iam.least_privilege.analyze`, `iam.access.review`,
`iam.rbac.sync`, `iam.federation.setup`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `iam_policy_generate` | no | Least-privilege policy from observed usage |
| `access_review` | no | Entitlement review + revocation candidates |
| `entitlement_diff` | no | granted vs. used vs. missing entitlements |
| built-ins | mixed | `terraform_plan`, `terraform_apply` (approved only), `policy_check` |

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.identity.graph import IdentityAgent

agent = IdentityAgent.from_manifest("agents/identity/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "demo-1"}}
out = app.invoke(
    {
        "task": "generate and attach a least-privilege policy for ci-deployer",
        "context": {"workspace": "iam-core", "provider": "aws",
                    "principal": "arn:aws:iam::123456789012:role/ci-deployer"},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    config,
)
# The graph ALWAYS interrupts at `approval` for this task (mutating plan).
# After a recorded human approval:
out = app.invoke(None, config)
print(out["results"]["report"])
```
