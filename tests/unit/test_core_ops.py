import json
import logging
from decimal import Decimal

import pytest

from trading_system.core.ops import (
    CircuitBreakerPolicy,
    CircuitBreakerState,
    OrderCreatedEvent,
    RetryPolicy,
    StructuredLogFormat,
    StructuredLogger,
    TimeoutPolicy,
    correlation_scope,
    event_payload,
    execute_with_resilience,
    redact_payload,
)


def test_redact_payload_masks_sensitive_fields() -> None:
    payload = {"api_key": "abc", "token_value": "def", "symbol": "BTCUSDT"}

    redacted = redact_payload(payload)

    assert redacted["api_key"] == "***"
    assert redacted["token_value"] == "***"
    assert redacted["symbol"] == "BTCUSDT"


def test_structured_logger_emits_json_with_correlation_id(caplog) -> None:
    logger = StructuredLogger("trading_system.tests", log_format=StructuredLogFormat.JSON)

    with correlation_scope("corr-123"):
        with caplog.at_level(logging.INFO):
            logger.emit(
                "order.created",
                logging.INFO,
                event_payload(OrderCreatedEvent("BTCUSDT", "buy", Decimal("1"), "2024-01-01T00:00:00Z")),
            )

    message = caplog.records[-1].message
    body = json.loads(message)
    assert body["correlation_id"] == "corr-123"
    assert body["event"] == "order.created"


def test_subscriber_receives_emitted_event() -> None:
    logger = StructuredLogger("trading_system.tests.sub", log_format=StructuredLogFormat.JSON)
    received = []
    logger.subscribe(received.append)

    logger.emit("test.event", logging.INFO, {"key": "value"})

    assert len(received) == 1
    assert received[0].event == "test.event"


def test_unsubscribe_stops_delivery() -> None:
    logger = StructuredLogger("trading_system.tests.unsub", log_format=StructuredLogFormat.JSON)
    received = []
    callback = received.append  # store reference for identity comparison
    logger.subscribe(callback)
    logger.unsubscribe(callback)

    logger.emit("test.event", logging.INFO, {})

    assert len(received) == 0


def test_subscriber_exception_does_not_affect_others() -> None:
    logger = StructuredLogger("trading_system.tests.exc", log_format=StructuredLogFormat.JSON)
    received = []

    def bad_subscriber(record):
        raise RuntimeError("boom")

    logger.subscribe(bad_subscriber)
    logger.subscribe(received.append)

    logger.emit("test.event", logging.INFO, {})

    assert len(received) == 1


def test_execute_with_resilience_opens_circuit_breaker_after_failures() -> None:
    state = CircuitBreakerState()
    retry = RetryPolicy(max_attempts=1, backoff_seconds=0)
    timeout = TimeoutPolicy(timeout_seconds=1)
    breaker = CircuitBreakerPolicy(failure_threshold=1, reset_timeout_seconds=10)

    with pytest.raises(RuntimeError):
        execute_with_resilience(
            operation="io-call",
            callback=lambda: (_ for _ in ()).throw(ValueError("boom")),
            retry=retry,
            timeout=timeout,
            circuit_breaker=breaker,
            circuit_state=state,
        )

    with pytest.raises(RuntimeError, match="Circuit breaker open"):
        execute_with_resilience(
            operation="io-call",
            callback=lambda: "ok",
            retry=retry,
            timeout=timeout,
            circuit_breaker=breaker,
            circuit_state=state,
        )
