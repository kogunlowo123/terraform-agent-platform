# TAP Agent Core

How TAP domain agents are composed, how they talk to each other, and how humans
stay in the loop. Every directory under `agents/` (except this one) is a domain
agent built from the same skeleton.

## The standard graph

Every domain agent is a `tap_sdk.BaseAgent` subclass whose `build_graph()`
returns a compiled LangGraph `StateGraph` over the shared `AgentState`
(`task, context, plan, actions, results, errors, requires_approval`):

```
analyze --> plan --> policy_precheck --+--> act --> verify --> report
                                       |     ^         |
                                       |     +--retry--+
                                       +--(denied)---------> report
```

- **analyze** — classify the task, pull semantic memory, resolve scope.
- **plan** — produce an ordered list of intended actions (typed tool calls).
- **policy_precheck** — evaluate the plan against OPA *before* anything runs
  (`policy_check` tool). Hard deny short-circuits to `report`. Soft deny or a
  mutating plan sets `requires_approval = True`.
- **approval** — interrupt node. Graphs are compiled with
  `interrupt_before=["approval"]`; the orchestrator (or Temporal workflow)
  resumes the thread only after a recorded human approval. Non-mutating plans
  skip this node entirely.
- **act** — execute the plan with guardrails enforced (scope allowlist,
  mutation budget, dry-run default). Mutations only ever run a previously
  evaluated plan artifact.
- **verify** — post-conditions: drift check, health probes, scan re-run.
  Failures route back to `act` (bounded retries) or on to `report` with errors.
- **report** — emit the output contract JSON (see
  [`prompts/system_base.md`](prompts/system_base.md)), persist episodic memory,
  publish `agent.<name>.completed` on NATS.

Domain agents may insert extra nodes (e.g. SecOps adds `severity_gate` between
`act` and `verify`; Identity forces `requires_approval = True` for every
mutation regardless of policy result).

## Checkpointing

`build_graph(checkpointer=...)` accepts any LangGraph `BaseCheckpointSaver`.
In production the orchestrator passes the Postgres checkpointer so interrupted
threads (approvals) survive restarts; the SDK test harness passes
`MemorySaver`.

## Delegation over NATS (request/reply)

Agents never import each other. Cross-domain work is delegated through the
event bus:

- Subject convention: `agent.<name>.request` (request/reply with a 60s
  deadline), `agent.<name>.events` (pub/sub progress).
- Payload: `{"task": str, "context": dict, "trace_id": str, "tenant_id": str,
  "budget": {"tokens": int, "mutations": int}}` — the delegate's reply is the
  same output contract JSON every agent emits from `report`.
- The caller records the delegation in `state["actions"]` so the audit trail
  shows exactly which agent did what.

The orchestrator ([`orchestrator.py`](orchestrator.py)) is the supervisor
implementation of this pattern: it resolves capabilities against the Agent
Registry, fans out requests, and aggregates replies.

## Escalation to humans

Three triggers, one mechanism:

1. `requires_approval = True` (policy soft-fail, mutation plan, destroy,
   identity mutation) — graph interrupts at `approval`; Temporal signals a
   human via Slack/API with an SLA timer.
2. Critical findings (SecOps `severity_gate`) — always escalate, never
   auto-remediate criticals.
3. Unrecoverable errors after retry budget — `report` emits
   `status: "escalated"` and publishes `agent.<name>.escalation`.

Approvals are recorded (who, when, what plan artifact) and are part of the
immutable audit trail.

## Prompts

[`prompts/system_base.md`](prompts/system_base.md) is the shared system prompt
(role, guardrails, output contract). Each agent appends its small delta file
(`prompts/<name>.md`). Deltas state only what differs: domain scope, extra
nodes, extra hard rules.

## Adding a new domain agent

1. `mkdir agents/<name>` with `agent.yaml`, `graph.py`, `tools.py`,
   `README.md` (copy an existing agent as the template).
2. Manifest must declare: name, version, domain, capabilities,
   required_tools, memory.semantic_collection, guardrails, model.
3. Register it: `tap agents publish agents/<name>` — the registry validates
   the manifest and makes the capabilities discoverable to the orchestrator.
