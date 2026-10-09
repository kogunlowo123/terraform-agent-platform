# TAP Commercialization Plan

Status: v1.0 working plan · Owners: founding team
Related: [ADR-0007 Licensing](../adr/0007-licensing.md) · [Roadmap](../roadmap.md) · [Multi-tenant design](multi-tenant-design.md)

Model: open-core (ADR-0007). The Apache 2.0 core wins adoption; the business
sells what organizations need to run it at enterprise scale, plus the hosted
service, plus a marketplace take.

---

## 1. MVP Feature List (Launch — end of Roadmap P1)

The OSS launch and the first cloud offering share one feature bar:

- Governed runs on AWS: plan → policy gate → approval → apply → verify, with
  compensation/rollback, encrypted + versioned state, OIDC federation.
- Three hardened agents: Infrastructure, SecOps, CostOps.
- OPA policy packs (terraform, cost, baseline security) with `opa test` CI
  patterns; GitHub integration (PR plans, checks, webhook runs); Slack
  approvals; `tap` CLI; audit trail with export.
- Cloud-only at launch: hosted control plane (pooled tier), team RBAC
  (built-in roles), usage dashboard.

Explicitly not in MVP: multi-cloud, marketplace, SSO/SCIM, dedicated cells —
sequenced in the [roadmap](../roadmap.md) P2/P3.

## 2. Enterprise Tier (Fortune 500)

Sold as the `tap-enterprise` add-on / dedicated SaaS tier (ADR-0007 boundary:
things organizations buy, not things engineers need):

- **SSO/SCIM** (Entra ID, Okta) with automated joiner/leaver flows.
- **Advanced RBAC/ABAC** — custom roles, attribute policies, admin UI.
- **Audit export** — streaming SIEM integration (Splunk, Sentinel, Datadog),
  signed audit attestations.
- **Dedicated cells** — single-tenant control plane, region pinning, CMK,
  private networking ([deployment guide](saas-deployment-guide.md)).
- **Compliance packs** — SOC2/ISO/HIPAA/PCI policy bundles + evidence export
  mapped in `compliance/`.
- **Support SLAs** — 24×7, 30-minute P1, named TAM
  ([SLA tiers](saas-deployment-guide.md)).
- **Air-gapped option** — offline installer, artifact mirror, no-egress
  licensing.
- **Premium agents** — advanced FinOps optimization, compliance remediation,
  migration (TFC/TFE → TAP) agents.

## 3. Marketplace Business Model

The marketplace is the network-effect moat: agents and modules, distributed
as signed OCI artifacts (ADR-0009), in three tiers (internal / community /
enterprise).

- **Community agents**: free, license-declared, verification-scanned. No
  revenue; they exist to make TAP the default place agents live.
- **Enterprise agents**: paid, sold through the marketplace with a
  **rev-share — 80/20 publisher/platform** at launch (deliberately generous;
  the scarce resource is publishers, not margin).
- **Verification program**: paid annual review (security review, guardrail
  audit, support commitment) granting a "Verified" badge and eligibility to
  run in enterprise tenants. Unverified agents never run in pooled SaaS
  ([security guide](../guides/security-guide.md)).
- Platform operators (MSPs) can run private marketplaces — an enterprise
  feature.

## 4. Pricing Model (sketch — validate with design partners)

Three meters, aligned to value and to COGS:

| Meter | What it prices | Rationale |
|---|---|---|
| Per workspace / month | Standing footprint under management | Predictable base; maps to incumbent (TFC/Spacelift) buying habits |
| Per run | Execution consumption beyond included volume | Scales with actual usage; spiky consumers pay for their spikes |
| Agent-token metering | LLM spend by agent executions, passed through with margin | The genuinely new cost driver; pass-through+margin avoids both subsidizing heavy agent use and gouging light use |

Sketch: **Free** (OSS self-host, unlimited; cloud: 3 workspaces, community
agents, capped runs/tokens) → **Pro** ~$29/workspace/mo + run and token
overage → **Enterprise** custom (dedicated cell platform fee + volume
commits). All three meters ride the `cost.*` metering stream
([deployment guide §4](saas-deployment-guide.md)).

## 5. Competitive Positioning

| Competitor | Their center of gravity | TAP's wedge |
|---|---|---|
| Terraform Cloud/HCP | Incumbent run platform; BSL estate, IBM-owned | License-risk-free engine choice (ADR-0001), agents, open core, Sentinel migration adapter |
| Spacelift | Best-in-class CI-for-IaC, policy-first | TAP automates *intent*, not pipelines: governed autonomous remediation, agent marketplace |
| Scalr | TFC-compatible hierarchy + OPA | Same + agents; TAP's OSS core vs. closed SaaS |
| Port | Developer portal / catalog | TAP executes; portals catalog. Port is an integration, not a competitor, until they execute |
| Humanitec | Platform orchestration abstraction | TAP keeps Terraform's semantics (plan artifact, policy gates) instead of abstracting them away |

One-line position: **the open, agentic IaC platform — pipelines automated
runs; TAP governs agents that operate infrastructure.** The honest risk in
this table: every incumbent is bolting on AI features. The moat is not "has
agents" but the governed-execution substrate (ADRs 0002/0003/0009) that makes
autonomous infra mutation *safe to buy* — that is the hard part to retrofit.

## 6. GTM Phases

1. **OSS community (P1–P2).** Ship a genuinely complete core; win the
   practitioners burned by the BSL change. Metrics: stars → weekly active
   self-hosted installs (opt-in telemetry), Discord/Slack size, external
   contributors, marketplace publishers.
2. **PLG cloud (P2–P3).** Self-serve cloud with free tier; convert self-host
   evaluators who don't want to operate Temporal. Metrics: signup → first
   governed run < 1 hour, free→paid conversion, net run growth per tenant.
3. **Enterprise sales (P3–P4).** Sales-assisted motion on top of PLG signal
   (self-host installs inside F500 domains are the pipeline). Land: one team
   on Pro / a migration from TFC. Expand: dedicated cell + compliance packs.
   Metrics: ACV, pipeline from OSS signal, TFC-migration win rate.

## 7. Cost Model (COGS per tenant)

Pooled-tier monthly COGS sketch, mid-size tenant (20 workspaces, 400 runs,
moderate agent use):

| Component | Driver | Est. / mo |
|---|---|---|
| Compute (control-plane share + runners) | Runner job-minutes dominate; spot for plans | $40–80 |
| LLM tokens | Agent executions; the volatile line | $50–200 |
| Storage (state versions, audit, vector) | Grows with history; lifecycle policies cap it | $5–15 |
| Data transfer, KMS, misc | Egress, key ops | $5–10 |
| Allocated shared (Temporal, NATS, observability) | Per-cell fixed ÷ tenants | $10–20 |

Implications: token COGS is the margin wildcard — hence metered pass-through
pricing and per-tenant budgets ([multi-tenant design §4](multi-tenant-design.md));
runner compute is optimizable (spot, right-sizing) independent of pricing.

**Gross-margin targets:** blended ≥ 70% at GA, ≥ 75% at scale; enterprise
dedicated cells priced to ≥ 65% (cells carry fixed COGS, so the platform fee
floors at cell cost ÷ 0.35). Token-heavy tenants are margin-managed by
construction (pass-through+margin), not by hope. Review quarterly against
actual `cost.*` metering data.
