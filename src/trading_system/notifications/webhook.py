from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading
from collections.abc import Callable

import httpx

from trading_system.core.ops import EventRecord

_logger = logging.getLogger(__name__)

DEFAULT_EVENTS: frozenset[str] = frozenset({
    "order.filled",
    "risk.rejected",
    "pattern.alert",
    "system.error",
    "portfolio.reconciliation.position_adjusted",
})

_QUEUE_MAX = 200
_SENTINEL = None  # shutdown signal


class WebhookNotifier:
    """Fire-and-forget webhook notifier backed by a single bounded worker thread."""

    def __init__(
        self,
        url: str,
        events: frozenset[str] = DEFAULT_EVENTS,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.url = url
        self.events = events
        self.timeout_seconds = timeout_seconds
        self._queue: queue.Queue = queue.Queue(maxsize=_QUEUE_MAX)
        self._worker = threading.Thread(
            target=self._run_worker,
            daemon=True,
            name="webhook-worker",
        )
        self._worker.start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_worker(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while True:
                payload = self._queue.get()
                if payload is _SENTINEL:
                    break
                try:
                    loop.run_until_complete(self._send(payload))
                except Exception:
                    _logger.warning("Webhook worker error", exc_info=True)
        finally:
            loop.close()

    async def _send(self, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                resp = await client.post(self.url, json=payload)
                resp.raise_for_status()
                return
            except Exception:
                pass
            # 1 retry
            try:
                resp = await client.post(self.url, json=payload)
                resp.raise_for_status()
            except Exception:
                _logger.warning(
                    "Webhook delivery failed after retry: event=%s url=%s",
                    payload.get("event"),
                    self.url,
                    exc_info=True,
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify(self, record: EventRecord) -> None:
        if record.event not in self.events:
            return
        payload = {
            "event": record.event,
            "timestamp": record.timestamp,
            "payload": record.payload,
            "source": "trading-system",
        }
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            _logger.warning(
                "Webhook queue full (%d), dropping event: %s", _QUEUE_MAX, record.event
            )

    def as_subscriber(self) -> Callable[[EventRecord], None]:
        return self.notify

    def shutdown(self, timeout: float = 5.0) -> None:
        """Drain the queue and stop the worker. Call on process exit if needed."""
        self._queue.put(_SENTINEL)
        self._worker.join(timeout=timeout)


def build_webhook_notifier() -> WebhookNotifier | None:
    url = os.getenv("TRADING_SYSTEM_WEBHOOK_URL", "").strip()
    if not url:
        return None
    events_str = os.getenv(
        "TRADING_SYSTEM_WEBHOOK_EVENTS",
        "order.filled,risk.rejected,pattern.alert,system.error,"
        "portfolio.reconciliation.position_adjusted",
    )
    events = frozenset(e.strip() for e in events_str.split(",") if e.strip())
    timeout = float(os.getenv("TRADING_SYSTEM_WEBHOOK_TIMEOUT", "5"))
    return WebhookNotifier(url=url, events=events, timeout_seconds=timeout)
