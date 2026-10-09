# LLMOps Agent

AI infrastructure operations: model endpoint deployment (Bedrock, Azure
OpenAI, Vertex), RAG stack provisioning, prompt registry operations, eval
runs, and AI governance checks.

## Responsibilities

- Deploy model endpoints via `terraform/ai/` modules through governed runs;
  deploys without a `governance_review_id` are denied in `analyze`.
- Provision RAG stacks: tenant-namespaced vector DB collection, ingestion
  pipeline, AI Gateway route.
- Publish versioned, immutable prompts (rollback = republish prior version).
- Run eval suites; the `verify` node fails deploys whose eval gate fails,
  and the eval run id is cited as evidence in the report.

## Capabilities

`ai.model.deploy`, `ai.rag.provision`, `ai.prompt.publish`, `ai.eval.run`,
`ai.governance.check`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `model_deploy` | yes | Governed endpoint deployment |
| `rag_provision` | yes | Vector DB + ingestion + gateway route |
| `prompt_publish` | yes (registry) | Immutable versioned prompt publish |
| `eval_run` | no | Eval suite execution, promotion gate |
| built-ins | mixed | `terraform_plan`, `terraform_apply`, `policy_check`, `cost_estimate` |

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.llmops.graph import LLMOpsAgent

agent = LLMOpsAgent.from_manifest("agents/llmops/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

out = app.invoke(
    {
        "task": "deploy a claude endpoint for the support copilot",
        "context": {"workspace": "ai-support", "provider": "bedrock",
                    "model_id": "anthropic.claude-sonnet", "endpoint_name": "support-copilot",
                    "governance_review_id": "AIR-2026-041", "suite": "support-v2"},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    {"configurable": {"thread_id": "demo-1"}},
)
print(out["results"]["report"])
```
