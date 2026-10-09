"""SecOps domain tools: finding triage and remediation PRs.

Scanners (scan_checkov, scan_tfsec, scan_trivy) and OPA validation
(policy_check) are tap_sdk built-ins.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


class Finding(BaseModel):
    id: str
    scanner: Literal["checkov", "tfsec", "trivy", "opa"]
    rule_id: str
    severity: Severity
    resource: str
    description: str
    remediation_hint: str | None = None


class FindingTriageInput(BaseModel):
    findings: list[Finding]
    workspace: str
    suppress_known_false_positives: bool = Field(
        default=True,
        description="Consult semantic memory for prior triage decisions (rule id + rationale).",
    )


class TriagedFinding(BaseModel):
    finding: Finding
    disposition: Literal["remediate", "escalate", "suppress", "accept_risk"]
    rationale: str
    suppression_expiry: str | None = Field(
        default=None, description="ISO date; mandatory when disposition is 'suppress'."
    )


class FindingTriageOutput(BaseModel):
    triaged: list[TriagedFinding]
    critical_count: int
    high_count: int


class RemediationPrInput(BaseModel):
    repo: str
    workspace: str
    findings: list[TriagedFinding] = Field(
        description="Only dispositions == 'remediate'; CRITICALs are rejected (escalate instead)."
    )
    branch: str = "tap/secops-remediation"


class RemediationPrOutput(BaseModel):
    pr_url: str
    fixed_rule_ids: list[str]
    unfixable: list[str] = Field(default_factory=list, description="Rule ids needing manual work.")


@tool
def finding_triage(params: FindingTriageInput) -> FindingTriageOutput:
    """Triage merged scanner findings into dispositions.

    Pure: dedupes across scanners, applies prior triage decisions from
    semantic memory, and classifies each finding. CRITICAL findings are
    always dispositioned 'escalate' — never 'remediate' or 'suppress'.
    """
    # Contract: POST /v1/security/triage -> 200 {triaged[], critical_count, high_count}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def remediation_pr(params: RemediationPrInput) -> RemediationPrOutput:
    """Open a remediation PR fixing triaged HIGH/MEDIUM/LOW findings.

    Mutating (VCS only): generates fixes on a branch and opens a PR with the
    finding evidence attached. Rejects any CRITICAL in the input (platform
    enforces; agent must not submit them).
    """
    # Contract: POST /v1/security/remediations -> 201 {pr_url, fixed_rule_ids[], unfixable[]}
    raise NotImplementedError("platform API binding injected by runner")
