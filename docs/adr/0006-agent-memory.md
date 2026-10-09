# ADR-0006: Agent Memory — Three Tiers, Pluggable Vector Store

Status: Accepted
Date: 2026-10-09

## Context

TAP agents need memory with three distinct access patterns, and conflating
them produces either a slow cache or an unqueryable database:

1. **Working memory** — the current task's scratch state: sub-second access,
   TTL-bounded, disposable.
2. **Episodic memory** — what happened: every agent execution, step, decision,
   and checkpoint, durable and auditable, joined against runs and tenants.
3. **Semantic memory** — what was learned: embeddings over past incidents,
   module docs, runbooks, and tenant conventions, retrieved by similarity
   with metadata filters.

Constraints: strict tenant isolation in every tier; the whole stack must run
in the dev compose file and air-gapped; no new datastore where an existing one
already fits; vector-DB choice is volatile enough that it must be swappable.

## Options Considered

| Option | Fit | Verdict |
|---|---|---|
| Single store for all tiers (Postgres + pgvector only) | Simple ops; but working-memory churn thrashes the system of record, and pgvector filtering/scale lags dedicated engines | Rejected as the only store; pgvector acceptable for small self-hosted installs via the plugin interface |
| Three tiers: Redis + Postgres + dedicated vector DB | Each tier on the engine built for its access pattern; Redis and Postgres already exist in the platform | **Accepted** |
| Vector default: Qdrant | OSS (Apache 2.0), single binary, strong payload filtering, collection-level isolation | **Accepted as default** |
| Vector default: Pinecone | Excellent managed service; proprietary, no self-host — breaks air-gapped | Plugin target only |
| Vector default: Weaviate | Capable OSS; heavier operationally, module system adds surface | Plugin target only |
| Vector default: Milvus | Scales furthest; multi-component deployment (etcd, MinIO) too heavy for default | Plugin target only |
| Vector default: Chroma | Lightest for dev; immature multi-tenant/authz story | Plugin target only |

## Decision

Three-tier memory, managed by the Memory Manager in `agents/core/`
([ARCHITECTURE.md §4, §6](../architecture/ARCHITECTURE.md)):

- **Working — Redis.** Keys TTL'd to the agent execution; also serves locks
  and rate counters. Nothing in Redis is ever the only copy of anything.
- **Episodic — Postgres.** `agent_executions` and `CHECKPOINT` rows under the
  same RLS tenancy as all platform data; doubles as the LangGraph
  checkpointer store (ADR-0002), so deterministic replay and episodic memory
  are the same substrate.
- **Semantic — vector DB behind a `VectorStore` plugin interface**
  (`plugins/`): upsert, similarity search with metadata filters, collection
  lifecycle. **Qdrant is the default**: Apache 2.0, single binary (fits
  compose and air-gapped), payload filtering strong enough for
  tenancy-scoped queries. Adapters planned for Pinecone, Weaviate, Milvus,
  and Chroma.
- **Namespacing:** every semantic collection is named
  `tenant:{id}:agent:{name}`. The Memory Manager derives the namespace from
  the execution context — agent code cannot name an arbitrary collection.
  Higher isolation tiers get physically separate collections or instances
  ([multi-tenant design](../saas/multi-tenant-design.md)).

## Consequences

Positive:

- Each tier runs on an engine shaped for its access pattern; no cross-tier
  interference (embedding backfills cannot slow approval queries).
- Episodic memory inherits Postgres's RLS, backup, and audit posture for free.
- The `VectorStore` interface makes vector-DB churn a plugin concern — the
  default can change without touching agent code, and enterprises can bring
  their incumbent.
- Enforced namespacing makes cross-tenant memory leakage a code-review-visible
  violation rather than a runtime accident.

Negative:

- Three stores to operate even in the smallest install; mitigated by the
  compose stack and Helm chart treating them as one unit, and Redis/Postgres
  being required by the platform regardless.
- Embedding-model versioning is an unsolved lifecycle cost: model upgrades
  require collection re-indexing, which the Memory Manager must support as a
  background job.
- The plugin interface is a lowest-common-denominator API; store-specific
  features (Qdrant quantization, Pinecone serverless tiers) are reachable
  only via adapter-specific config, not platform code.
