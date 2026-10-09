# ADR-0007: Licensing — Apache 2.0 Core, Open-Core Model

Status: Accepted
Date: 2026-10-09

## Context

TAP is both an open platform meant to win community adoption and the
foundation of a commercial SaaS ([commercialization](../saas/commercialization.md)).
The license must serve both, and the Terraform relicensing saga (ADR-0001) is
the cautionary tale on every prospective user's mind: the ecosystem has fresh,
specific memories of a BSL conversion destroying trust overnight.

Forces:

- Enterprise adoption requires a license legal departments pre-approve.
- Infrastructure tooling without a **patent grant** is a non-starter for large
  contributors.
- A future **CNCF path** (credibility, neutrality, distribution) requires an
  OSI-approved license — CNCF accepts Apache 2.0.
- We need *some* protection for the commercial business — but the protection
  must not poison the core's adoption flywheel.

## Options Considered

| Option | Adoption / trust | Patent grant | SaaS-competitor protection | CNCF compatible | Verdict |
|---|---|---|---|---|---|
| Apache 2.0 | Gold standard; pre-approved everywhere | Explicit grant + retaliation clause | None in the license itself | Yes | **Accepted for core** |
| MIT | Equally trusted, simpler | None — a real gap for infra with large corporate contributors | None | Yes | Rejected: loses the patent grant for no gain |
| Elastic License 2.0 | "Source-available" — rejected by OSS purists and many legal departments | n/a (not OSI) | Blocks offering TAP as a managed service | No | Rejected for core |
| BSL 1.1 | Post-Terraform, actively toxic in the IaC community specifically | Converts to open after change date | Strong — blocks competitive use | No | Rejected for core |

## Decision

**The core platform is Apache 2.0** — everything in this repository: control
plane, SDK, agent framework, the core agents, runners, policies, modules,
observability, and docs. The commercial strategy is **open-core**, with the
boundary drawn at *organizational* capability rather than platform capability:

- **Open (this repo):** the full governed-run platform. A team can self-host
  TAP and run production infrastructure with policy gates, approvals, audit,
  and the core agent set. The open product must be genuinely complete — a
  crippled core kills the flywheel the license exists to create.
- **Proprietary (separate `tap-enterprise` repo, commercial license):**
  SSO/SCIM provisioning, advanced RBAC (custom roles, ABAC administration
  UI), dedicated cells, compliance packs, premium agents, and the hosted
  SaaS's billing/metering plane. These sell to buyers, not users.
- **Marketplace agents carry their own licenses**, declared in the agent
  manifest and surfaced at install; the marketplace verification pipeline
  checks license compatibility with the deploying tier.
- Contributions require a DCO sign-off (no CLA with relicensing rights): a
  deliberate, structural commitment that the core *cannot* quietly convert to
  BSL later — the inverse of the Terraform story, and we say so in the README.

### Why not BSL for the core

BSL would protect revenue against a hyperscaler offering TAP-as-a-service —
a speculative threat at our stage — at the certain cost of: no CNCF path, no
pre-approved legal status, hostile reception in the exact community
(IaC practitioners burned by HashiCorp) we need to win, and a standing excuse
for every potential contributor to not contribute. For a platform whose moat
is agents, modules, and marketplace network effects rather than the engine
itself, the trade is plainly bad.

## Consequences

Positive:

- Zero-friction adoption and contribution; Apache 2.0's patent grant protects
  users and contributors alike.
- CNCF submission remains open as a strategic option.
- The enterprise boundary is legible: features organizations buy, not
  features engineers need.

Negative:

- Nothing stops a cloud vendor from hosting TAP's core commercially. Accepted:
  our defensibility is velocity, the marketplace, and the enterprise tier.
- Open-core requires permanent boundary discipline; every feature triages
  open vs. enterprise, and mistakes in the open direction are irreversible.
- Two repos, two release trains; enterprise must build against the core's
  public extension points (`plugins/`, SDK) only, which we enforce in CI.
