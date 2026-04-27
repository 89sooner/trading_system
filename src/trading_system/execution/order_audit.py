from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from trading_system.core.compat import UTC

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit tests
    psycopg = None  # type: ignore[assignment]

_log = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class OrderAuditRecord:
    record_id: str
    scope: str
    owner_id: str
    event: str
    symbol: str | None
    side: str | None
    requested_quantity: str | None
    filled_quantity: str | None
    price: str | None
    status: str | None
    reason: str | None
    timestamp: str
    payload: dict[str, Any]
    broker_order_id: str | None = None


class OrderAuditRepository(Protocol):
    def append(self, record: OrderAuditRecord) -> None:
        ...

    def list(
        self,
        *,
        scope: str | None = None,
        owner_id: str | None = None,
        symbol: str | None = None,
        event: str | None = None,
        limit: int = 100,
    ) -> list[OrderAuditRecord]:
        ...


class FileOrderAuditRepository:
    def __init__(self, base_dir: Path | str = "data/order_audit") -> None:
        self._base_dir = Path(base_dir)
        self._lock = threading.Lock()
        os.makedirs(self._base_dir, exist_ok=True)
        self._ensure_index()

    def append(self, record: OrderAuditRecord) -> None:
        path = self._record_path(record.record_id)
        tmp = self._base_dir / f"{record.record_id}_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(asdict(record), default=str), encoding="utf-8")
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

        with self._lock:
            index = self._read_index()
            index["records"].append(_index_entry(record))
            self._write_index(index)

    def list(
        self,
        *,
        scope: str | None = None,
        owner_id: str | None = None,
        symbol: str | None = None,
        event: str | None = None,
        limit: int = 100,
    ) -> list[OrderAuditRecord]:
        with self._lock:
            entries = list(self._read_index().get("records", []))
        entries = _filter_entries(
            entries,
            scope=scope,
            owner_id=owner_id,
            symbol=symbol,
            event=event,
        )
        entries = sorted(entries, key=lambda item: item.get("timestamp", ""), reverse=True)
        selected = entries[: max(1, min(limit, 500))]
        records: list[OrderAuditRecord] = []
        for entry in selected:
            record = self._read_record(entry["record_id"])
            if record is not None:
                records.append(record)
        return records

    def _record_path(self, record_id: str) -> Path:
        return self._base_dir / f"{record_id}.json"

    def _index_path(self) -> Path:
        return self._base_dir / "_index.json"

    def _ensure_index(self) -> None:
        if not self._index_path().exists():
            self._write_index({"records": []})

    def _read_index(self) -> dict[str, Any]:
        try:
            return json.loads(self._index_path().read_text(encoding="utf-8"))
        except Exception:
            return {"records": []}

    def _write_index(self, payload: dict[str, Any]) -> None:
        tmp = self._base_dir / f"_index_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
            os.replace(tmp, self._index_path())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _read_record(self, record_id: str) -> OrderAuditRecord | None:
        path = self._record_path(record_id)
        if not path.exists():
            return None
        return _deserialize_record(json.loads(path.read_text(encoding="utf-8")))


class SupabaseOrderAuditRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._conn: Any = None
        self._schema_checked = False

    def append(self, record: OrderAuditRecord) -> None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO order_audit_records
                    (
                        record_id, scope, owner_id, event, symbol, side,
                        requested_quantity, filled_quantity, price, status, reason,
                        timestamp, payload, broker_order_id
                    )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s::jsonb, %s
                )
                """,
                (
                    record.record_id,
                    record.scope,
                    record.owner_id,
                    record.event,
                    record.symbol,
                    record.side,
                    record.requested_quantity,
                    record.filled_quantity,
                    record.price,
                    record.status,
                    record.reason,
                    record.timestamp,
                    json.dumps(record.payload, default=str),
                    record.broker_order_id,
                ),
            )

    def list(
        self,
        *,
        scope: str | None = None,
        owner_id: str | None = None,
        symbol: str | None = None,
        event: str | None = None,
        limit: int = 100,
    ) -> list[OrderAuditRecord]:
        conditions: list[str] = []
        params: list[object] = []
        if scope is not None:
            conditions.append("scope = %s")
            params.append(scope)
        if owner_id is not None:
            conditions.append("owner_id = %s")
            params.append(owner_id)
        if symbol is not None:
            conditions.append("symbol = %s")
            params.append(symbol)
        if event is not None:
            conditions.append("event = %s")
            params.append(event)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        with self._get_conn().cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    record_id, scope, owner_id, event, symbol, side,
                    requested_quantity, filled_quantity, price, status, reason,
                    timestamp, payload, broker_order_id
                FROM order_audit_records
                {where}
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                [*params, max(1, min(limit, 500))],
            )
            rows = cur.fetchall()
        return [_deserialize_db_row(row) for row in rows]

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            if psycopg is None:
                raise ModuleNotFoundError("psycopg is required for SupabaseOrderAuditRepository.")
            self._conn = psycopg.connect(self._database_url, autocommit=True)
            self._schema_checked = False
        self._ensure_schema()
        return self._conn

    def _ensure_schema(self) -> None:
        if self._schema_checked:
            return
        with self._conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS order_audit_records (
                    record_id          TEXT PRIMARY KEY,
                    scope              TEXT NOT NULL,
                    owner_id           TEXT NOT NULL,
                    event              TEXT NOT NULL,
                    symbol             TEXT,
                    side               TEXT,
                    requested_quantity TEXT,
                    filled_quantity    TEXT,
                    price              TEXT,
                    status             TEXT,
                    reason             TEXT,
                    timestamp          TIMESTAMPTZ NOT NULL,
                    payload            JSONB NOT NULL DEFAULT '{}'::jsonb,
                    broker_order_id    TEXT,
                    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_order_audit_scope_owner_timestamp
                ON order_audit_records (scope, owner_id, timestamp DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_order_audit_symbol_timestamp
                ON order_audit_records (symbol, timestamp DESC)
                """
            )
        self._schema_checked = True


def create_order_audit_repository() -> OrderAuditRepository:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return SupabaseOrderAuditRepository(database_url)
    base_dir = Path(os.getenv("TRADING_SYSTEM_ORDER_AUDIT_DIR", "data/order_audit"))
    return FileOrderAuditRepository(base_dir)


def append_step_order_audit_events(
    *,
    repository: OrderAuditRepository | None,
    scope: str | None,
    owner_id: str | None,
    events: Any,
) -> None:
    if repository is None or scope is None or owner_id is None:
        return
    for event_name, payload in _iter_step_events(events):
        try:
            repository.append(
                _record_from_event(
                    scope=scope,
                    owner_id=owner_id,
                    event=event_name,
                    payload=payload,
                )
            )
        except Exception as exc:
            _log.warning("Failed to append order audit record: %s", exc)
            continue


def _iter_step_events(events: Any):
    for name, event_name in (
        ("order_created", "order.created"),
        ("order_filled", "order.filled"),
        ("order_rejected", "order.rejected"),
        ("risk_rejected", "risk.rejected"),
    ):
        payload = getattr(events, name, None)
        if payload:
            yield event_name, payload


def _record_from_event(
    *,
    scope: str,
    owner_id: str,
    event: str,
    payload: dict[str, Any],
) -> OrderAuditRecord:
    timestamp = str(
        payload.get("timestamp") or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    return OrderAuditRecord(
        record_id=f"oa_{uuid.uuid4().hex}",
        scope=scope,
        owner_id=owner_id,
        event=event,
        symbol=_optional_str(payload.get("symbol")),
        side=_optional_str(payload.get("side")),
        requested_quantity=_first_str(payload, "requested_quantity", "quantity"),
        filled_quantity=_optional_str(payload.get("filled_quantity")),
        price=_first_str(payload, "fill_price", "price"),
        status=_optional_str(payload.get("status")),
        reason=_optional_str(payload.get("reason")),
        timestamp=timestamp,
        payload=dict(payload),
        broker_order_id=_optional_str(payload.get("broker_order_id")),
    )


def _first_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return str(value)
    return None


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _index_entry(record: OrderAuditRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "scope": record.scope,
        "owner_id": record.owner_id,
        "event": record.event,
        "symbol": record.symbol,
        "timestamp": record.timestamp,
    }


def _filter_entries(
    entries: list[dict[str, Any]],
    *,
    scope: str | None,
    owner_id: str | None,
    symbol: str | None,
    event: str | None,
) -> list[dict[str, Any]]:
    filtered = entries
    if scope is not None:
        filtered = [item for item in filtered if item.get("scope") == scope]
    if owner_id is not None:
        filtered = [item for item in filtered if item.get("owner_id") == owner_id]
    if symbol is not None:
        filtered = [item for item in filtered if item.get("symbol") == symbol]
    if event is not None:
        filtered = [item for item in filtered if item.get("event") == event]
    return filtered


def _deserialize_record(data: dict[str, Any]) -> OrderAuditRecord:
    return OrderAuditRecord(
        record_id=data["record_id"],
        scope=data["scope"],
        owner_id=data["owner_id"],
        event=data["event"],
        symbol=data.get("symbol"),
        side=data.get("side"),
        requested_quantity=data.get("requested_quantity"),
        filled_quantity=data.get("filled_quantity"),
        price=data.get("price"),
        status=data.get("status"),
        reason=data.get("reason"),
        timestamp=data["timestamp"],
        payload=dict(data.get("payload", {})),
        broker_order_id=data.get("broker_order_id"),
    )


def _deserialize_db_row(row: tuple[Any, ...]) -> OrderAuditRecord:
    (
        record_id,
        scope,
        owner_id,
        event,
        symbol,
        side,
        requested_quantity,
        filled_quantity,
        price,
        status,
        reason,
        timestamp,
        payload,
        broker_order_id,
    ) = row
    parsed_payload = payload if isinstance(payload, dict) else json.loads(payload or "{}")
    return OrderAuditRecord(
        record_id=record_id,
        scope=scope,
        owner_id=owner_id,
        event=event,
        symbol=symbol,
        side=side,
        requested_quantity=requested_quantity,
        filled_quantity=filled_quantity,
        price=price,
        status=status,
        reason=reason,
        timestamp=_serialize_timestamp(timestamp),
        payload=parsed_payload,
        broker_order_id=broker_order_id,
    )


def _serialize_timestamp(value: Any) -> str:
    return value.isoformat().replace("+00:00", "Z") if hasattr(value, "isoformat") else str(value)
