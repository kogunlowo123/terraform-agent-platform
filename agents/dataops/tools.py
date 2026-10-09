"""DataOps domain tools: warehouses, DAG scaffolding, catalog registration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool


class WarehouseProvisionInput(BaseModel):
    platform: Literal["snowflake", "databricks"]
    name: str
    size: Literal["xsmall", "small", "medium", "large", "xlarge"] = Field(
        default="xsmall",
        description="Smallest size satisfying the workload; sizing up needs justification.",
    )
    auto_suspend_minutes: int = Field(default=5, ge=1, description="Mandatory auto-suspend.")
    workload: str = Field(description="Stated workload justifying the size.")
    workspace: str


class WarehouseProvisionOutput(BaseModel):
    run_id: str
    resource_id: str | None = None
    status: Literal["planned", "applied", "pending_approval"]
    monthly_cost_estimate_usd: float | None = None


class DagGenerateInput(BaseModel):
    pipeline_name: str
    platform: Literal["airflow", "databricks_workflows"] = "airflow"
    source: str = Field(description="Source system/dataset URI.")
    destination: str = Field(description="Destination dataset URI.")
    schedule: str = Field(default="@daily", description="Cron or Airflow preset.")
    owner: str = Field(description="Owning team; embedded in DAG metadata.")
    sla_hours: int = Field(default=24, ge=1, description="SLA embedded in DAG metadata.")


class DagGenerateOutput(BaseModel):
    files: dict[str, str] = Field(description="Path -> generated DAG source.")
    idempotent: bool = Field(description="Generator guarantees idempotent task design.")
    lint_warnings: list[str] = Field(default_factory=list)


class CatalogRegisterInput(BaseModel):
    dataset_uri: str
    catalog: str = Field(default="default", description="Target catalog instance.")
    owner: str
    classification: Literal["public", "internal", "confidential", "restricted"] = "internal"
    schema_fields: list[dict[str, str]] = Field(
        default_factory=list, description="[{name, type, description}] column metadata."
    )


class CatalogRegisterOutput(BaseModel):
    catalog_entry_id: str
    lineage_registered: bool


@tool
def warehouse_provision(params: WarehouseProvisionInput) -> WarehouseProvisionOutput:
    """Provision a Snowflake warehouse / Databricks SQL warehouse via a
    governed Terraform run.

    Mutating: auto-suspend is mandatory and injected if omitted; any size
    above 'small' routes through cost policy and may require approval.
    """
    # Contract: POST /v1/data/warehouses -> 202 {run_id, resource_id, status,
    #   monthly_cost_estimate_usd}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def dag_generate(params: DagGenerateInput) -> DagGenerateOutput:
    """Scaffold an idempotent pipeline DAG with owner + SLA metadata.

    Pure: generates source files only; committing them is the devops agent's
    job (delegated over NATS).
    """
    # Contract: POST /v1/data/pipelines/generate -> 200 {files{}, idempotent,
    #   lint_warnings[]}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def catalog_register(params: CatalogRegisterInput) -> CatalogRegisterOutput:
    """Register a dataset in the data catalog with ownership, classification
    and lineage.

    Mutating (catalog only): mandatory for every dataset the agent
    provisions — no orphan datasets.
    """
    # Contract: POST /v1/data/catalog/entries -> 201 {catalog_entry_id,
    #   lineage_registered}
    raise NotImplementedError("platform API binding injected by runner")
