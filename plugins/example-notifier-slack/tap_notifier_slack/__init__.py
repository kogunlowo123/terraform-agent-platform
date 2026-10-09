"""Example TAP notifier plugin: Slack webhook notifications for run events.

Registered under the ``tap.notifiers`` entry-point group as ``slack``.
Configure with the ``TAP_SLACK_WEBHOOK_URL`` environment variable (or pass the
URL explicitly). Subscribes naturally to ``tap.*.run.*`` subjects.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

import httpx

__version__ = "0.1.0"

__all__ = ["SlackNotifier", "__version__"]


class _EventLike(Protocol):
    """Structural type matching tap_platform.events.bus.Event."""

    id: str
    subject: str
    tenant_id: str
    payload: dict[str, Any]
    occurred_at: str


_EMOJI_BY_EVENT = {
    "run.plan_finished": ":clipboard:",
    "run.awaiting_approval": ":raised_hand:",
    "run.apply.succeeded": ":white_check_mark:",
    "run.failed": ":x:",
    "run.drift_detected": ":warning:",
}


class SlackNotifier:
    """Posts TAP run lifecycle events to a Slack incoming webhook."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.environ.get("TAP_SLACK_WEBHOOK_URL", "")
        if not self.webhook_url:
            raise ValueError("TAP_SLACK_WEBHOOK_URL is required for the slack notifier")
        self._http = httpx.AsyncClient(timeout=10)

    async def notify(self, event: _EventLike) -> None:
        """Format the event and POST it to the webhook (at-least-once)."""
        event_name = event.subject.split(".", 2)[-1]  # strip 'tap.{tenant}.'
        emoji = _EMOJI_BY_EVENT.get(event_name, ":gear:")
        run_id = str(event.payload.get("run_id", "n/a"))
        text = (
            f"{emoji} *{event_name}* — run `{run_id}` "
            f"(tenant `{event.tenant_id[:8]}…`, {event.occurred_at})"
        )
        response = await self._http.post(self.webhook_url, json={"text": text})
        response.raise_for_status()

    async def aclose(self) -> None:
        """Release the HTTP client."""
        await self._http.aclose()
