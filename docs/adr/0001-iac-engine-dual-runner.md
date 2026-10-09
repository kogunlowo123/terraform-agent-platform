# ADR-0001: IaC Engine — Terraform + OpenTofu Dual Runner

Status: Accepted
Date: 2026-10-09

## Context

TAP's execution plane runs infrastructure-as-code on behalf of tenants. The
engine choice is the platform's most load-bearing dependency and carries legal
exposure, not just technical risk:

- HashiCorp relicensed Terraform from MPL-2.0 to **BSL 1.1** in August 2023.
  BSL prohibits offering products "competitive with HashiCorp's" — which a
  commercial IaC SaaS plainly is. IBM's 2025 acquisition of HashiCorp adds a
  second layer of uncertainty about future license enforcement posture.
- **OpenTofu** (Linux Foundation) forked at Terraform 1.5 under MPL-2.0 and
  maintains near-complete provider and language compatibility, with its own
  features (state encryption, early variable evaluation).
- Enterprise customers have large existing Terraform estates and some are
  contractually tied to HCP; a Tofu-only platform blocks them, a
  Terraform-only platform blocks us.
- Teams also ask about Terragrunt (DRY orchestration), Pulumi (general-purpose
  languages), and Crossplane (K8s-native control plane). The platform must
  answer why not those.

## Options Considered

| Option | Adoption | Licensing | Plan semantics | Language lock-in | K8s coupling | Verdict |
|---|---|---|---|---|---|---|
| Terraform only | Dominant, huge module ecosystem | BSL 1.1 — redistribution/competition risk for a commercial SaaS; IBM ownership adds uncertainty | Gold standard plan/apply | HCL only | None | Rejected as sole engine: legal exposure |
| OpenTofu only | Growing fast, LF-governed | MPL-2.0 — safe to embed and resell | Terraform-equivalent | HCL only | None | Rejected as sole engine: blocks HCP-tied enterprises |
| Terragrunt | Popular in large estates | MPL-2.0 | Delegates to TF/Tofu; adds DRY orchestration | HCL + HCL wrapper | None | Not an engine; adopt its *pattern*, not the tool |
| Pulumi | Strong with dev-centric teams | Apache 2.0 (OSS core) | Preview weaker than plan artifact; state service gravity | TS/Python/Go — fragments module ecosystem | None | Rejected as core; possible future runner plugin |
| Crossplane | CNCF, platform-team niche | Apache 2.0 | Reconciliation loop, no reviewable plan artifact | YAML/XRDs | Hard requirement — control plane *is* K8s | Rejected: weak plan/preview semantics break TAP's policy-gate model |

## Decision

Implement a **dual runner** behind a single `IaCRunner` plugin interface
(`plugins/`): both Terraform and OpenTofu binaries ship as runner images, and
each workspace declares its engine and version.

- **OpenTofu is the default** for TAP-operated SaaS deployments — MPL-2.0
  removes redistribution and competitive-use risk entirely.
- Terraform remains fully supported for self-hosted customers who hold their
  own HashiCorp relationship; TAP invokes the binary the customer provides or
  pulls, which keeps TAP outside BSL's distribution surface.
- **Terragrunt-style DRY** is provided natively: the control plane generates
  backend and provider configuration per workspace at run time, so modules
  contain no backend blocks and no credentials. No Terragrunt dependency.
- The `IaCRunner` interface normalizes: init, plan (JSON output), apply from
  plan artifact, destroy, state operations, and version resolution.

## Consequences

Positive:

- No legal exposure in the SaaS offering; no dependency on HashiCorp/IBM
  goodwill for the default path.
- Customers migrate between engines per workspace — a genuine differentiator
  against Terraform Cloud.
- Generated backend/provider config eliminates an entire class of
  copy-paste drift and keeps credentials out of module source.
- Plugin interface leaves the door open for a Pulumi runner if demand appears.

Negative:

- **Provider compatibility testing matrix**: every supported engine version ×
  the top providers (aws, azurerm, google, kubernetes, helm) must pass the
  module test suite in CI. This matrix is a standing cost; we cap supported
  engine versions at current-minus-two.
- Terraform and OpenTofu will diverge over time (plan JSON schema, state
  format, language features). The `IaCRunner` abstraction must absorb this;
  divergence-sensitive code is quarantined to the runner plugins.
- Two sets of upstream release notes to track; engine-version advisories
  become a platform responsibility.
