from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol

_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_SENSITIVE_KEYWORDS = ("secret", "token", "password", "api_key", "apikey")


class StructuredLogFormat(StrEnum):
    JSON = "json"
    KEY_VALUE = "key_value"


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.01


@dataclass(slots=True)
class TimeoutPolicy:
    timeout_seconds: float = 1.0


@dataclass(slots=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 3
    reset_timeout_seconds: float = 5.0


class SecretProvider(Protocol):
    def get_secret(self, name: str) -> str:
        """Load one secret value from a protected source."""


class EnvSecretProvider:
    def get_secret(self, name: str) -> str:
        value = os.getenv(name)
        if value is None or not value.strip():
            raise RuntimeError(f"Missing required secret: {name}")
        return value


@dataclass(slots=True)
class EventRecord:
    event: str
    severity: str
    correlation_id: str
    timestamp: str
    payload: dict[str, Any]


@dataclass(slots=True)
class OrderCreatedEvent:
    symbol: str
    side: str
    quantity: Decimal


@dataclass(slots=True)
class OrderRejectedEvent:
    symbol: str
    side: str
    quantity: Decimal
    reason: str


@dataclass(slots=True)
class OrderFilledEvent:
    symbol: str
    side: str
    requested_quantity: Decimal
    filled_quantity: Decimal
    fill_price: Decimal
    fee: Decimal
    status: str


@dataclass(slots=True)
class RiskRejectedEvent:
    symbol: str
    requested_quantity: Decimal
    current_position: Decimal
    price: Decimal


@dataclass(slots=True)
class ExceptionEvent:
    error_type: str
    message: str


class StructuredLogger:
    def __init__(
        self,
        name: str,
        log_format: StructuredLogFormat = StructuredLogFormat.JSON,
    ) -> None:
        self._logger = logging.getLogger(name)
        self._format = log_format

    def emit(self, event: str, severity: int, payload: dict[str, Any]) -> None:
        correlation_id = get_or_create_correlation_id()
        record = EventRecord(
            event=event,
            severity=logging.getLevelName(severity),
            correlation_id=correlation_id,
            timestamp=datetime.now(tz=UTC).isoformat(),
            payload=redact_payload(payload),
        )
        self._logger.log(severity, self._serialize(record))

    def _serialize(self, record: EventRecord) -> str:
        if self._format == StructuredLogFormat.KEY_VALUE:
            parts = [
                f"event={record.event}",
                f"severity={record.severity}",
                f"correlation_id={record.correlation_id}",
                f"timestamp={record.timestamp}",
            ]
            for key, value in sorted(record.payload.items()):
                parts.append(f"{key}={value}")
            return " ".join(parts)

        return json.dumps(
            {
                "event": record.event,
                "severity": record.severity,
                "correlation_id": record.correlation_id,
                "timestamp": record.timestamp,
                "payload": record.payload,
            },
            default=str,
            sort_keys=True,
        )


@dataclass(slots=True)
class CircuitBreakerState:
    failures: int = 0
    opened_at: float | None = None

    def can_execute(self, policy: CircuitBreakerPolicy, now: float) -> bool:
        if self.opened_at is None:
            return True
        if now - self.opened_at >= policy.reset_timeout_seconds:
            self.failures = 0
            self.opened_at = None
            return True
        return False

    def on_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def on_failure(self, policy: CircuitBreakerPolicy, now: float) -> None:
        self.failures += 1
        if self.failures >= policy.failure_threshold:
            self.opened_at = now


def ensure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def get_or_create_correlation_id() -> str:
    existing = _CORRELATION_ID.get()
    if existing is not None:
        return existing
    generated = uuid.uuid4().hex
    _CORRELATION_ID.set(generated)
    return generated


@contextmanager
def correlation_scope(correlation_id: str | None = None):
    token = _CORRELATION_ID.set(correlation_id or uuid.uuid4().hex)
    try:
        yield _CORRELATION_ID.get()
    finally:
        _CORRELATION_ID.reset(token)


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload: dict[str, Any] = {}
    for key, value in payload.items():
        normalized = key.lower()
        if any(secret_key in normalized for secret_key in _SENSITIVE_KEYWORDS):
            safe_payload[key] = "***"
        else:
            safe_payload[key] = value
    return safe_payload


def event_payload(event: Any) -> dict[str, Any]:
    return asdict(event)


def execute_with_resilience(
    operation: str,
    callback,
    *,
    retry: RetryPolicy,
    timeout: TimeoutPolicy,
    circuit_breaker: CircuitBreakerPolicy,
    circuit_state: CircuitBreakerState,
) -> Any:
    now = time.monotonic()
    if not circuit_state.can_execute(circuit_breaker, now):
        raise RuntimeError(f"Circuit breaker open for operation '{operation}'.")

    for attempt in range(1, retry.max_attempts + 1):
        started_at = time.monotonic()
        try:
            result = callback()
            elapsed = time.monotonic() - started_at
            if elapsed > timeout.timeout_seconds:
                raise TimeoutError(
                    f"Operation '{operation}' exceeded timeout {timeout.timeout_seconds}s."
                )
            circuit_state.on_success()
            return result
        except (TimeoutError, OSError, ValueError) as exc:
            circuit_state.on_failure(circuit_breaker, time.monotonic())
            if attempt == retry.max_attempts:
                raise RuntimeError(
                    f"Operation '{operation}' failed after {retry.max_attempts} attempts."
                ) from exc
            time.sleep(retry.backoff_seconds)
