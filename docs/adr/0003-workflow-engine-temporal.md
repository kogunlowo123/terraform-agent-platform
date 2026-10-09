# ADR-0003: Workflow Engine — Temporal

Status: Accepted
Date: 2026-10-09

## Context

The governed run lifecycle — plan → policy → approve → apply → verify
([ARCHITECTURE.md §5](../architecture/ARCHITECTURE.md)) — is a long-running,
stateful, failure-prone process:

- A run can wait **days** at an approval gate.
- Every step must survive control-plane restarts and deploys without losing
  position or re-executing side effects.
- A failed apply needs **compensation**: rollback plan or state restore, run
  as reliably as the forward path.
- Approvals arrive asynchronously from Slack, API, or the portal and must be
  delivered to exactly the right in-flight run.
- Enterprises will audit the exact history of every run.

Queue-plus-worker architectures push all of this onto application code:
idempotency bookkeeping, timers, dead-letter handling, resumption logic. That
code is where infra platforms rot.

## Options Considered

| Option | Durability | Human approval | Compensation | Long-running runs | Ops cost | Verdict |
|---|---|---|---|---|---|---|
| Temporal | Durable execution, full event history, replay | Signals + timers (SLA escalation) native | Saga pattern first-class | Unbounded workflow lifetime | One more stateful service | **Accepted** |
| Homegrown DAG engine (Postgres + workers) | Hand-built checkpoint tables | Hand-built | Hand-built | Hand-built timer service | Lowest footprint, highest defect surface | Rejected: we would spend years rebuilding Temporal's hard parts |
| Airflow | Scheduler-oriented, task retries | Poor — not interactive | Weak | Designed for batch DAGs, not event-driven waits | Mature but heavy | Rejected: wrong execution model (scheduled batch vs. durable reactive) |
| Step Functions / cloud-native | Managed durability | Callbacks | Supported | Supported | Zero self-hosting | Rejected: couples core to one cloud; TAP must run on-prem and air-gapped |
| Argo Workflows | Pod-level retries | Suspend/resume, coarse | Weak | K8s-bound | Light if already on K8s | Rejected: container DAGs, not stateful business workflows; no typed signals |

## Decision

**Temporal** owns the run lifecycle. `RunWorkflow` in `platform/` is the single
implementation of the governed lifecycle; agents, API calls, and webhooks all
start or signal it — nothing else sequences a run.

- **Activities** wrap the side-effecting steps: schedule runner job, evaluate
  policy, emit events, record audit. Activities are idempotent by
  `run_id + step`.
- **Signals** carry approvals and cancellations; a timer alongside the
  approval wait enforces the approval SLA and triggers escalation.
- **Saga compensation** implements rollback: on apply failure, the
  compensation path executes the rollback plan or restores the last good
  `STATE_VERSION`, with the same gating rules as any apply.
- Deployment: self-hosted Temporal (bundled in the dev compose stack and the
  production Helm chart) or **Temporal Cloud** for SaaS cells — the workflow
  code is identical.

## Consequences

Positive:

- Run state is never lost: deploys, crashes, and node failures are invisible
  to in-flight runs.
- The full event history of every workflow doubles as an execution-grade audit
  record, complementing the `AUDIT_LOG` table.
- Approval, timeout, retry, and rollback logic is declarative workflow code —
  testable with Temporal's replay test framework in `tests/`.
- Versioned workflow definitions let us evolve the lifecycle without stranding
  in-flight runs.

Negative:

- **Operational weight**: Temporal server + its Postgres persistence is a real
  distributed system to run. Mitigations: Temporal Cloud option for SaaS;
  bundled, opinionated Helm values for self-hosters; Temporal shares the
  existing Postgres HA story rather than introducing a new datastore.
- Workflow determinism constraints (no raw I/O or clock reads in workflow
  code) are a learning curve; the developer guide covers the rules and CI
  runs replay tests to catch violations.
- Version skew between workflow code and in-flight histories requires
  discipline: all lifecycle changes go through Temporal's patching API.
