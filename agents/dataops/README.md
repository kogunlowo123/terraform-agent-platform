# DataOps Agent

Data platform provisioning and pipeline scaffolding: Snowflake, Databricks,
Airflow, lakehouse components, and catalog governance.

## Responsibilities

- Provision warehouses with mandatory auto-suspend and smallest-fit sizing
  (sizing up requires a stated workload justification).
- Scaffold idempotent pipeline DAGs carrying owner + SLA metadata
  (committing them is delegated to the devops agent).
- Register every provisioned dataset in the catalog — the `verify` node
  fails the run if a provision is planned without catalog registration.

## Capabilities

`data.warehouse.provision`, `data.pipeline.scaffold`,
`data.catalog.register`, `data.lakehouse.provision`.

## Tools

| Tool | Mutating | Purpose |
|---|---|---|
| `warehouse_provision` | yes | Governed Snowflake/Databricks warehouse run |
| `dag_generate` | no | Idempotent DAG scaffolding with metadata |
| `catalog_register` | yes (catalog) | Dataset registration + lineage |
| built-ins | mixed | `terraform_plan`, `terraform_apply`, `policy_check`, `cost_estimate` |

## Example invocation (SDK test harness)

```python
from langgraph.checkpoint.memory import MemorySaver
from agents.dataops.graph import DataOpsAgent

agent = DataOpsAgent.from_manifest("agents/dataops/agent.yaml")
app = agent.build_graph(checkpointer=MemorySaver())

out = app.invoke(
    {
        "task": "provision a snowflake warehouse for the marts workload",
        "context": {"workspace": "data-analytics", "platform": "snowflake",
                    "name": "marts_wh", "size": "xsmall",
                    "workload": "dbt nightly marts build",
                    "dataset_uri": "snowflake://analytics/marts",
                    "owner": "analytics-eng"},
        "plan": [], "actions": [], "results": {}, "errors": [],
        "requires_approval": False,
    },
    {"configurable": {"thread_id": "demo-1"}},
)
print(out["results"]["report"])
```
