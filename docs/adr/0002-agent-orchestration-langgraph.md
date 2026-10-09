# ADR-0002: Agent Orchestration — LangGraph + MCP

Status: Accepted
Date: 2026-10-09

## Context

TAP agents mutate production infrastructure. That single fact disqualifies most
of the agent-framework landscape: conversation-centric frameworks where the LLM
improvises control flow are acceptable for research assistants, not for a
system that runs `apply` against a tenant's AWS account.

Hard requirements for the orchestration layer:

1. **Explicit, inspectable control flow** — the set of states an agent can be
   in, and the edges between them, must be reviewable like code.
2. **Durable checkpointing** — agent state must survive pod restarts and be
   persisted per step, in Postgres alongside the rest of the system of record.
3. **Deterministic replay** — a failed or disputed agent execution must be
   reproducible from its checkpoint history for audit and debugging.
4. **Human-in-the-loop interrupts** — an agent must be able to pause on a
   mutating edge, wait indefinitely for approval, and resume exactly where it
   stopped.
5. **Tool portability** — tenant and marketplace tools should work from TAP's
   own agents *and* from external clients (Claude Code, IDEs, chat surfaces).

## Options Considered

| Option | Control flow | Checkpointing | Replay | Human-in-loop | Verdict |
|---|---|---|---|---|---|
| LangGraph | Explicit StateGraph, typed state | First-class, Postgres saver | Deterministic from checkpoints | Native `interrupt()` on any edge | **Accepted** |
| CrewAI | Role/task abstraction, LLM-mediated delegation | Limited | Weak — conversation-driven | Bolt-on | Rejected: insufficient determinism for infra mutation |
| AutoGen | Multi-agent conversation loops | Limited | Weak — emergent control flow | Bolt-on | Rejected: same class of problem as CrewAI |
| Semantic Kernel | Planner + plugins, .NET-first | Partial | Partial | Partial | Rejected: ecosystem mismatch with Python control plane (ADR-0008) |
| OpenAI Agents SDK | Handoffs + guardrails | Vendor-hosted sessions | Vendor-dependent | Partial | Rejected: couples core orchestration to one LLM vendor; TAP routes across providers via the AI Gateway |
| Homegrown state machine | Full control | Build it ourselves | Build it ourselves | Build it ourselves | Rejected: re-implements LangGraph poorly; no ecosystem leverage |

## Decision

**LangGraph** is the agent runtime. Every TAP agent is a LangGraph
`StateGraph` with a typed state schema, packaged with a manifest
(`agent.yaml`) under `agents/`, built on the base framework in `agents/core/`
and the SDK in `sdk/`.

- Checkpoints persist to **Postgres** (the `CHECKPOINT` entity in
  [ARCHITECTURE.md §6](../architecture/ARCHITECTURE.md)), under the same RLS
  tenancy model as all other data.
- Every mutating edge passes through the guardrail component (scope
  allowlists, mutation budget, policy pre-check) before the tool executes.
- Human approval uses LangGraph interrupts for *agent-level* pauses; *run-level*
  approvals (plan gates) live in Temporal (ADR-0003). The two compose: an
  agent requesting an apply triggers a Temporal workflow, which owns the gate.
- **MCP (Model Context Protocol)** is the tool-exposure standard. Agent tools
  are published as MCP servers, so the same `terraform_plan` or
  `cost_estimate` tool is callable from a TAP agent graph, from Claude Code,
  or from any MCP client a customer points at their TAP tenant.

## Consequences

Positive:

- Agent behavior is a reviewable artifact: graph topology diffs appear in PRs.
- Deterministic replay gives auditors and support a step-by-step record of
  every agent decision, tied to the run audit trail.
- MCP makes TAP's tool surface a distribution channel — developers meet TAP
  inside their existing agentic tooling before they ever open the portal.
- LangGraph's ecosystem velocity (checkpointers, streaming, eval tooling)
  accrues to us.

Negative:

- LangChain-ecosystem dependency churn is real; we pin versions and wrap
  LangGraph behind `agents/core/` so agent authors never import it directly.
- Graph-structured agents are more upfront work than "give the LLM tools and
  a loop"; the SDK's templates and the developer guide mitigate.
- Two interrupt mechanisms (LangGraph, Temporal) require a clear composition
  rule, documented above, to avoid double-gating or gaps.
