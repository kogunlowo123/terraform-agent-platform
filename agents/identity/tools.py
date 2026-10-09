"""Identity domain tools: IAM policy generation, access reviews, entitlement
diffs. Every mutation in this domain requires human approval (guardrail
override in agent.yaml)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool


class IamPolicyGenerateInput(BaseModel):
    provider: Literal["aws", "azure", "gcp"]
    principal: str = Field(description="Role/user/service-account the policy attaches to.")
    required_access: list[str] = Field(
        description="Observed or requested access needs, e.g. 's3:GetObject on arn:...bucket/*'."
    )
    base_on_observed_usage: bool = Field(
        default=True,
        description="Derive from entitlement_diff observations (least-privilege by construction).",
    )


class IamPolicyGenerateOutput(BaseModel):
    policy_document: dict = Field(description="Provider-native policy JSON.")
    warnings: list[str] = Field(
        default_factory=list,
        description="Flags: wildcard principals, unconditioned iam:PassRole, trust changes.",
    )
    least_privilege_score: float = Field(ge=0.0, le=1.0)


class AccessReviewInput(BaseModel):
    scope: str = Field(description="Tenant/project/workspace under review.")
    review_window_days: int = Field(default=90, ge=7)
    include_service_accounts: bool = True


class AccessReviewFinding(BaseModel):
    principal: str
    entitlement: str
    last_used: str | None = Field(default=None, description="ISO timestamp; None = never used.")
    recommendation: Literal["keep", "revoke", "downgrade", "review"]
    rationale: str


class AccessReviewOutput(BaseModel):
    findings: list[AccessReviewFinding]
    revocation_candidates: int


class EntitlementDiffInput(BaseModel):
    principal: str
    provider: Literal["aws", "azure", "gcp"]
    observation_window_days: int = Field(default=90, ge=30)


class EntitlementDiffOutput(BaseModel):
    granted: list[str] = Field(description="Entitlements currently granted.")
    used: list[str] = Field(description="Entitlements actually exercised in the window.")
    unused: list[str] = Field(description="granted - used: least-privilege reduction set.")
    missing: list[str] = Field(
        default_factory=list, description="Denied attempts suggesting legitimate needs."
    )


@tool
def iam_policy_generate(params: IamPolicyGenerateInput) -> IamPolicyGenerateOutput:
    """Generate a least-privilege IAM policy for a principal.

    Pure: starts from observed usage (never from '*'), emits provider-native
    JSON plus warnings for risky constructs (wildcard principals,
    unconditioned iam:PassRole, trust-policy changes). Attaching the policy
    is a separate, always-approved mutation.
    """
    # Contract: POST /v1/identity/policies/generate -> 200 {policy_document,
    #   warnings[], least_privilege_score}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def access_review(params: AccessReviewInput) -> AccessReviewOutput:
    """Run an access review over a scope: who holds what, what is unused,
    what should be revoked or downgraded.

    Pure: produces recommendations only; revocations are mutations that each
    require human approval.
    """
    # Contract: POST /v1/identity/access-reviews -> 200 {findings[], revocation_candidates}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def entitlement_diff(params: EntitlementDiffInput) -> EntitlementDiffOutput:
    """Diff granted vs. exercised entitlements for a principal over an
    observation window (CloudTrail / Azure Activity / GCP audit logs).

    Pure: the foundation for least-privilege policy generation.
    """
    # Contract: GET /v1/identity/principals/{principal}/entitlement-diff
    #   -> 200 {granted[], used[], unused[], missing[]}
    raise NotImplementedError("platform API binding injected by runner")
