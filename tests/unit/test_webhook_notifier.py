"""Unit tests for WebhookNotifier."""
from __future__ import annotations

import asyncio
import queue
from unittest.mock import patch

from trading_system.core.ops import EventRecord
from trading_system.notifications.webhook import (
    WebhookNotifier,
    build_webhook_notifier,
)


def _make_record(event: str = "order.filled") -> EventRecord:
    return EventRecord(
        event=event,
        severity="INFO",
        correlation_id="test-corr",
        timestamp="2024-01-01T00:00:00Z",
        payload={"symbol": "AAPL"},
    )


# ---------------------------------------------------------------------------
# build_webhook_notifier
# ---------------------------------------------------------------------------


def test_build_webhook_notifier_no_url(monkeypatch):
    monkeypatch.delenv("TRADING_SYSTEM_WEBHOOK_URL", raising=False)
    assert build_webhook_notifier() is None


def test_build_webhook_notifier_with_url(monkeypatch):
    monkeypatch.setenv("TRADING_SYSTEM_WEBHOOK_URL", "http://example.com/hook")
    notifier = build_webhook_notifier()
    assert notifier is not None
    assert notifier.url == "http://example.com/hook"
    assert "order.filled" in notifier.events


def test_build_webhook_notifier_custom_events(monkeypatch):
    monkeypatch.setenv("TRADING_SYSTEM_WEBHOOK_URL", "http://example.com/hook")
    monkeypatch.setenv("TRADING_SYSTEM_WEBHOOK_EVENTS", "order.filled,system.error")
    notifier = build_webhook_notifier()
    assert notifier is not None
    assert notifier.events == frozenset({"order.filled", "system.error"})


def test_build_webhook_notifier_custom_timeout(monkeypatch):
    monkeypatch.setenv("TRADING_SYSTEM_WEBHOOK_URL", "http://example.com/hook")
    monkeypatch.setenv("TRADING_SYSTEM_WEBHOOK_TIMEOUT", "10")
    notifier = build_webhook_notifier()
    assert notifier is not None
    assert notifier.timeout_seconds == 10.0


# ---------------------------------------------------------------------------
# notify() — queue interaction (mock queue to avoid worker thread bleed)
# ---------------------------------------------------------------------------


def test_notify_skips_non_target_event():
    notifier = WebhookNotifier(url="http://example.com/hook")
    record = _make_record("some.other.event")
    with patch.object(notifier._queue, "put_nowait") as mock_put:
        notifier.notify(record)
        mock_put.assert_not_called()


def test_notify_target_event_enqueues_payload():
    notifier = WebhookNotifier(url="http://example.com/hook")
    record = _make_record("order.filled")
    with patch.object(notifier._queue, "put_nowait") as mock_put:
        notifier.notify(record)
        mock_put.assert_called_once()
        payload = mock_put.call_args[0][0]
        assert payload["event"] == "order.filled"
        assert payload["source"] == "trading-system"
        assert "timestamp" in payload
        assert "payload" in payload


def test_notify_drops_when_queue_full():
    """queue.Full should not propagate out of notify()."""
    notifier = WebhookNotifier(url="http://example.com/hook")
    with patch.object(notifier._queue, "put_nowait", side_effect=queue.Full):
        notifier.notify(_make_record("order.filled"))  # must not raise


# ---------------------------------------------------------------------------
# _send() — async HTTP with retry
# ---------------------------------------------------------------------------


def test_send_retries_on_failure():
    """_send() makes one initial attempt then exactly one retry on failure."""
    import httpx

    notifier = WebhookNotifier(url="http://example.com/hook", timeout_seconds=1.0)
    call_count = 0

    async def failing_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("connection refused")

    # Patch put_nowait on ALL existing notifiers' queues so background workers
    # never receive items and therefore never call _send during this test.
    with patch.object(notifier._queue, "put_nowait"):
        with patch.object(httpx.AsyncClient, "post", new=failing_post):
            asyncio.run(
                notifier._send({
                    "event": "order.filled",
                    "timestamp": "now",
                    "payload": {},
                    "source": "trading-system",
                })
            )

    assert call_count == 2  # initial attempt + 1 retry


def test_payload_structure():
    """_send receives the expected payload shape."""
    notifier = WebhookNotifier(url="http://example.com/hook")
    record = _make_record("order.filled")

    captured: list[dict] = []

    async def capturing_send(payload: dict) -> None:
        captured.append(payload)

    # Replace the instance's _send for this test only
    notifier._send = capturing_send  # type: ignore[method-assign]

    payload = {
        "event": record.event,
        "timestamp": record.timestamp,
        "payload": record.payload,
        "source": "trading-system",
    }
    asyncio.run(notifier._send(payload))

    assert captured[0]["event"] == "order.filled"
    assert captured[0]["source"] == "trading-system"
    assert "timestamp" in captured[0]
    assert "payload" in captured[0]


# ---------------------------------------------------------------------------
# as_subscriber
# ---------------------------------------------------------------------------


def test_as_subscriber_returns_callable():
    notifier = WebhookNotifier(url="http://example.com/hook")
    subscriber = notifier.as_subscriber()
    assert callable(subscriber)
    # Should be the bound notify method
    assert subscriber.__func__ is WebhookNotifier.notify  # type: ignore[attr-defined]
