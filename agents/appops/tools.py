"""AppOps domain tools: environment templates, provisioning, releases.

All tools use pydantic IO models. Bodies are platform-API contracts; the
execution plane is wired in by the runner at deploy time.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool


class TemplateRenderInput(BaseModel):
    template_id: str = Field(description="Catalog template id, e.g. 'catalog/web-service'.")
    version: str = Field(default="latest", description="Template version constraint.")
    parameters: dict[str, str] = Field(default_factory=dict, description="Template parameters.")
    workspace: str = Field(description="Target workspace slug.")


class TemplateRenderOutput(BaseModel):
    rendered_dir: str = Field(description="Path/URI of the rendered configuration bundle.")
    files: list[str] = Field(description="Relative paths of rendered files.")
    parameter_digest: str = Field(description="sha256 over resolved parameters, for audit.")


class EnvProvisionInput(BaseModel):
    workspace: str
    environment: Literal["dev", "staging", "prod", "preview"]
    rendered_dir: str = Field(description="Bundle from template_render; never ad-hoc HCL.")
    ttl_hours: int | None = Field(
        default=None, description="Auto-teardown TTL for ephemeral/preview environments."
    )


class EnvProvisionOutput(BaseModel):
    run_id: str = Field(description="Platform run id executing the provision.")
    environment_url: str | None = None
    status: Literal["planned", "applied", "pending_approval"]


class ReleasePromoteInput(BaseModel):
    application: str
    artifact_digest: str = Field(description="OCI digest of the release artifact.")
    from_environment: Literal["dev", "staging"]
    to_environment: Literal["staging", "prod"]
    strategy: Literal["rolling", "blue_green", "canary"] = "rolling"


class ReleasePromoteOutput(BaseModel):
    promotion_id: str
    status: Literal["promoted", "pending_approval", "rejected"]
    verification_checks: list[str] = Field(default_factory=list)


@tool
def template_render(params: TemplateRenderInput) -> TemplateRenderOutput:
    """Render an environment template from the platform catalog into a
    Terraform configuration bundle.

    Pure (non-mutating): resolves the template version, validates parameters
    against the template's JSON schema, and renders to an artifact store.
    """
    # Contract: POST /v1/templates/{template_id}/render
    #   -> 200 {rendered_dir, files[], parameter_digest}
    #   -> 422 on schema-invalid parameters (surfaced in state.errors).
    raise NotImplementedError("platform API binding injected by runner")


@tool
def env_provision(params: EnvProvisionInput) -> EnvProvisionOutput:
    """Provision (or update) an application environment from a rendered
    bundle via a governed platform run.

    Mutating: always starts as a plan; apply only proceeds through the
    standard policy + approval gates. TTL'd environments register their own
    teardown workflow.
    """
    # Contract: POST /v1/workspaces/{workspace}/runs
    #   body {action: "apply", dir: rendered_dir, env, ttl_hours}
    #   -> 202 {run_id, status}; status reflects the Temporal run lifecycle.
    raise NotImplementedError("platform API binding injected by runner")


@tool
def release_promote(params: ReleasePromoteInput) -> ReleasePromoteOutput:
    """Promote a release artifact along the environment chain.

    Mutating: dev -> staging -> prod only; skipping a stage is rejected by
    the platform and escalated. Promotion to prod always requires approval.
    """
    # Contract: POST /v1/applications/{application}/promotions
    #   body {artifact_digest, from_environment, to_environment, strategy}
    #   -> 202 {promotion_id, status, verification_checks[]}.
    raise NotImplementedError("platform API binding injected by runner")
