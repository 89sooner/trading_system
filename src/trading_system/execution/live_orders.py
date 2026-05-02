from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from trading_system.core.compat import UTC, StrEnum

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit tests
    psycopg = None  # type: ignore[assignment]

_log = logging.getLogger(__name__)


class LiveOrderStatus(StrEnum):
    SUBMITTED = "submitted"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    STALE = "stale"
    UNKNOWN = "unknown"


TERMINAL_LIVE_ORDER_STATUSES = {
    LiveOrderStatus.FILLED,
    LiveOrderStatus.REJECTED,
    LiveOrderStatus.CANCELLED,
}

ACTIVE_LIVE_ORDER_STATUSES = {
    LiveOrderStatus.SUBMITTED,
    LiveOrderStatus.OPEN,
    LiveOrderStatus.PARTIALLY_FILLED,
    LiveOrderStatus.CANCEL_REQUESTED,
    LiveOrderStatus.STALE,
    LiveOrderStatus.UNKNOWN,
}


@dataclass(slots=True, frozen=True)
class LiveOrderRecord:
    record_id: str
    session_id: str
    symbol: str
    side: str
    requested_quantity: str
    filled_quantity: str
    remaining_quantity: str
    status: str
    broker_order_id: str | None
    submitted_at: str
    last_synced_at: str | None = None
    stale_after: str | None = None
    cancel_requested: bool = False
    cancel_requested_at: str | None = None
    cancelled_at: str | None = None
    last_error: str | None = None
    payload: dict[str, Any] | None = None

    @property
    def live_status(self) -> LiveOrderStatus:
        try:
            return LiveOrderStatus(self.status)
        except ValueError:
            return LiveOrderStatus.UNKNOWN

    @property
    def is_terminal(self) -> bool:
        return self.live_status in TERMINAL_LIVE_ORDER_STATUSES

    @property
    def is_active(self) -> bool:
        return self.live_status in ACTIVE_LIVE_ORDER_STATUSES


@dataclass(slots=True, frozen=True)
class LiveOrderFilter:
    session_id: str | None = None
    symbol: str | None = None
    status: str | None = None
    broker_order_id: str | None = None
    active_only: bool = False
    sort: str = "desc"
    limit: int = 100


class LiveOrderRepository(Protocol):
    def upsert(self, record: LiveOrderRecord) -> None:
        ...

    def get(self, record_id: str) -> LiveOrderRecord | None:
        ...

    def list(self, query: LiveOrderFilter | None = None) -> list[LiveOrderRecord]:
        ...

    def list_active(self, *, session_id: str | None = None) -> list[LiveOrderRecord]:
        ...

    def list_stale(self, *, now: str, session_id: str | None = None) -> list[LiveOrderRecord]:
        ...

    def mark_cancel_requested(
        self,
        record_id: str,
        *,
        requested_at: str,
        last_error: str | None = None,
    ) -> LiveOrderRecord | None:
        ...

    def update_from_broker(
        self,
        record_id: str,
        *,
        status: str,
        filled_quantity: str,
        remaining_quantity: str,
        synced_at: str,
        broker_order_id: str | None = None,
        last_error: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> LiveOrderRecord | None:
        ...


class FileLiveOrderRepository:
    def __init__(self, base_dir: Path | str = "data/live_orders") -> None:
        self._base_dir = Path(base_dir)
        self._lock = threading.Lock()
        os.makedirs(self._base_dir, exist_ok=True)
        self._ensure_index()

    def upsert(self, record: LiveOrderRecord) -> None:
        self._write_record(record)
        with self._lock:
            index = self._read_index()
            records = [
                item
                for item in index.get("records", [])
                if item.get("record_id") != record.record_id
            ]
            records.append(_index_entry(record))
            index["records"] = records
            self._write_index(index)

    def get(self, record_id: str) -> LiveOrderRecord | None:
        return self._read_record(record_id)

    def list(self, query: LiveOrderFilter | None = None) -> list[LiveOrderRecord]:
        resolved = query or LiveOrderFilter()
        with self._lock:
            entries = list(self._read_index().get("records", []))
        entries = _filter_entries(entries, resolved)
        entries = sorted(
            entries,
            key=lambda item: item.get("submitted_at", ""),
            reverse=_normalize_sort(resolved.sort) == "desc",
        )
        selected = entries[: max(1, min(resolved.limit, 5000))]
        records: list[LiveOrderRecord] = []
        for entry in selected:
            record = self._read_record(entry["record_id"])
            if record is not None:
                records.append(record)
        return records

    def list_active(self, *, session_id: str | None = None) -> list[LiveOrderRecord]:
        return self.list(LiveOrderFilter(session_id=session_id, active_only=True, limit=5000))

    def list_stale(self, *, now: str, session_id: str | None = None) -> list[LiveOrderRecord]:
        return [
            record
            for record in self.list_active(session_id=session_id)
            if _is_stale(record, now)
        ]

    def mark_cancel_requested(
        self,
        record_id: str,
        *,
        requested_at: str,
        last_error: str | None = None,
    ) -> LiveOrderRecord | None:
        record = self.get(record_id)
        if record is None:
            return None
        updated = replace(
            record,
            status=LiveOrderStatus.CANCEL_REQUESTED.value,
            cancel_requested=True,
            cancel_requested_at=requested_at,
            last_error=last_error,
        )
        self.upsert(updated)
        return updated

    def update_from_broker(
        self,
        record_id: str,
        *,
        status: str,
        filled_quantity: str,
        remaining_quantity: str,
        synced_at: str,
        broker_order_id: str | None = None,
        last_error: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> LiveOrderRecord | None:
        record = self.get(record_id)
        if record is None:
            return None
        resolved_status = _normalize_status(status)
        updated = replace(
            record,
            status=resolved_status.value,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            broker_order_id=broker_order_id or record.broker_order_id,
            last_synced_at=synced_at,
            cancelled_at=(
                synced_at
                if resolved_status == LiveOrderStatus.CANCELLED
                else record.cancelled_at
            ),
            last_error=last_error,
            payload=payload if payload is not None else record.payload,
        )
        self.upsert(updated)
        return updated

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

    def _write_record(self, record: LiveOrderRecord) -> None:
        tmp = self._base_dir / f"{record.record_id}_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(asdict(record), default=str), encoding="utf-8")
            os.replace(tmp, self._record_path(record.record_id))
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _read_record(self, record_id: str) -> LiveOrderRecord | None:
        path = self._record_path(record_id)
        if not path.exists():
            return None
        return _deserialize_record(json.loads(path.read_text(encoding="utf-8")))


class SupabaseLiveOrderRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._conn: Any = None
        self._schema_checked = False

    def upsert(self, record: LiveOrderRecord) -> None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO live_order_lifecycle
                    (
                        record_id, session_id, symbol, side,
                        requested_quantity, filled_quantity, remaining_quantity,
                        status, broker_order_id, submitted_at, last_synced_at,
                        stale_after, cancel_requested, cancel_requested_at,
                        cancelled_at, last_error, payload
                    )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s::jsonb
                )
                ON CONFLICT (record_id) DO UPDATE SET
                    session_id          = EXCLUDED.session_id,
                    symbol              = EXCLUDED.symbol,
                    side                = EXCLUDED.side,
                    requested_quantity  = EXCLUDED.requested_quantity,
                    filled_quantity     = EXCLUDED.filled_quantity,
                    remaining_quantity  = EXCLUDED.remaining_quantity,
                    status              = EXCLUDED.status,
                    broker_order_id     = EXCLUDED.broker_order_id,
                    submitted_at        = EXCLUDED.submitted_at,
                    last_synced_at      = EXCLUDED.last_synced_at,
                    stale_after         = EXCLUDED.stale_after,
                    cancel_requested    = EXCLUDED.cancel_requested,
                    cancel_requested_at = EXCLUDED.cancel_requested_at,
                    cancelled_at        = EXCLUDED.cancelled_at,
                    last_error          = EXCLUDED.last_error,
                    payload             = EXCLUDED.payload
                """,
                _db_values(record),
            )

    def get(self, record_id: str) -> LiveOrderRecord | None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                SELECT
                    record_id, session_id, symbol, side,
                    requested_quantity, filled_quantity, remaining_quantity,
                    status, broker_order_id, submitted_at, last_synced_at,
                    stale_after, cancel_requested, cancel_requested_at,
                    cancelled_at, last_error, payload
                FROM live_order_lifecycle
                WHERE record_id = %s
                """,
                (record_id,),
            )
            row = cur.fetchone()
        return _deserialize_db_row(row) if row is not None else None

    def list(self, query: LiveOrderFilter | None = None) -> list[LiveOrderRecord]:
        resolved = query or LiveOrderFilter()
        conditions: list[str] = []
        params: list[object] = []
        if resolved.session_id is not None:
            conditions.append("session_id = %s")
            params.append(resolved.session_id)
        if resolved.symbol is not None:
            conditions.append("symbol = %s")
            params.append(resolved.symbol)
        if resolved.status is not None:
            conditions.append("status = %s")
            params.append(resolved.status)
        if resolved.broker_order_id is not None:
            conditions.append("broker_order_id = %s")
            params.append(resolved.broker_order_id)
        if resolved.active_only:
            conditions.append("status = ANY(%s)")
            params.append([status.value for status in ACTIVE_LIVE_ORDER_STATUSES])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        direction = "ASC" if _normalize_sort(resolved.sort) == "asc" else "DESC"
        with self._get_conn().cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    record_id, session_id, symbol, side,
                    requested_quantity, filled_quantity, remaining_quantity,
                    status, broker_order_id, submitted_at, last_synced_at,
                    stale_after, cancel_requested, cancel_requested_at,
                    cancelled_at, last_error, payload
                FROM live_order_lifecycle
                {where}
                ORDER BY submitted_at {direction}
                LIMIT %s
                """,
                [*params, max(1, min(resolved.limit, 5000))],
            )
            rows = cur.fetchall()
        return [_deserialize_db_row(row) for row in rows]

    def list_active(self, *, session_id: str | None = None) -> list[LiveOrderRecord]:
        return self.list(LiveOrderFilter(session_id=session_id, active_only=True, limit=5000))

    def list_stale(self, *, now: str, session_id: str | None = None) -> list[LiveOrderRecord]:
        conditions = [
            "status = ANY(%s)",
            "stale_after IS NOT NULL",
            "stale_after <= %s",
        ]
        params: list[object] = [
            [status.value for status in ACTIVE_LIVE_ORDER_STATUSES],
            now,
        ]
        if session_id is not None:
            conditions.append("session_id = %s")
            params.append(session_id)
        with self._get_conn().cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    record_id, session_id, symbol, side,
                    requested_quantity, filled_quantity, remaining_quantity,
                    status, broker_order_id, submitted_at, last_synced_at,
                    stale_after, cancel_requested, cancel_requested_at,
                    cancelled_at, last_error, payload
                FROM live_order_lifecycle
                WHERE {" AND ".join(conditions)}
                ORDER BY submitted_at DESC
                """,
                params,
            )
            rows = cur.fetchall()
        return [_deserialize_db_row(row) for row in rows]

    def mark_cancel_requested(
        self,
        record_id: str,
        *,
        requested_at: str,
        last_error: str | None = None,
    ) -> LiveOrderRecord | None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                UPDATE live_order_lifecycle
                SET status = %s,
                    cancel_requested = TRUE,
                    cancel_requested_at = %s,
                    last_error = %s
                WHERE record_id = %s
                RETURNING
                    record_id, session_id, symbol, side,
                    requested_quantity, filled_quantity, remaining_quantity,
                    status, broker_order_id, submitted_at, last_synced_at,
                    stale_after, cancel_requested, cancel_requested_at,
                    cancelled_at, last_error, payload
                """,
                (
                    LiveOrderStatus.CANCEL_REQUESTED.value,
                    requested_at,
                    last_error,
                    record_id,
                ),
            )
            row = cur.fetchone()
        return _deserialize_db_row(row) if row is not None else None

    def update_from_broker(
        self,
        record_id: str,
        *,
        status: str,
        filled_quantity: str,
        remaining_quantity: str,
        synced_at: str,
        broker_order_id: str | None = None,
        last_error: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> LiveOrderRecord | None:
        current = self.get(record_id)
        if current is None:
            return None
        resolved = _normalize_status(status)
        updated = replace(
            current,
            status=resolved.value,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            broker_order_id=broker_order_id or current.broker_order_id,
            last_synced_at=synced_at,
            cancelled_at=(
                synced_at
                if resolved == LiveOrderStatus.CANCELLED
                else current.cancelled_at
            ),
            last_error=last_error,
            payload=payload if payload is not None else current.payload,
        )
        self.upsert(updated)
        return updated

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            if psycopg is None:
                raise ModuleNotFoundError("psycopg is required for SupabaseLiveOrderRepository.")
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
                CREATE TABLE IF NOT EXISTS live_order_lifecycle (
                    record_id           TEXT PRIMARY KEY,
                    session_id          TEXT NOT NULL,
                    symbol              TEXT NOT NULL,
                    side                TEXT NOT NULL,
                    requested_quantity  TEXT NOT NULL,
                    filled_quantity     TEXT NOT NULL,
                    remaining_quantity  TEXT NOT NULL,
                    status              TEXT NOT NULL,
                    broker_order_id     TEXT,
                    submitted_at        TIMESTAMPTZ NOT NULL,
                    last_synced_at      TIMESTAMPTZ,
                    stale_after         TIMESTAMPTZ,
                    cancel_requested    BOOLEAN NOT NULL DEFAULT FALSE,
                    cancel_requested_at TIMESTAMPTZ,
                    cancelled_at        TIMESTAMPTZ,
                    last_error          TEXT,
                    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_live_order_lifecycle_session_status
                ON live_order_lifecycle (session_id, status, submitted_at DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_live_order_lifecycle_broker_order
                ON live_order_lifecycle (broker_order_id)
                WHERE broker_order_id IS NOT NULL
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_live_order_lifecycle_stale
                ON live_order_lifecycle (status, stale_after)
                WHERE stale_after IS NOT NULL
                """
            )
        self._schema_checked = True


def create_live_order_repository() -> LiveOrderRepository:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return SupabaseLiveOrderRepository(database_url)
    base_dir = Path(os.getenv("TRADING_SYSTEM_LIVE_ORDER_DIR", "data/live_orders"))
    return FileLiveOrderRepository(base_dir)


def new_live_order_record(
    *,
    session_id: str,
    symbol: str,
    side: str,
    requested_quantity: str,
    filled_quantity: str,
    remaining_quantity: str,
    status: str,
    broker_order_id: str | None,
    submitted_at: str | None = None,
    stale_after: str | None = None,
    payload: dict[str, Any] | None = None,
) -> LiveOrderRecord:
    submitted = submitted_at or datetime.now(UTC).isoformat()
    return LiveOrderRecord(
        record_id=f"live_order_{uuid.uuid4().hex}",
        session_id=session_id,
        symbol=symbol,
        side=side,
        requested_quantity=requested_quantity,
        filled_quantity=filled_quantity,
        remaining_quantity=remaining_quantity,
        status=_normalize_status(status).value,
        broker_order_id=broker_order_id,
        submitted_at=submitted,
        last_synced_at=submitted,
        stale_after=stale_after,
        payload=payload or {},
    )


def _normalize_status(status: str) -> LiveOrderStatus:
    try:
        return LiveOrderStatus(status)
    except ValueError:
        return LiveOrderStatus.UNKNOWN


def _filter_entries(entries: list[dict[str, Any]], query: LiveOrderFilter) -> list[dict[str, Any]]:
    result = entries
    if query.session_id is not None:
        result = [item for item in result if item.get("session_id") == query.session_id]
    if query.symbol is not None:
        result = [item for item in result if item.get("symbol") == query.symbol]
    if query.status is not None:
        result = [item for item in result if item.get("status") == query.status]
    if query.broker_order_id is not None:
        result = [item for item in result if item.get("broker_order_id") == query.broker_order_id]
    if query.active_only:
        active = {status.value for status in ACTIVE_LIVE_ORDER_STATUSES}
        result = [item for item in result if item.get("status") in active]
    return result


def _index_entry(record: LiveOrderRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "session_id": record.session_id,
        "symbol": record.symbol,
        "side": record.side,
        "status": record.status,
        "broker_order_id": record.broker_order_id,
        "submitted_at": record.submitted_at,
        "stale_after": record.stale_after,
    }


def _deserialize_record(payload: dict[str, Any]) -> LiveOrderRecord:
    return LiveOrderRecord(
        record_id=str(payload["record_id"]),
        session_id=str(payload["session_id"]),
        symbol=str(payload["symbol"]),
        side=str(payload["side"]),
        requested_quantity=str(payload["requested_quantity"]),
        filled_quantity=str(payload["filled_quantity"]),
        remaining_quantity=str(payload["remaining_quantity"]),
        status=str(payload["status"]),
        broker_order_id=payload.get("broker_order_id"),
        submitted_at=str(payload["submitted_at"]),
        last_synced_at=payload.get("last_synced_at"),
        stale_after=payload.get("stale_after"),
        cancel_requested=bool(payload.get("cancel_requested", False)),
        cancel_requested_at=payload.get("cancel_requested_at"),
        cancelled_at=payload.get("cancelled_at"),
        last_error=payload.get("last_error"),
        payload=payload.get("payload") or {},
    )


def _deserialize_db_row(row: Any) -> LiveOrderRecord:
    return LiveOrderRecord(
        record_id=str(row[0]),
        session_id=str(row[1]),
        symbol=str(row[2]),
        side=str(row[3]),
        requested_quantity=str(row[4]),
        filled_quantity=str(row[5]),
        remaining_quantity=str(row[6]),
        status=str(row[7]),
        broker_order_id=row[8],
        submitted_at=_iso(row[9]),
        last_synced_at=_iso(row[10]) if row[10] is not None else None,
        stale_after=_iso(row[11]) if row[11] is not None else None,
        cancel_requested=bool(row[12]),
        cancel_requested_at=_iso(row[13]) if row[13] is not None else None,
        cancelled_at=_iso(row[14]) if row[14] is not None else None,
        last_error=row[15],
        payload=row[16] or {},
    )


def _db_values(record: LiveOrderRecord) -> tuple[object, ...]:
    return (
        record.record_id,
        record.session_id,
        record.symbol,
        record.side,
        record.requested_quantity,
        record.filled_quantity,
        record.remaining_quantity,
        record.status,
        record.broker_order_id,
        record.submitted_at,
        record.last_synced_at,
        record.stale_after,
        record.cancel_requested,
        record.cancel_requested_at,
        record.cancelled_at,
        record.last_error,
        json.dumps(record.payload or {}, default=str),
    )


def _is_stale(record: LiveOrderRecord, now: str) -> bool:
    if record.stale_after is None or not record.is_active:
        return False
    return _parse_dt(record.stale_after) <= _parse_dt(now)


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalize_sort(sort: str) -> str:
    return "asc" if sort == "asc" else "desc"
