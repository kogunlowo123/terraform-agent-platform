"""LLMOps domain tools: model endpoints, RAG stacks, prompt registry, evals."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool


class ModelDeployInput(BaseModel):
    provider: Literal["bedrock", "azure_openai", "vertex"]
    model_id: str = Field(description="Provider model id, e.g. an Anthropic model on Bedrock.")
    endpoint_name: str
    workspace: str
    governance_review_id: str = Field(
        description="Mandatory AI governance review id; deploys without one are denied."
    )
    capacity: dict[str, int] = Field(
        default_factory=dict, description="Provider-specific throughput/PTU/replica settings."
    )


class ModelDeployOutput(BaseModel):
    run_id: str
    endpoint_arn_or_url: str | None = None
    status: Literal["planned", "applied", "pending_approval"]


class RagProvisionInput(BaseModel):
    workspace: str
    vector_db: Literal["qdrant", "pgvector", "opensearch"] = "qdrant"
    collection: str
    embedding_model: str
    ingestion_sources: list[str] = Field(description="URIs the ingestion pipeline will index.")


class RagProvisionOutput(BaseModel):
    run_id: str
    components: list[str] = Field(description="Provisioned components (db, pipeline, gateway route).")
    status: Literal["planned", "applied", "pending_approval"]


class PromptPublishInput(BaseModel):
    registry_path: str = Field(description="e.g. 'registry/support/triage'.")
    template: str
    version_bump: Literal["major", "minor", "patch"] = "patch"
    changelog: str


class PromptPublishOutput(BaseModel):
    version: str = Field(description="Published immutable version, e.g. '1.4.0'.")
    registry_url: str


class EvalRunInput(BaseModel):
    endpoint_name: str
    suite: str = Field(description="Eval suite id from the eval catalog.")
    baseline_version: str | None = Field(
        default=None, description="Compare against this prior run/version."
    )


class EvalRunOutput(BaseModel):
    eval_run_id: str
    passed: bool
    scores: dict[str, float]
    regressions: list[str] = Field(default_factory=list)


@tool
def model_deploy(params: ModelDeployInput) -> ModelDeployOutput:
    """Deploy a model endpoint (Bedrock / Azure OpenAI / Vertex) via a
    governed Terraform run using terraform/ai/ modules.

    Mutating: denied without a governance_review_id; prod promotion requires
    a passing eval_run id in evidence.
    """
    # Contract: POST /v1/ai/endpoints -> 202 {run_id, endpoint_arn_or_url, status}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def rag_provision(params: RagProvisionInput) -> RagProvisionOutput:
    """Provision a RAG stack: vector DB collection, ingestion pipeline, and
    an AI Gateway route wired to the embedding model.

    Mutating: collections are namespaced tenant:{id}:...; cross-tenant
    sources are denied by policy.
    """
    # Contract: POST /v1/ai/rag-stacks -> 202 {run_id, components[], status}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def prompt_publish(params: PromptPublishInput) -> PromptPublishOutput:
    """Publish a versioned, immutable prompt to the registry.

    Mutating (registry only): rollback is a new publish of a prior version,
    never an in-place edit.
    """
    # Contract: POST /v1/ai/prompts/{registry_path}/versions -> 201 {version, registry_url}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def eval_run(params: EvalRunInput) -> EvalRunOutput:
    """Run an eval suite against an endpoint and gate promotion on the result.

    Pure (no infra mutation): results land in the eval store and are cited
    as evidence in the report.
    """
    # Contract: POST /v1/ai/evals -> 200 {eval_run_id, passed, scores{}, regressions[]}
    raise NotImplementedError("platform API binding injected by runner")
