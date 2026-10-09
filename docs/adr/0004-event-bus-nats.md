# ADR-0004: Event Bus — NATS JetStream Default, Kafka Adapter

Status: Accepted
Date: 2026-10-09

## Context

TAP is event-driven at the seams: run state transitions (`run.*`), agent
lifecycle and inter-agent comms (`agent.*`), policy decisions (`policy.*`),
and cost/metering events (`cost.*`) all flow over a bus. Requirements:

- **Per-tenant isolation** on the bus itself — a tenant's consumers must not
  be able to subscribe to another tenant's subjects.
- At-least-once delivery with replay for metering and audit consumers.
- Request/reply for agent-to-agent delegation, not just pub/sub.
- Must run in the dev compose stack, in a single-node edge deployment, and in
  a multi-AZ SaaS cell — same system everywhere.
- Enterprises with existing Kafka estates will demand Kafka integration.

## Options Considered

| Option | Ops footprint | Tenant isolation | Delivery semantics | Request/reply | Ecosystem | Verdict |
|---|---|---|---|---|---|---|
| NATS JetStream | Single static binary; 3-node cluster for HA | Subject hierarchy + accounts; per-tenant permissions natively | At-least-once, streams with replay, exactly-once windows | Native | Smaller than Kafka's, sufficient | **Accepted as default** |
| Kafka | ZooKeeper-less still heavy: brokers, partitions, rebalancing | ACL-based, coarser; topic-per-tenant explodes partitions | At-least-once / EOS transactions | Not native (RPC anti-pattern) | Largest: connectors, stream processors | Adapter, not default |
| RabbitMQ | Moderate | Vhost-per-tenant workable | At-least-once | Native | Mature but aging stream support | Rejected: streams/replay weaker than JetStream, no advantage over NATS |
| Redis Streams | Already deployed (ADR-0006) | Weak — no subject-level authz model | At-least-once with consumer groups | Hand-rolled | n/a | Rejected: conflates cache and bus failure domains |
| Cloud-native (SNS/SQS, Pub/Sub) | Zero self-host | Per-cloud IAM | Varies | No | Per-cloud | Rejected for core: breaks on-prem/air-gapped parity |

## Decision

**NATS JetStream** is the default and bundled event bus, behind an `EventBus`
plugin interface in `plugins/` with a **Kafka adapter** as the first alternate
implementation.

- Subject scheme: `tap.{tenant_id}.{domain}.{event}` — e.g.
  `tap.t_42.run.completed`, `tap.t_42.cost.run_metered`. NATS account
  permissions grant each tenant-scoped consumer only its own subtree;
  platform consumers (metering, audit) hold cross-tenant read on specific
  domains.
- JetStream streams per domain with R3 replication in production
  ([ARCHITECTURE.md §9](../architecture/ARCHITECTURE.md)); consumers are
  idempotent by `run_id + seq`.
- Agent request/reply (delegation, escalation) uses core NATS; durable
  domains use JetStream.
- The Kafka adapter maps subjects to topics with a tenant-ID header and
  partition key; it targets enterprises that mandate Kafka as the
  integration backbone, not TAP-internal traffic.

## Consequences

Positive:

- One ~20 MB binary covers dev laptop through production cell: the compose
  stack and the Helm chart ship the same system, which keeps dev/prod parity
  honest.
- Subject-per-tenant isolation is enforced by the broker, not by consumer
  discipline — a real security boundary, cheap to audit.
- Metering and billing consume `cost.*` as a replayable stream, decoupled from
  the request path.

Negative:

- Kafka's ecosystem (Connect, ksqlDB, Flink integration) is unavailable on the
  default path; customers who need it bridge via the Kafka adapter, which is a
  second implementation to test and maintain.
- JetStream's operational tooling and hiring pool are thinner than Kafka's;
  mitigated by NATS's much smaller operational surface in the first place.
- The `EventBus` abstraction must stay at the semantic level TAP needs
  (publish, durable subscribe, replay) and resist leaking NATS- or
  Kafka-specific features into platform code.
