"""DevOps domain tools: pipeline generation, GitOps commits, promotion PRs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool


class PipelineGenerateInput(BaseModel):
    repo: str = Field(description="Target repository, e.g. 'apps/checkout'.")
    platform: Literal["github_actions", "gitlab_ci"] = "github_actions"
    stack: str = Field(description="App stack hint, e.g. 'python-fastapi', 'node-next'.")
    environments: list[str] = Field(default_factory=lambda: ["dev", "staging", "prod"])
    include_policy_gate: bool = Field(
        default=True, description="TAP policy gate + scan steps; must stay true for apply pipelines."
    )


class PipelineGenerateOutput(BaseModel):
    files: dict[str, str] = Field(description="Path -> generated pipeline YAML.")
    gates: list[str] = Field(description="Gate steps embedded (policy, scans, approvals).")


class GitopsCommitInput(BaseModel):
    repo: str
    branch: str = Field(description="Feature branch; never a protected branch.")
    files: dict[str, str] = Field(description="Path -> content to commit.")
    message: str
    open_pr: bool = True


class GitopsCommitOutput(BaseModel):
    commit_sha: str
    pr_url: str | None = None


class PromotionPrInput(BaseModel):
    repo: str = Field(description="GitOps repo holding environment overlays.")
    application: str
    artifact_digest: str = Field(description="Exact digest being promoted; tags are rejected.")
    from_environment: str
    to_environment: str


class PromotionPrOutput(BaseModel):
    pr_url: str
    checks_required: list[str] = Field(default_factory=list)


@tool
def pipeline_generate(params: PipelineGenerateInput) -> PipelineGenerateOutput:
    """Generate a CI/CD pipeline (GitHub Actions or GitLab CI) for a repo.

    Pure: emits YAML embedding the TAP plan -> policy gate -> scan -> apply
    sequence. Never generates a pipeline that applies without a prior
    evaluated plan.
    """
    # Contract: POST /v1/pipelines/generate -> 200 {files{}, gates[]}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def gitops_commit(params: GitopsCommitInput) -> GitopsCommitOutput:
    """Commit generated manifests/pipelines to a feature branch and open a PR.

    Mutating (VCS only): pushes to a non-protected branch via the platform's
    VCS app credentials; direct pushes to protected branches are refused
    server-side.
    """
    # Contract: POST /v1/vcs/{repo}/commits -> 201 {commit_sha, pr_url}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def promotion_pr(params: PromotionPrInput) -> PromotionPrOutput:
    """Open an environment-promotion PR in the GitOps repo (ArgoCD overlays).

    Mutating (VCS only): updates the target overlay to the exact artifact
    digest. Merge is left to humans/required checks; the agent never merges.
    """
    # Contract: POST /v1/gitops/{repo}/promotions -> 201 {pr_url, checks_required[]}
    raise NotImplementedError("platform API binding injected by runner")
