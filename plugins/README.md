# TAP Plugin Architecture

TAP extends through standard Python entry points — a plugin is just an
installable package that registers a class under one of the TAP entry-point
groups. No forking, no control-plane changes.

## Entry-point groups

| Group | Contract (ABC) | Built-ins |
|---|---|---|
| `tap.runners` | `tap_platform.runner.base.IaCRunner` | `terraform`, `opentofu` |
| `tap.vector_stores` | `tap_platform.memory.base.VectorStore` | `qdrant` (default), `pinecone` (stub) |
| `tap.event_buses` | `tap_platform.events.bus.EventBus` | `nats` (default), `kafka` (stub) |
| `tap.policy_engines` | policy evaluation adapter (OPA-native; Sentinel adapter ships here) | `opa` |
| `tap.notifiers` | `notify(event) -> None` async callable class | — (see the Slack example) |

The platform discovers implementations at startup via
`importlib.metadata.entry_points(group="tap....")` and selects them by
configuration (e.g. `TAP_VECTOR_STORE=qdrant`, `TAP_EVENT_BUS=nats`).

## Writing a plugin

1. Create a package with a `pyproject.toml` that declares the entry point:

   ```toml
   [project.entry-points."tap.notifiers"]
   slack = "tap_notifier_slack:SlackNotifier"
   ```

2. Implement the group's contract. Notifiers implement:

   ```python
   class Notifier(Protocol):
       async def notify(self, event: Event) -> None: ...
   ```

   where `Event` is `tap_platform.events.bus.Event`.

3. Install it next to the platform (`pip install .`) — TAP picks it up on
   restart. Enterprise deployments distribute plugins as signed wheels through
   the marketplace pipeline.

## Conventions

- snake_case everywhere; UUIDs as `str`; timestamps UTC ISO 8601.
- Plugins must be async-first and must not block the event loop.
- A plugin never receives cloud credentials; it sees platform events and APIs
  only, scoped to the tenant that configured it.
- Version plugins with semver and pin the `tap-platform` major you target.

## Example

[`example-notifier-slack/`](example-notifier-slack/) is a minimal working
notifier plugin: a `pyproject.toml` with the entry point and one module that
posts run lifecycle events to a Slack webhook.
