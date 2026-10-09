# Architecture Decision Records

ADRs capture the significant, hard-to-reverse decisions behind TAP. Each record
states the context at decision time, the options weighed, the decision, and its
consequences. ADRs are immutable once Accepted; a changed decision gets a new
ADR that supersedes the old one.

Reference architecture: [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)

## Index

| ID | Title | Status | Date |
|---|---|---|---|
| [0001](0001-iac-engine-dual-runner.md) | IaC engine: Terraform + OpenTofu dual runner | Accepted | 2026-10-09 |
| [0002](0002-agent-orchestration-langgraph.md) | Agent orchestration: LangGraph + MCP | Accepted | 2026-10-09 |
| [0003](0003-workflow-engine-temporal.md) | Workflow engine: Temporal | Accepted | 2026-10-09 |
| [0004](0004-event-bus-nats.md) | Event bus: NATS JetStream (Kafka adapter) | Accepted | 2026-10-09 |
| [0005](0005-policy-engine-opa.md) | Policy engine: OPA native, Sentinel adapter | Accepted | 2026-10-09 |
| [0006](0006-agent-memory.md) | Agent memory: 3-tier with pluggable vector store | Accepted | 2026-10-09 |
| [0007](0007-licensing.md) | Licensing: Apache 2.0 core, open-core model | Accepted | 2026-10-09 |
| [0008](0008-control-plane-python-fastapi.md) | Control plane: Python 3.12 + FastAPI + Postgres RLS | Accepted | 2026-10-09 |
| [0009](0009-execution-security.md) | Execution security: ephemeral runners, OIDC, signed artifacts | Accepted | 2026-10-09 |

## Format

Every ADR follows the same structure:

- **Title** — decision, stated as a noun phrase.
- **Status** — Proposed / Accepted / Superseded by ADR-NNNN.
- **Date** — date of acceptance.
- **Context** — forces, constraints, and the problem that made a decision necessary.
- **Options Considered** — table of candidates with tradeoffs.
- **Decision** — what we chose, and the specific shape of the choice.
- **Consequences** — positive and negative, honestly stated.

## Authoring a New ADR

1. Copy the structure above into `docs/adr/NNNN-short-slug.md` (next free number).
2. Open a PR; the Platform Architecture Group reviews.
3. On merge, set Status to Accepted and add the row to the index table here.
