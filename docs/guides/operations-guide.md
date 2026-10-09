# TAP Operations Guide

Audience: operators running TAP — self-hosted or as the SaaS team.
Related: [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) · [Security guide](security-guide.md) · [SaaS deployment guide](../saas/saas-deployment-guide.md)

---

## 1. Deployment Topologies

| Topology | Use | Shape |
|---|---|---|
| Docker compose | Dev, evaluation, demos | Entire stack on one host via `./scripts/dev-up.sh`; no HA, no OIDC |
| Kubernetes (Helm) | Production self-hosted | Control-plane deployments (API, orchestrator, registry, marketplace, AI gateway) + Temporal + NATS (R3) + runner namespace; Postgres/Redis/Qdrant in-cluster or managed equivalents |
| Temporal Cloud option | Production, reduced ops | Same Helm chart with the Temporal server disabled and workers pointed at Temporal Cloud; removes the heaviest stateful component (ADR-0003 mitigation) |

Production baseline: multi-AZ node pools; control-plane pods stateless behind
HPA; dedicated node pool(s) for runners with taints so tenant workloads never
co-schedule with the control plane; GitOps-managed via ArgoCD app-of-apps in
`gitops/platform/` ([ARCHITECTURE.md §9](../architecture/ARCHITECTURE.md)).

## 2. Upgrades

- Control plane: rolling deploy; API and orchestrator are stateless.
  Database migrations run as a pre-upgrade Job and must be backward-compatible
  one version (expand/contract pattern) — the previous release must run
  against the migrated schema.
- Temporal workflows: in-flight runs survive upgrades by design; workflow
  code changes ship behind Temporal's versioning/patching API. Never deploy a
  workflow change that fails replay tests.
- Runner images: new image tags take effect on the next run; in-flight jobs
  finish on their pinned image. Engine version additions go through the
  ADR-0001 compatibility matrix first.
- Order: migrate DB → deploy workers → deploy control plane → bump runner
  tags. Rollback is the reverse; schema rollbacks are forward-fixes only.

## 3. Backup and Restore

| Asset | Method | Target |
|---|---|---|
| Postgres (system of record + checkpoints + Temporal persistence) | Continuous WAL archiving + nightly base backup (or managed-DB PITR) | RPO ≤ 5 min |
| State bucket | Versioned object store + cross-region replication; per-tenant KMS keys backed up by the KMS itself | RPO ≈ 0 |
| Qdrant | Nightly snapshot per collection | Rebuildable from Postgres sources if lost |
| NATS JetStream | R3 replication; streams are replayable transit, not system of record | n/a |

Restore drill (quarterly, non-negotiable): restore Postgres PITR to a staging
cell, re-hydrate the control plane via GitOps, verify a seeded run's full
history and a state-version checksum. Control-plane RTO target ≤ 30 min.

State restore for a single workspace: `tap state restore --workspace W
--version N` — creates a new `STATE_VERSION` from the old one (never
overwrites history) and requires the same approval gate as an apply.

## 4. Scaling Runners

Runners are ephemeral K8s Jobs (ADR-0009); scaling is a queue problem:

- Autoscale the runner node pool on pending-Job count (cluster autoscaler or
  Karpenter); pre-pull runner images via DaemonSet to cut start latency.
- Per-tenant concurrency limits and run quotas are enforced in the workflow
  engine *before* Job creation — see
  [noisy-neighbor controls](../saas/multi-tenant-design.md).
- Large tenants on the siloed tier get dedicated node pools; size on peak
  concurrent runs, not run count.
- Watch: Job queue latency (pending → running), image pull time, node-pool
  headroom. Plan capacity for the Monday-morning and end-of-quarter apply
  storms.

## 5. Incident Runbooks

**Stuck run.** Symptom: run in `running` beyond SLO. Check Temporal UI for
the workflow — if the workflow is healthy and waiting, it is an approval or a
long plan, not an incident. If an activity is retrying: inspect the runner Job
(`kubectl -n tap-runners describe job run-<id>`). Dead node → Temporal retries
on a fresh Job automatically. Truly wedged → `tap run cancel --run <id>`
(triggers compensation path); never delete the Job first — let the workflow
own the lifecycle.

**State lock held.** Symptom: runs failing with lock timeout on one workspace.
Locks are Postgres advisory locks tied to a session. Find the holder in
`pg_locks`; if the holding run is alive, wait. If orphaned (crashed runner
whose session persists): `tap state unlock --workspace W --force` — this is
audited and requires the operator role. Never unlock while an apply Job for
that workspace is Running.

**Drift storm.** Symptom: drift detected on many workspaces at once. This is
almost never real drift — suspect a provider API change, a changed data-source
default, or an engine/provider version bump. Pause drift-remediation proposals
tenant-wide (`tap drift pause --tenant T`), diff one representative plan by
hand, pin the suspect provider version, then resume. Never let auto-remediation
run during a storm.

**Policy service outage — fail-closed.** OPA unreachable means **no run
proceeds past the gate**: plans queue, applies block. This is by design; the
platform never fails open. Response: OPA is stateless — restart/scale it;
bundles re-pull from the bundle registry. If the bundle registry itself is
down, OPA serves its last-good bundle from local cache. Communicate queued-run
latency to tenants; do not override the gate. There is deliberately no
"skip policy" switch.

## 6. SLOs

| SLO | Target | Notes |
|---|---|---|
| Control-plane API availability | 99.9% monthly | Gate for SaaS GA |
| API latency p95 (CRUD) | < 300 ms | Excludes run execution |
| Run start latency (accepted → runner executing) | p95 < 60 s | Includes Job scheduling + image pull |
| Approval delivery (gate hit → notification sent) | p95 < 30 s | Slack/API/portal |
| Policy evaluation | p95 < 5 s per plan | OPA eval + normalization |
| Event delivery (`run.*` publish → consumer ack) | p95 < 10 s | JetStream |

Error budgets drive release pace: a blown monthly budget freezes feature
deploys for the affected service until the budget recovers. Dashboards and
alert rules live in `observability/`; golden signals per container are defined
in [ARCHITECTURE.md §11](../architecture/ARCHITECTURE.md).
