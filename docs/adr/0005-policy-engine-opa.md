# ADR-0005: Policy Engine — OPA Native, Sentinel Adapter, Kyverno for Admission

Status: Accepted
Date: 2026-10-09

## Context

Policy as code is TAP's core governance mechanism: every run is evaluated at
plan time ([ARCHITECTURE.md §5](../architecture/ARCHITECTURE.md)), with
hard-fail, soft-fail (approval-required), and advisory outcomes. The engine
choice determines:

- Whether policies are **testable** artifacts a platform team can CI-gate.
- Whether the policy language is portable across TAP, Kubernetes admission,
  CI pipelines, and customer-side tooling.
- The migration story for Terraform Cloud/Enterprise customers with existing
  **Sentinel** policy estates — a significant segment of TAP's target market.
- Vendor neutrality: policy is exactly the layer customers refuse to re-write
  twice.

## Options Considered

| Option | Language | Testability | Governance | Scope | Verdict |
|---|---|---|---|---|---|
| OPA / Rego | Rego, declarative | `opa test` first-class; coverage reporting | CNCF graduated, vendor-neutral | General-purpose: plan JSON, API authz, admission | **Accepted as native engine** |
| Sentinel | Sentinel DSL | Mocking-based, HCP-oriented | Proprietary (HashiCorp/IBM) | Terraform-ecosystem only | Adapter only — same BSL-era vendor risk as ADR-0001 |
| Kyverno | YAML policies | `kyverno test` | CNCF, K8s-native | Kubernetes admission only; cannot evaluate a Terraform plan | Adopted for K8s admission, not core |
| Cedar | Cedar | Good, formally verified core | AWS-stewarded, Apache 2.0 | Authorization-shaped, not plan-evaluation-shaped | Rejected for plan policy; watchlist for authz |
| Homegrown rules (Python) | Python | pytest | Ours alone | Whatever we build | Rejected: no customer-portable policy artifact, no ecosystem |

## Decision

**OPA/Rego is TAP's native policy engine** for plan-time gates, API
authorization (RBAC × ABAC decisions, [ARCHITECTURE.md §7](../architecture/ARCHITECTURE.md)),
and agent guardrail pre-checks.

- Policies live in `policies/` (terraform, kubernetes, cost, ai) and are
  shipped as versioned **OPA bundles** from the `governance/` framework;
  tenants pin bundle versions per policy set.
- Every policy merges with `opa test` passing and coverage reported in CI;
  `tests/` includes the policy test suites.
- Policy input is the normalized plan JSON plus run context (workspace,
  environment, cost delta, scan results) — one input schema across both IaC
  engines (ADR-0001).
- A **Sentinel adapter** in `governance/` translates common Sentinel policy
  patterns to Rego and, where translation is impossible, executes Sentinel
  policies via customer-provided tooling, flagged as unverified-by-TAP. This
  is a migration ramp, not a supported long-term target.
- **Kyverno** handles Kubernetes admission for TAP's own clusters and for
  tenant K8s policies in `policies/kubernetes/`, where its K8s-native
  ergonomics beat Rego; decisions still emit `policy.*` events into the same
  audit stream.

## Consequences

Positive:

- One policy language across plan gates, authz, and CI — customers' Rego
  skills and the public Rego ecosystem (library policies, Regal linting)
  transfer directly.
- `opa test` makes policy changes reviewable and regression-safe, which is
  the difference between policy-as-code and policy-as-configuration.
- CNCF graduation and vendor neutrality remove the "will the policy layer be
  relicensed" conversation from enterprise procurement.
- Sentinel adapter gives TFE migrators a credible path without anchoring TAP's
  core to a proprietary DSL.

Negative:

- Rego's learning curve is real; mitigated by the policy library in
  `policies/`, templates, and advisory-mode rollout for new policies.
- The Sentinel adapter can never be 100% faithful; translation gaps must be
  surfaced explicitly during migration, which adds support load.
- Two admission-relevant engines (OPA, Kyverno) means contributors must know
  which layer a rule belongs to; the governance framework docs draw that line.
