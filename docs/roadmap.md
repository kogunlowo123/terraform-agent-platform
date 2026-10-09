# TAP Roadmap

Status: living document · Owners: Platform Architecture Group
Related: [README](../README.md) · [ARCHITECTURE.md](architecture/ARCHITECTURE.md) · [Commercialization](saas/commercialization.md)

Phases are sequential but overlap; exit criteria gate the *next* phase's
start, not all work in it. Engineering estimates assume a core team of 4–6
senior engineers and exclude GTM/sales effort.

---

## P0 — Foundation (this scaffold)

**Scope.** Everything required for a platform team to build on TAP without
re-litigating architecture: reference architecture and ADRs 0001–0009; repo
skeleton (`agents/`, `platform/`, `sdk/`, `plugins/`, `terraform/`,
`policies/`, `governance/`); OpenAPI v1 contract and DB schema; dev compose
stack (Postgres, Redis, NATS, Qdrant, Temporal, OPA); CI skeleton (lint,
pytest, `opa test`, terratest harness); base policies and module standards.

**Exit criteria.**
- `./scripts/dev-up.sh` brings up the full local stack from a clean machine.
- A demo plan run flows end-to-end: API → Temporal → runner → OPA gate →
  (mock) apply, with audit rows and `run.*` events emitted.
- SDK can scaffold a hello-world agent that loads in the orchestrator.
- All ADRs Accepted; docs in this directory complete.

**Estimate.** 6–8 eng-months.

## P1 — MVP: Single-Cloud Governed Runs + OSS Launch

**Scope.** Production-quality governed runs on **AWS**: full plan → policy →
approve → apply → verify lifecycle with compensation; state encryption,
locking, versioning; OIDC federation; **3 agents** shipped hardened
(Infrastructure, SecOps, CostOps); **GitHub integration** (PR plan comments,
checks API, webhook-triggered runs); CLI (`tap`); Slack approvals; the AWS
module set in `terraform/aws/` covered by terratest; **public OSS launch**
(Apache 2.0, docs, examples, contribution guide).

**Exit criteria.**
- One design-partner team runs real AWS production changes through TAP for
  30 days with zero state-corruption incidents.
- Policy gates and human approval demonstrably block a seeded violation and a
  seeded destroy.
- OSS launch shipped: tagged release, quickstart ≤ 30 minutes on a laptop.
- p95 control-plane API latency < 300 ms at launch-scale load.

**Estimate.** 10–14 eng-months.

## P2 — Multi-Cloud + Marketplace Beta

**Scope.** Azure and GCP runner parity (OIDC federation, module sets,
compatibility matrix per ADR-0001); drift detection as a scheduled run type
with remediation proposals; remaining core agents (NetOps, DevOps, Identity)
to hardened status; **marketplace beta**: signed OCI agent publishing
(cosign + SBOM per ADR-0009), verification pipeline, install/upgrade flows,
internal + community tiers; GitLab integration; Kafka event-bus adapter.

**Exit criteria.**
- Same example workload provisions on AWS, Azure, and GCP through identical
  TAP workflows.
- ≥ 10 external (non-core-team) agents published through the verification
  pipeline; install-to-first-run < 15 minutes.
- Drift detection running on all design-partner workspaces with < 5% false
  positives.

**Estimate.** 12–16 eng-months.

## P3 — Enterprise Tier

**Scope.** The commercial `tap-enterprise` capabilities (ADR-0007): SSO/SCIM
(Entra ID, Okta); advanced RBAC (custom roles, ABAC administration); **dedicated
cells** (per-tenant control plane via the cell architecture in the
[SaaS deployment guide](saas/saas-deployment-guide.md)); **compliance packs**
(SOC2/ISO27001/HIPAA/PCI policy bundles + evidence export from `compliance/`
mappings); audit log export (SIEM); air-gapped install path; Sentinel
migration adapter GA; support SLA machinery.

**Exit criteria.**
- TAP's own SOC 2 Type I complete; Type II window open.
- Two paying enterprise tenants on dedicated cells in production.
- SCIM-driven onboarding/offboarding round-trips against Entra ID and Okta.
- Air-gapped reference install documented and tested quarterly.

**Estimate.** 12–16 eng-months.

## P4 — SaaS GA

**Scope.** Multi-tenant SaaS at general availability: self-service signup and
tenant onboarding; billing and metering on `cost.*` events (per-workspace,
per-run, agent-token metering per [commercialization](saas/commercialization.md));
multi-region cells with region pinning; published SLAs + status page;
marketplace GA with enterprise rev-share; 24×7 on-call with the runbooks in
the [operations guide](guides/operations-guide.md) battle-tested.

**Exit criteria.**
- 99.9% control-plane availability over a full quarter, measured against the
  published SLO.
- Billing accurate against metering replay to within 0.1%; dunning and
  overage flows live.
- Tenant onboard (signup → first governed run) < 1 hour unassisted;
  offboard/export flows exercised by real departures.
- Unit economics at or better than the gross-margin targets in the
  commercialization plan.

**Estimate.** 10–14 eng-months.

---

Total to SaaS GA: roughly 50–68 eng-months of core platform work. Sequencing
risk concentrates in P1 (the governed-run core must be right) and P3
(compliance work is calendar-bound, not effort-bound — start audits early).
