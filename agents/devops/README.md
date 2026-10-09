# DevOps Agent

CI/CD and GitOps automation: pipeline generation, ArgoCD application
manifests, and environment-promotion pull requests.

## Responsibilities

- Generate GitHub Actions / GitLab CI pipelines embedding the TAP plan ->
  policy gate -> scan -> apply sequence.
- Commit generated manifests to feature branches and open PRs (never pushes
  to protected branches, never merges its own PRs).
- Open promotion PRs pinning the exact artifact digest in ArgoCD overlays.

## Capabilities

`pipeline.generate`, `gitops.sync`, `environment.promotion.pr`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `pipeline_generate` | no | Emit pipeline YAML with mandatory gates |
| `gitops_commit` | yes (VCS) | Branch commit + PR via platform VCS app |
| `promotion_pr` | yes (VCS) | Environment promotion PR (digest-pinned) |
| built-ins | mixed | `policy_check`, `scan_checkov` |

## Graph

Standard flow; VCS mutations gate on approval when `dry_run` is false or
policy returns `approval_required`.

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.devops.graph import DevOpsAgent

agent = DevOpsAgent.from_manifest("agents/devops/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

out = app.invoke(
    {
        "task": "generate a CI pipeline for the checkout service",
        "context": {"repo": "apps/checkout", "stack": "python-fastapi",
                    "platform": "github_actions"},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    {"configurable": {"thread_id": "demo-1"}},
)
print(out["results"]["report"])
```
