"""Infrastructure domain tools: HCL generation, module selection, validation.

Built-ins (terraform_plan/apply, module_search, cost_estimate, policy_check,
scan_*) come from tap_sdk; only domain-specific tools live here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool


class HclGenerateInput(BaseModel):
    workspace: str
    provider: Literal["aws", "azure", "gcp", "kubernetes"]
    intent: str = Field(description="Natural-language infrastructure intent.")
    modules: list[str] = Field(
        default_factory=list,
        description="Registry module ids selected by module_select; raw resources need justification.",
    )
    variables: dict[str, str] = Field(default_factory=dict)


class HclGenerateOutput(BaseModel):
    dir: str = Field(description="Path/URI of the generated configuration.")
    files: dict[str, str] = Field(description="Relative path -> HCL content.")
    raw_resource_justifications: dict[str, str] = Field(
        default_factory=dict,
        description="resource address -> why no registry module fit.",
    )


class ModuleSelectInput(BaseModel):
    requirement: str = Field(description="What the module must provide.")
    provider: Literal["aws", "azure", "gcp", "kubernetes"]
    constraints: dict[str, str] = Field(
        default_factory=dict, description="e.g. {'compliance': 'cis', 'min_version': '2.x'}."
    )


class ModuleCandidate(BaseModel):
    module_id: str
    version: str
    score: float = Field(ge=0.0, le=1.0, description="Fit score from registry ranking.")
    verified: bool = Field(description="Marketplace verification status.")


class ModuleSelectOutput(BaseModel):
    selected: ModuleCandidate
    alternatives: list[ModuleCandidate] = Field(default_factory=list)


class TerraformValidateInput(BaseModel):
    dir: str = Field(description="Configuration directory to validate.")
    workspace: str


class TerraformValidateOutput(BaseModel):
    valid: bool
    diagnostics: list[str] = Field(default_factory=list)


@tool
def hcl_generate(params: HclGenerateInput) -> HclGenerateOutput:
    """Generate Terraform configuration for the stated intent.

    Pure: composes registry modules (preferred) plus justified raw resources
    into a configuration bundle. Backend/provider blocks are injected from
    workspace settings, Terragrunt-style, not authored here.
    """
    # Contract: POST /v1/iac/generate -> 200 {dir, files{}, raw_resource_justifications{}}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def module_select(params: ModuleSelectInput) -> ModuleSelectOutput:
    """Rank and select the best registry module for a requirement.

    Pure: semantic search over the module registry (module_search built-in)
    plus constraint filtering (provider, compliance tier, version).
    """
    # Contract: POST /v1/modules/select -> 200 {selected, alternatives[]}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def terraform_validate(params: TerraformValidateInput) -> TerraformValidateOutput:
    """Run `terraform validate` (plus fmt check) on a generated bundle in an
    ephemeral runner.

    Pure: no state access, no cloud credentials; syntax + schema validation
    only.
    """
    # Contract: POST /v1/workspaces/{workspace}/validate -> 200 {valid, diagnostics[]}
    raise NotImplementedError("platform API binding injected by runner")
