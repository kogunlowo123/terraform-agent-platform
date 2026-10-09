"""Event bus abstraction (NATS JetStream default, Kafka adapter stub).

Subjects follow ``tap.{tenant_id}.{domain}.{event}``, e.g.
``tap.3f2c...a1.run.plan_finished``. Consumers must be idempotent by
``(run_id, sequence)`` (ARCHITECTURE.md §9).
"""

from __future__ import annotations

__all__ = ["bus", "kafka_bus", "nats_bus"]
