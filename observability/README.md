# TAP Observability

OTel SDK everywhere -> OTel Collector -> Prometheus (metrics), Loki (logs),
Tempo (traces). See [`../docs/architecture/ARCHITECTURE.md`](../docs/architecture/ARCHITECTURE.md) §11.

## Layout

| Path | Purpose |
|---|---|
| [`otel-collector.yaml`](otel-collector.yaml) | Collector config (ConfigMap): OTLP receivers, batch + tenant attribution processors, Prometheus/Loki/Tempo exporters |
| [`prometheus/rules.yaml`](prometheus/rules.yaml) | PrometheusRule with the TAP alert set |
| [`grafana/dashboards/tap-runs.json`](grafana/dashboards/tap-runs.json) | Runs dashboard (uid `tap-runs`) |
| [`grafana/dashboards/tap-agents.json`](grafana/dashboards/tap-agents.json) | Agents dashboard (uid `tap-agents`) |

Everything here is deployed by the ArgoCD observability app
([`../gitops/platform/apps/observability.yaml`](../gitops/platform/apps/observability.yaml));
dashboards are picked up by the Grafana sidecar via the `grafana_dashboard`
ConfigMap label.

## Metric contract

Emitted by the control plane, workflow engine, and AI gateway. Every series
carries `tenant_id` (the collector inserts `untenanted` when missing — that
label showing up is a bug in the emitting service).

| Metric | Type | Labels | Source |
|---|---|---|---|
| `tap_runs_total` | counter | `status`, `action`, `tenant_id` | workflow engine |
| `tap_runs_in_state` | gauge | `state`, `tenant_id` | workflow engine |
| `tap_run_duration_seconds` | histogram | `action`, `tenant_id` | workflow engine |
| `tap_policy_decisions_total` | counter | `decision` (deny/soft_fail/advisory/allow), `package`, `tenant_id` | policy service |
| `tap_drift_resources` | gauge | `workspace`, `environment`, `tenant_id` | drift workflows |
| `tap_runner_queue_depth` | gauge | — | runner controller |
| `tap_agent_executions_total` | counter | `agent`, `status`, `tenant_id` | orchestrator |
| `tap_agent_tokens_total` | counter | `agent`, `model`, `tenant_id` | AI gateway |
| `tap_agent_token_budget_daily` | gauge | `agent`, `tenant_id` | AI gateway |
| `tap_agent_guardrail_violations_total` | counter | `agent`, `rule`, `tenant_id` | guardrail layer |
| `tap_workflow_last_progress_timestamp_seconds` | gauge | `workflow_type` | workflow engine |

## Alerts

Defined in [`prometheus/rules.yaml`](prometheus/rules.yaml):

| Alert | Severity | Fires when |
|---|---|---|
| `RunFailureRateHigh` | critical | >20% of runs failing over 15m |
| `PolicyDenialSpike` | warning | denial rate >4x the prior-6h baseline for 30m |
| `DriftDetected` | warning | any workspace reports drifted resources for 10m |
| `RunnerQueueBacklog` | warning | >25 queued runs for 10m |
| `AgentTokenBudgetExceeded` | warning | daily token spend over per-agent budget |
| `TemporalWorkflowStuck` | critical | Run/Drift workflow with no progress for >1h |

## Local development

The dev compose stack exposes Prometheus and Grafana; `scripts/dev-up.sh`
prints the URLs. Import the dashboards by UID — panels only need the
`prometheus` datasource.
