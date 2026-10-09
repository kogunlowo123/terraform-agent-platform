# SecOps Agent

Security scan orchestration (Checkov, tfsec, Trivy), OPA validation, finding
triage, and remediation PRs.

## Responsibilities

- Run and merge multi-scanner results against workspaces and repos.
- Validate plans/configs against OPA policy bundles.
- Triage findings consistently (prior decisions persist in semantic memory
  keyed by rule id + rationale); suppressions require justification + expiry.
- Open remediation PRs for HIGH/MEDIUM/LOW findings. Never direct applies.

## Severity gate (domain-specific node)

`severity_gate` sits between `act` and `verify`. Any CRITICAL finding forces
`requires_approval = True`, sets `severity_gate.verdict = "escalate"` in the
report, and is excluded from auto-remediation. Criticals always reach a human.

## Capabilities

`security.scan.orchestrate`, `security.policy.validate`,
`security.finding.triage`, `security.remediation.pr`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `finding_triage` | no | Dedupe + disposition merged findings |
| `remediation_pr` | yes (VCS) | Fix PR for remediable findings |
| built-ins | no | `scan_checkov`, `scan_tfsec`, `scan_trivy`, `policy_check` |

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.secops.graph import SecOpsAgent

agent = SecOpsAgent.from_manifest("agents/secops/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

out = app.invoke(
    {
        "task": "scan the payments workspace and remediate findings",
        "context": {"workspace": "net-payments", "repo": "apps/payments",
                    "dir": "terraform/"},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    {"configurable": {"thread_id": "demo-1"}},
)
print(out["results"]["report"])  # status == "escalated" if criticals found
```
