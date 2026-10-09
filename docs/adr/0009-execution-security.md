# ADR-0009: Execution Security — Ephemeral Runners, OIDC Federation, Signed Artifacts

Status: Accepted
Date: 2026-10-09

## Context

The execution plane is where TAP touches tenant clouds with mutating
credentials — the highest-value target in the system. The threat model
([security guide](../guides/security-guide.md)) concentrates here: credential
theft from runners, state exfiltration, plan/apply divergence, supply-chain
compromise of agent or runner images, and an LLM-influenced agent requesting a
destructive action. Each control below answers a specific attack, and they are
decided together because they only work together.

## Options Considered

| Concern | Options | Chosen | Rejected because |
|---|---|---|---|
| Runner lifecycle | Long-lived worker pool; ephemeral K8s Job per run step | Ephemeral Jobs | Warm pools accumulate secrets, state, and compromise; reuse is the attack surface |
| Cloud credentials | Static keys in a vault; broker-issued STS; OIDC federation | OIDC federation | Static keys leak and rot; a broker is a stateful secret store we'd have to defend |
| State protection | Shared bucket + single key; per-tenant KMS envelope encryption | Per-tenant KMS | Single key makes one compromise a full-platform state breach |
| Plan/apply integrity | Re-plan at apply time; apply the evaluated plan artifact only | Plan-artifact-only apply | Re-planning reintroduces TOCTOU — the applied change is not the approved change |
| Supply chain | Trust registry contents; sign + verify (cosign) with SBOM | Signed artifacts | Unsigned marketplace distribution is an arbitrary-code-execution channel into runners |
| Destroy actions | Policy-gated like any run; always human-approved | Always human-approved | No policy evaluation of a plan JSON reliably prices blast radius of deletion |

## Decision

1. **Ephemeral runners.** Every plan/apply/scan executes as a single-use
   Kubernetes Job from a minimal, pinned runner image: non-root, read-only
   root filesystem, no privilege escalation, seccomp `RuntimeDefault`,
   per-tenant egress NetworkPolicy
   ([multi-tenant design](../saas/multi-tenant-design.md)). The pod is
   deleted on completion; nothing persists on the node.
2. **OIDC federation, no static cloud keys.** The runner's projected service
   account token is exchanged directly with the tenant's cloud (AWS
   AssumeRoleWithWebIdentity, Azure workload identity federation, GCP
   workload identity) for a **15-minute token scoped to the workspace's
   role**. TAP stores trust configuration, never credentials.
3. **Per-tenant KMS-encrypted state.** State versions are envelope-encrypted
   with a per-tenant KMS key before hitting the versioned object store;
   higher isolation tiers use customer-managed keys. Key revocation is part
   of tenant offboarding.
4. **Plan-artifact-only apply.** Apply jobs execute the exact plan artifact
   that policy evaluated and the approver saw — content-addressed, integrity-
   checked at apply time. The workflow engine (ADR-0003) refuses an apply
   whose artifact hash does not match the approved plan. No TOCTOU window.
5. **Signed agent and runner artifacts.** All first-party images and all
   marketplace agents are **cosign-signed with an SBOM published**;
   admission verifies signatures against the trusted-publisher keyring, and
   the marketplace verification pipeline (scan, license check, capability
   review) gates community publication.
6. **Destroy is always human-approved.** Regardless of policy result, tier, or
   agent autonomy settings, a destroy run requires an explicit, recorded human
   approval. This is a platform invariant, not a configurable policy.

## Consequences

Positive:

- Compromise of any single runner yields a 15-minute, single-workspace
  credential and no neighbor data — the blast radius design goal.
- "No static cloud credentials" is a one-sentence answer to the first
  question in every enterprise security review.
- The approved-plan invariant makes the audit trail semantically complete:
  what was approved is provably what ran.
- SBOMs and signatures give customers a supply-chain story that survives
  SOC 2 and vendor-security questionnaires (`compliance/` mappings).

Negative:

- Job-per-step adds pod-startup latency (seconds) to every run; acceptable
  against minutes-long plans, partially offset by pre-pulled images.
- OIDC trust setup per tenant cloud account is real onboarding friction;
  mitigated by bootstrap modules in `terraform/` that create the trust
  configuration.
- Mandatory destroy approval frustrates full-autonomy aspirations —
  deliberately. Ephemeral-environment teardown gets a narrow, policy-scoped
  exception process only via pre-approved workspace classes, and that
  exception itself requires an accepted future ADR.
