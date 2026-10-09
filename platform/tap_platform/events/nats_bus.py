"""NATS JetStream event bus (TAP default).

One stream ``TAP`` captures ``tap.>``; per-tenant isolation comes from the
subject hierarchy ``tap.{tenant_id}.*.*`` plus account-level NATS permissions
in hardened deployments. R3 replication in production (ARCHITECTURE.md §9).
"""

from __future__ import annotations

import json

import nats
from nats.aio.client import Client as NatsClient
from nats.js import JetStreamContext
from nats.js.api import RetentionPolicy, StorageType, StreamConfig

from tap_platform.config import Settings, get_settings
from tap_platform.events.bus import Event, EventBus, EventHandler

STREAM_NAME = "TAP"
STREAM_SUBJECTS = ["tap.>"]


class NatsEventBus(EventBus):
    """JetStream-backed publish/subscribe."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._nc: NatsClient | None = None
        self._js: JetStreamContext | None = None

    async def connect(self) -> None:
        """Connect and idempotently ensure the TAP stream exists."""
        self._nc = await nats.connect(self._settings.nats_url)
        self._js = self._nc.jetstream()
        try:
            await self._js.add_stream(
                StreamConfig(
                    name=STREAM_NAME,
                    subjects=STREAM_SUBJECTS,
                    retention=RetentionPolicy.LIMITS,
                    storage=StorageType.FILE,
                    max_age=30 * 24 * 3600,  # 30 days
                )
            )
        except Exception:
            # Stream already exists (or is managed externally): update instead.
            await self._js.update_stream(
                StreamConfig(name=STREAM_NAME, subjects=STREAM_SUBJECTS)
            )

    async def close(self) -> None:
        """Drain and close the connection."""
        if self._nc is not None:
            await self._nc.drain()
            self._nc = None
            self._js = None

    async def publish(self, event: Event) -> None:
        """Publish with the event id as Nats-Msg-Id for server-side dedupe."""
        if self._js is None:
            raise RuntimeError("NatsEventBus.connect() must be called before publish()")
        await self._js.publish(
            event.subject,
            json.dumps(event.model_dump()).encode(),
            headers={"Nats-Msg-Id": event.id},
        )

    async def subscribe(
        self, subject_filter: str, handler: EventHandler, *, durable_name: str | None = None
    ) -> None:
        """Push-subscribe with explicit acks; nak on handler failure."""
        if self._js is None:
            raise RuntimeError("NatsEventBus.connect() must be called before subscribe()")

        async def _on_message(msg: "nats.aio.msg.Msg") -> None:
            try:
                event = Event.model_validate(json.loads(msg.data.decode()))
                await handler(event)
                await msg.ack()
            except Exception:
                await msg.nak(delay=5)

        await self._js.subscribe(
            subject_filter,
            durable=durable_name,
            cb=_on_message,
            manual_ack=True,
            stream=STREAM_NAME,
        )
