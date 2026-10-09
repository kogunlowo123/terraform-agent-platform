"""Kafka event bus adapter (stub) for enterprises with existing Kafka estates.

Subjects map to topics by replacing dots with hyphens per level where topic
naming rules require it; tenant isolation uses topic ACLs. Install the
``kafka`` extra (``pip install tap-platform[kafka]``) and select it via
``TAP_EVENT_BUS=kafka``.
"""

from __future__ import annotations

from tap_platform.config import Settings, get_settings
from tap_platform.events.bus import Event, EventBus, EventHandler


class KafkaEventBus(EventBus):
    """aiokafka-backed publish/subscribe (stub)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def connect(self) -> None:
        """Start an AIOKafkaProducer against ``kafka_bootstrap_servers``."""
        raise NotImplementedError("AIOKafkaProducer start + topic ensure (admin client)")

    async def close(self) -> None:
        """Stop producer and all consumers."""
        raise NotImplementedError("producer/consumer stop")

    async def publish(self, event: Event) -> None:
        """Produce to the topic derived from the subject, keyed by tenant_id."""
        raise NotImplementedError("producer.send_and_wait(topic, value, key=tenant_id)")

    async def subscribe(
        self, subject_filter: str, handler: EventHandler, *, durable_name: str | None = None
    ) -> None:
        """Consume via a consumer group named after durable_name."""
        raise NotImplementedError("AIOKafkaConsumer(group_id=durable_name) poll loop")
