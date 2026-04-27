from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from trading_system.core.compat import UTC
from trading_system.core.ops import EventRecord

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional dependency in unit tests
    psycopg = None  # type: ignore[assignment]

_ARCHIVED_PREFIXES = (
    "risk.",
    "portfolio.reconciliation.",
    "system.control",
    "system.error",
    "system.shutdown",
)
_ARCHIVED_SEVERITIES = {"WARNING", "ERROR", "CRITICAL"}


@dataclass(slots=True, frozen=True)
class LiveRuntimeEventRecord:
    record_id: str
    session_id: str
    event: str
    severity: str
    correlation_id: str
    timestamp: str
    payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class LiveRuntimeEventFilter:
    session_id: str | None = None
    start: str | None = None
    end: str | None = None
    severity: str | None = None
    event: str | None = None
    sort: str = "desc"
    limit: int = 100


class LiveRuntimeEventRepository(Protocol):
    def append(self, record: LiveRuntimeEventRecord) -> None:
        ...

    def list(self, query: LiveRuntimeEventFilter) -> list[LiveRuntimeEventRecord]:
        ...


class FileLiveRuntimeEventRepository:
    def __init__(self, base_dir: Path | str = "data/live_events") -> None:
        self._base_dir = Path(base_dir)
        self._lock = threading.Lock()
        os.makedirs(self._base_dir, exist_ok=True)
        self._ensure_index()

    def append(self, record: LiveRuntimeEventRecord) -> None:
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
            index["events"].append(_index_entry(record))
            self._write_index(index)

    def list(self, query: LiveRuntimeEventFilter) -> list[LiveRuntimeEventRecord]:
        resolved = _normalize_query(query)
        with self._lock:
            entries = list(self._read_index().get("events", []))
        entries = _filter_entries(entries, resolved)
        entries = sorted(
            entries,
            key=lambda item: item.get("timestamp", ""),
            reverse=_normalize_sort(resolved.sort) == "desc",
        )
        selected = entries[: max(1, min(resolved.limit, 5000))]
        records: list[LiveRuntimeEventRecord] = []
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
            self._write_index({"events": []})

    def _read_index(self) -> dict[str, Any]:
        try:
            return json.loads(self._index_path().read_text(encoding="utf-8"))
        except Exception:
            return {"events": []}

    def _write_index(self, payload: dict[str, Any]) -> None:
        tmp = self._base_dir / f"_index_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
            os.replace(tmp, self._index_path())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _read_record(self, record_id: str) -> LiveRuntimeEventRecord | None:
        path = self._record_path(record_id)
        if not path.exists():
            return None
        return _deserialize_record(json.loads(path.read_text(encoding="utf-8")))


class SupabaseLiveRuntimeEventRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._conn: Any = None
        self._schema_checked = False

    def append(self, record: LiveRuntimeEventRecord) -> None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO live_runtime_events
                    (
                        record_id, session_id, event, severity,
                        correlation_id, timestamp, payload
                    )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    record.record_id,
                    record.session_id,
                    record.event,
                    record.severity,
                    record.correlation_id,
                    record.timestamp,
                    json.dumps(record.payload, default=str),
                ),
            )

    def list(self, query: LiveRuntimeEventFilter) -> list[LiveRuntimeEventRecord]:
        resolved = _normalize_query(query)
        conditions: list[str] = []
        params: list[object] = []
        if resolved.session_id is not None:
            conditions.append("session_id = %s")
            params.append(resolved.session_id)
        if resolved.start is not None:
            conditions.append("timestamp >= %s")
            params.append(resolved.start)
        if resolved.end is not None:
            conditions.append("timestamp <= %s")
            params.append(resolved.end)
        if resolved.severity is not None:
            conditions.append("severity = %s")
            params.append(resolved.severity)
        if resolved.event is not None:
            conditions.append("event = %s")
            params.append(resolved.event)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        direction = "ASC" if _normalize_sort(resolved.sort) == "asc" else "DESC"
        with self._get_conn().cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    record_id, session_id, event, severity,
                    correlation_id, timestamp, payload
                FROM live_runtime_events
                {where}
                ORDER BY timestamp {direction}
                LIMIT %s
                """,
                [*params, max(1, min(resolved.limit, 5000))],
            )
            rows = cur.fetchall()
        return [_deserialize_db_row(row) for row in rows]

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            if psycopg is None:
                raise ModuleNotFoundError(
                    "psycopg is required for SupabaseLiveRuntimeEventRepository."
                )
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
                CREATE TABLE IF NOT EXISTS live_runtime_events (
                    record_id      TEXT PRIMARY KEY,
                    session_id     TEXT NOT NULL,
                    event          TEXT NOT NULL,
                    severity       TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    timestamp      TIMESTAMPTZ NOT NULL,
                    payload        JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_live_runtime_events_session_timestamp
                ON live_runtime_events (session_id, timestamp DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_live_runtime_events_severity_timestamp
                ON live_runtime_events (severity, timestamp DESC)
                """
            )
        self._schema_checked = True


def create_live_runtime_event_repository() -> LiveRuntimeEventRepository:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return SupabaseLiveRuntimeEventRepository(database_url)
    base_dir = Path(os.getenv("TRADING_SYSTEM_LIVE_EVENTS_DIR", "data/live_events"))
    return FileLiveRuntimeEventRepository(base_dir)


def should_archive_runtime_event(record: EventRecord) -> bool:
    severity = record.severity.upper()
    return severity in _ARCHIVED_SEVERITIES or record.event.startswith(_ARCHIVED_PREFIXES)


def runtime_event_from_log(
    *,
    session_id: str,
    record: EventRecord,
) -> LiveRuntimeEventRecord:
    return LiveRuntimeEventRecord(
        record_id=uuid.uuid4().hex,
        session_id=session_id,
        event=record.event,
        severity=record.severity.upper(),
        correlation_id=record.correlation_id,
        timestamp=record.timestamp,
        payload=record.payload,
    )


def _index_entry(record: LiveRuntimeEventRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "session_id": record.session_id,
        "event": record.event,
        "severity": record.severity,
        "correlation_id": record.correlation_id,
        "timestamp": record.timestamp,
    }


def _deserialize_record(data: dict[str, Any]) -> LiveRuntimeEventRecord:
    return LiveRuntimeEventRecord(
        record_id=data["record_id"],
        session_id=data["session_id"],
        event=data["event"],
        severity=data["severity"],
        correlation_id=data["correlation_id"],
        timestamp=data["timestamp"],
        payload=dict(data.get("payload") or {}),
    )


def _deserialize_db_row(row: tuple[Any, ...]) -> LiveRuntimeEventRecord:
    record_id, session_id, event, severity, correlation_id, timestamp, payload = row
    parsed_payload = payload if isinstance(payload, dict) else json.loads(payload or "{}")
    return LiveRuntimeEventRecord(
        record_id=record_id,
        session_id=session_id,
        event=event,
        severity=severity,
        correlation_id=correlation_id,
        timestamp=_serialize_timestamp(timestamp),
        payload=parsed_payload,
    )


def _normalize_query(query: LiveRuntimeEventFilter) -> LiveRuntimeEventFilter:
    return LiveRuntimeEventFilter(
        session_id=_blank_to_none(query.session_id),
        start=query.start,
        end=query.end,
        severity=_blank_to_none(query.severity.upper() if query.severity else None),
        event=_blank_to_none(query.event),
        sort=_normalize_sort(query.sort),
        limit=max(1, min(query.limit, 5000)),
    )


def _filter_entries(
    entries: list[dict[str, Any]],
    query: LiveRuntimeEventFilter,
) -> list[dict[str, Any]]:
    start_dt = _parse_optional_datetime(query.start)
    end_dt = _parse_optional_datetime(query.end)
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        timestamp = _parse_optional_datetime(entry.get("timestamp"))
        if query.session_id is not None and entry.get("session_id") != query.session_id:
            continue
        if start_dt is not None and (timestamp is None or timestamp < start_dt):
            continue
        if end_dt is not None and (timestamp is None or timestamp > end_dt):
            continue
        if query.severity is not None and entry.get("severity") != query.severity:
            continue
        if query.event is not None and entry.get("event") != query.event:
            continue
        filtered.append(entry)
    return filtered


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_sort(sort: str) -> str:
    return "asc" if sort == "asc" else "desc"


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _serialize_timestamp(value: object) -> str:
    return value.isoformat().replace("+00:00", "Z") if hasattr(value, "isoformat") else str(value)
