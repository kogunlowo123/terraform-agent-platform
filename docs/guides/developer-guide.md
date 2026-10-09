# TAP Developer Guide

Audience: engineers building on or contributing to TAP — platform code,
agents, Terraform modules, policies.
Related: [README](../../README.md) · [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) · [ADR index](../adr/README.md)

---

## 1. Local Development Setup

Prerequisites: Docker (compose v2), Python 3.12, `make`, and either
`tofu` or `terraform` on PATH (OpenTofu is the default engine — ADR-0001).

```bash
# Clone, then bring up the full local stack
./scripts/dev-up.sh
```

`dev-up.sh` starts the docker compose stack:

| Service | Purpose | Default port |
|---|---|---|
| Postgres | System of record, RLS tenancy, agent checkpoints | 5432 |
| Redis | Working memory, sessions, locks | 6379 |
| NATS (JetStream) | Event bus — `run.*`, `agent.*`, `policy.*`, `cost.*` | 4222 |
| Qdrant | Semantic memory (default `VectorStore`) | 6333 |
| Temporal | Run lifecycle workflows (+ Temporal UI) | 7233 / 8233 |
| OPA | Policy evaluation | 8181 |

Then install and run the control plane:

```bash
pip install -e ./platform -e ./sdk
tap-server --config platform/config/dev.yaml

# Smoke test: a governed plan against the example stack
tap run plan --workspace demo --dir examples/aws-vpc-baseline
```

The dev config seeds a `demo` tenant and workspace, disables external OIDC
(local token auth), and points all services at the compose stack. Nothing in
dev mode can reach a real cloud unless you configure OIDC trust explicitly.

## 2. Repository Layout Tour

The full tree is in the [README](../../README.md). What matters day-to-day:

- `platform/` — control plane. FastAPI services, Temporal workflows,
  `platform/api/openapi.yaml` (the contract — change it first, code second),
  `platform/db/schema.sql`.
- `agents/core/` — base agent framework: `BaseAgent`, Memory Manager,
  guardrails, agent comms. Agent authors build on this, never on LangGraph
  directly (ADR-0002).
- `agents/<domain>/` — the core agents (secops, netops, costops, …). Each is
  a reference implementation of the SDK patterns.
- `sdk/` — what third-party agent authors install (`tap-sdk`).
- `plugins/` — the extension interfaces: `IaCRunner`, `EventBus`,
  `VectorStore`, policy adapters. Implement these to swap infrastructure.
- `terraform/` — reusable modules by provider; `policies/` — Rego;
  `tests/` — pytest + `opa test` suites + terratest.

## 3. Building an Agent with the SDK

An agent is: a manifest, a LangGraph graph built from SDK primitives, typed
tools, and tests.

```bash
tap-sdk new my-drift-agent   # scaffolds the layout below
```

```
my-drift-agent/
├── agent.yaml          # manifest
├── graph.py            # StateGraph definition
├── tools/              # typed tools (exposed via MCP)
├── tests/
└── Dockerfile          # built into a signed OCI artifact
```

**Manifest (`agent.yaml`).** Declares identity and — critically — the
guardrail envelope. The registry rejects agents whose tools exceed their
declared capabilities:

```yaml
apiVersion: tap/v1
kind: Agent
metadata:
  name: my-drift-agent
  version: 0.1.0
  license: Apache-2.0
spec:
  description: Detects drift and proposes remediation plans
  capabilities: [run.plan.read, drift.detect]   # no mutate capability
  tools: [terraform_plan, module_search]
  memory: {working: true, episodic: true, semantic: true}
  guardrails:
    mutation_budget: 0          # read-only agent
    scope: workspace            # never cross-workspace
```

**Graph (`graph.py`).** Subclass `BaseAgent`, define typed state, wire nodes.
The standard shape is plan → act → verify → report; every mutating edge is
automatically routed through the guardrail pre-check. Checkpointing to
Postgres is wired by the base class — do not add your own persistence.

**Tools.** A tool is a typed function registered with the SDK; the SDK
publishes it over MCP so it is callable from TAP agents and from external MCP
clients alike. Tools must be idempotent or declare they are not; non-idempotent
tools cannot be retried by the orchestrator.

**Tests.** `tap-sdk` ships a graph test harness: feed a recorded state, assert
the traversal and tool calls. CI requires graph tests plus guardrail tests
(prove the agent *cannot* exceed its manifest).

Publishing: `tap-sdk publish` builds the OCI artifact, signs it (cosign),
attaches the SBOM, and submits to the registry/marketplace pipeline
(ADR-0009).

## 4. Adding a Terraform Module

Modules live under `terraform/<provider>/<name>/` and follow a fixed standard —
CI rejects deviations:

- `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` (pinned provider
  and engine constraints; must pass on both Terraform and OpenTofu per the
  ADR-0001 compatibility matrix).
- Every variable and output has a `description`; variables have types;
  secrets are never variables with defaults.
- **No backend or provider blocks** — the platform generates backend/provider
  config per workspace at run time.
- `examples/` — at least one runnable example per module; examples are what
  terratest executes.
- `README.md` — generated by terraform-docs; do not hand-edit the tables.
- Tests: a terratest suite under `tests/` exercising the example (plan-only
  by default; apply tests run in the nightly cloud account).

## 5. PR Workflow and CI Gates

- Branch from `main`; one logical change per PR; link an issue or ADR for
  anything architectural. Architectural decisions require an ADR *before* the
  implementation PR ([ADR process](../adr/README.md)).
- Required CI gates, in order of failure frequency:
  1. Lint + types: ruff, mypy --strict (platform and SDK), terraform fmt,
     Regal (Rego lint).
  2. Unit: pytest (platform, SDK, agents), `opa test` with coverage floor.
  3. Contract: OpenAPI diff check — breaking changes need a version bump and
     explicit label.
  4. Module matrix: changed modules run terratest against the engine/provider
     matrix.
  5. Security: Checkov/tfsec/Trivy on changed modules and images; secret scan
     on the diff.
- Two approvals for `platform/db/`, `policies/`, and anything under
  `agents/core/` guardrails; one elsewhere. Squash merge; commits follow
  Conventional Commits.
