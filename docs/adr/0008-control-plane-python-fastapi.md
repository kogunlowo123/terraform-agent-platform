# ADR-0008: Control Plane — Python 3.12 + FastAPI + Postgres RLS

Status: Accepted
Date: 2026-10-09

## Context

The control plane (`platform/`) hosts the API gateway, agent orchestrator,
registry, marketplace service, and AI gateway. The language choice interacts
with two prior decisions: the agent runtime is LangGraph (ADR-0002), and the
SDK that third parties use to build agents must feel native to the people who
build agents today. The database must enforce multi-tenancy at a layer
application bugs cannot bypass.

Forces:

- **Agent-ecosystem gravity is decisive.** LangGraph, the LLM provider SDKs,
  embedding tooling, and evaluation frameworks are Python-first. A non-Python
  control plane means FFI bridges or a split codebase between orchestrator
  and API.
- The API must be **OpenAPI-first**: the contract in `platform/api/openapi.yaml`
  drives client SDKs, the CLI, and the portal.
- Control-plane throughput is modest by design — heavy work (plan/apply,
  scans) happens in runners (ADR-0009); agent latency is LLM-dominated. The
  hot path is CRUD, authz, and workflow signaling.
- Multi-tenant data isolation must not depend on every query author
  remembering a `WHERE tenant_id = ?`.

## Options Considered

| Option | Agent ecosystem fit | API contracts | Raw performance | Verdict |
|---|---|---|---|---|
| Python 3.12 + FastAPI | Native — LangGraph, LLM SDKs, SDK authors' language | OpenAPI generated from typed Pydantic models | Adequate with async; not the bottleneck | **Accepted** |
| Go | Weak — no LangGraph; agent runtime would still be Python, splitting the codebase | Good (oapi-codegen) | Excellent | Rejected: buys performance we don't need at the cost of the ecosystem we do |
| TypeScript/Node | Moderate LLM ecosystem; LangGraph.js lags Python | Good (zod-openapi) | Good | Rejected: second-tier agent ecosystem, no advantage elsewhere |
| Rust | None for agents | Workable | Best | Rejected: velocity cost unjustifiable for a CRUD-and-orchestration plane |
| JVM (Kotlin/Java) | Weak for agents | Good | Good | Rejected: same split-codebase problem as Go |

Database: PostgreSQL was uncontested (relational integrity for runs/approvals/
audit, RLS, advisory locks for state locking, LISTEN/NOTIFY, pgvector as a
small-install vector option per ADR-0006). The considered alternative — app-layer
tenancy filtering over any SQL store — was rejected because one missed filter
is a cross-tenant data breach.

## Decision

- **Python 3.12** across `platform/` and `sdk/`, fully type-annotated, mypy
  strict in CI; **FastAPI** for all HTTP services; Pydantic models as the
  single source of the OpenAPI 3.1 contract
  ([ARCHITECTURE.md §7](../architecture/ARCHITECTURE.md)).
- **PostgreSQL with row-level security on `tenant_id`** for every
  tenant-scoped table. The API layer sets the tenant context
  (`SET LOCAL app.tenant_id`) from the authenticated principal per
  transaction; application roles have no RLS-bypass privilege. Schema:
  `platform/db/schema.sql`.
- Performance posture, in order: async I/O end-to-end (asyncpg, httpx);
  stateless API and orchestrator pods behind HPA for horizontal scale;
  runners and Temporal carry all heavy or long-running work; Redis absorbs
  hot reads. uvloop and read replicas are the escalation path if profiling
  ever demands it.

## Consequences

Positive:

- One language from control plane through SDK to agents: contributors and
  marketplace authors work in the ecosystem they already know, and the
  orchestrator imports LangGraph directly.
- OpenAPI-first keeps CLI, portal, and customer clients honest; contract
  diffs are reviewable in PRs.
- RLS makes tenant isolation a database property, testable directly in
  `tests/` by attempting cross-tenant reads.

Negative:

- Python's ceiling is real: no free lunch on CPU-bound paths. Accepted
  because the architecture routes CPU-bound work to runners by construction;
  the mitigation list above is ordered and documented so we scale out before
  rewriting.
- RLS adds per-query planner overhead and complicates ad-hoc operational
  queries (operators must set tenant context deliberately — which is, in
  fact, the point).
- Strict typing discipline is load-bearing in a dynamic language; CI enforces
  it rather than convention.
