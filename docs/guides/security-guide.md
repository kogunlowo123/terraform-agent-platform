# TAP Security Guide

Audience: security engineers evaluating or operating TAP; platform engineers
configuring guardrails.
Related: [ARCHITECTURE.md §12](../architecture/ARCHITECTURE.md) · [ADR-0009](../adr/0009-execution-security.md) · [Multi-tenant design](../saas/multi-tenant-design.md)

---

## 1. Threat Model

Trust boundaries follow the container model in
[ARCHITECTURE.md §3](../architecture/ARCHITECTURE.md): user → API gateway;
control plane → agent orchestrator (LLM-influenced code); orchestrator →
runner fleet (tenant cloud credentials); marketplace → everything (third-party
code). The LLM is treated as an **untrusted reasoning component**: helpful,
never authoritative.

### STRIDE over the key containers and flows

| Threat | Vector (container) | Category | Primary controls |
|---|---|---|---|
| Prompt injection into agents | Hostile text in PR descriptions, resource tags, module docs, or memory reaches the orchestrator's LLM context and steers tool calls | Tampering / Elevation | Guardrails outside the LLM loop: manifest capability allowlists, mutation budgets, policy pre-check on every mutating edge; plan-artifact gate — injected intent still cannot apply an unevaluated plan; AI gateway strips/flags instruction-shaped content in retrieved context |
| Malicious marketplace agent | Trojaned agent artifact (Marketplace Service → Runner/Orchestrator) | Tampering / Elevation | cosign signature + SBOM verification at admission; marketplace verification pipeline (static scan, license, capability review); manifest-enforced capability envelope at runtime; tier policy: unverified agents never run in pooled SaaS |
| State exfiltration | Read of state versions (contain secrets-adjacent data) via API, bucket, or a compromised runner | Information disclosure | Per-tenant KMS envelope encryption; Postgres RLS on state metadata; runner receives only its workspace's state via short-lived URL; egress NetworkPolicy blocks arbitrary destinations; access audited per state version |
| Runner escape | Breakout from the ephemeral runner pod to node or neighbor pods | Elevation of privilege | Non-root, read-only rootfs, no privilege escalation, seccomp RuntimeDefault; dedicated tainted node pools (dedicated per tenant on siloed tier); single-use pods limit persistence; no control-plane credentials present in runner namespace |
| Credential theft | Theft of cloud credentials from runner, control plane, or config | Spoofing / Info disclosure | No static cloud keys exist to steal (OIDC federation, 15-min workspace-scoped tokens — ADR-0009); platform secrets are KMS/Vault references resolved at point of use; tokens unusable outside the issuing run's window |
| Approval forgery | Replaying or spoofing an approval signal to Temporal | Spoofing / Repudiation | Approvals are authenticated API calls bound to run ID + plan hash, recorded with principal and timestamp in `AUDIT_LOG`; Slack actions verify signed payloads server-side |
| Audit tampering | Deletion/modification of audit rows | Repudiation | Append-only audit table (no UPDATE/DELETE grants); SIEM export (enterprise tier) provides an off-platform copy |
| Event-bus abuse | Tenant consumer reads another tenant's subjects | Information disclosure | Broker-enforced subject permissions per tenant account (ADR-0004) |

## 2. Controls Mapping

Compliance-framework control mappings (SOC2, ISO 27001, HIPAA, PCI-DSS, GDPR,
NIST 800-53, CIS) live in `compliance/`, keyed by the control IDs above so an
auditor can trace framework → TAP control → implementing code/config.
Security scanning (Checkov, tfsec, Trivy, Terrascan) runs in CI and at plan
time; findings attach to the run record and are policy-evaluable.

## 3. Agent Guardrail Configuration

Guardrails are enforced in `agents/core/`, **outside** anything the LLM can
influence, and configured in three layers (most restrictive wins):

1. **Agent manifest** (`agent.yaml`) — the author's declared envelope:
   capabilities, tool list, `mutation_budget`, scope (`workspace` |
   `project` | `tenant`).
2. **Tenant policy** — platform admins cap what any agent may do per
   environment, e.g. `mutation_budget: 0` for all agents in `prod` except an
   allowlist, mandatory dry-run-first in regulated workspaces.
3. **Platform invariants** — not configurable: policy pre-check before every
   mutating tool call; destroy always human-approved; apply only from an
   evaluated plan artifact; agents cannot alter their own manifest, budget,
   or memory namespace.

Practical guidance: start every new agent at `mutation_budget: 0` (read-only)
in production and promote on evidence; keep `scope: workspace` unless there is
a demonstrated need; alert on guardrail denials — they are either an attack or
a broken agent, and both matter.

## 4. Secrets Handling

- **No secrets in TAP's database, state, or agent memory.** Workspace
  variables marked sensitive hold *references* (KMS/Vault paths); resolution
  happens in the runner at execution time and resolved values never leave it.
- State is encrypted per-tenant regardless (defense in depth — Terraform
  state may embed secret-bearing attributes despite best practice).
- The AI gateway redacts detected secrets and PII from prompts and traces
  before provider calls and before OTel capture
  ([ARCHITECTURE.md §10](../architecture/ARCHITECTURE.md)).
- CI secret-scans every diff; a committed credential fails the build and
  triggers rotation of that credential, not just removal.

## 5. Responsible Disclosure

- Report vulnerabilities to **security@tap-platform.dev** (PGP key published
  at the repo root on OSS launch). Please do not open public issues for
  security reports.
- Acknowledgment within 2 business days; triage and severity (CVSS) within
  7; coordinated disclosure target 90 days, negotiable for complex fixes.
- In-scope: this repository, published artifacts/images, the SaaS service.
  Out of scope: volumetric DoS, social engineering, third-party marketplace
  agents (report those to the marketplace abuse queue, which can pull the
  artifact platform-wide).
- Fixed vulnerabilities receive a GitHub security advisory + CVE; reporters
  are credited unless they opt out. No bug bounty at this stage; that changes
  with SaaS GA.
