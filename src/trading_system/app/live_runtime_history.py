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


@dataclass(slots=True, frozen=True)
class LiveRuntimeSessionRecord:
    session_id: str
    started_at: str
    ended_at: str | None
    provider: str
    broker: str
    live_execution: str
    symbols: list[str]
    last_state: str
    last_error: str | None = None
    preflight_summary: dict[str, Any] | None = None


@dataclass(slots=True, frozen=True)
class LiveRuntimeSessionFilter:
    start: str | None = None
    end: str | None = None
    provider: str | None = None
    broker: str | None = None
    live_execution: str | None = None
    state: str | None = None
    symbol: str | None = None
    has_error: bool | None = None
    sort: str = "desc"
    page: int = 1
    page_size: int = 20


@dataclass(slots=True, frozen=True)
class LiveRuntimeSessionListResult:
    records: list[LiveRuntimeSessionRecord]
    total: int
    page: int
    page_size: int


class LiveRuntimeSessionRepository(Protocol):
    def save(self, record: LiveRuntimeSessionRecord) -> None:
        ...

    def get(self, session_id: str) -> LiveRuntimeSessionRecord | None:
        ...

    def list(self, limit: int = 20) -> list[LiveRuntimeSessionRecord]:
        ...

    def search(
        self,
        query: LiveRuntimeSessionFilter | None = None,
    ) -> LiveRuntimeSessionListResult:
        ...


class FileLiveRuntimeSessionRepository:
    def __init__(self, base_dir: Path | str = "data/live_sessions") -> None:
        self._base_dir = Path(base_dir)
        self._lock = threading.Lock()
        os.makedirs(self._base_dir, exist_ok=True)
        self._ensure_index()

    def save(self, record: LiveRuntimeSessionRecord) -> None:
        path = self._record_path(record.session_id)
        tmp = self._base_dir / f"{record.session_id}_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(asdict(record), default=str), encoding="utf-8")
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

        with self._lock:
            index = self._read_index()
            entries = [
                entry
                for entry in index["sessions"]
                if entry["session_id"] != record.session_id
            ]
            entries.append(self._index_entry(record))
            index["sessions"] = entries
            self._write_index(index)

    def get(self, session_id: str) -> LiveRuntimeSessionRecord | None:
        path = self._record_path(session_id)
        if not path.exists():
            return None
        return _deserialize_session(json.loads(path.read_text(encoding="utf-8")))

    def list(self, limit: int = 20) -> list[LiveRuntimeSessionRecord]:
        return self.search(
            LiveRuntimeSessionFilter(page=1, page_size=max(limit, 1))
        ).records

    def search(
        self,
        query: LiveRuntimeSessionFilter | None = None,
    ) -> LiveRuntimeSessionListResult:
        resolved = _normalize_query(query)
        with self._lock:
            index = self._read_index()
        sessions = _filter_session_entries(index.get("sessions", []), resolved)
        sessions = sorted(
            sessions,
            key=lambda item: item.get("started_at", ""),
            reverse=_normalize_sort(resolved.sort) == "desc",
        )
        total = len(sessions)
        start = (resolved.page - 1) * resolved.page_size
        selected = sessions[start : start + resolved.page_size]
        return LiveRuntimeSessionListResult(
            records=[_deserialize_session(item) for item in selected],
            total=total,
            page=resolved.page,
            page_size=resolved.page_size,
        )

    def _index_path(self) -> Path:
        return self._base_dir / "_index.json"

    def _record_path(self, session_id: str) -> Path:
        return self._base_dir / f"{session_id}.json"

    def _ensure_index(self) -> None:
        if not self._index_path().exists():
            self._write_index({"sessions": []})

    def _read_index(self) -> dict[str, Any]:
        try:
            return json.loads(self._index_path().read_text(encoding="utf-8"))
        except Exception:
            return {"sessions": []}

    def _write_index(self, payload: dict[str, Any]) -> None:
        tmp = self._base_dir / f"_index_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
            os.replace(tmp, self._index_path())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _index_entry(self, record: LiveRuntimeSessionRecord) -> dict[str, Any]:
        return {
            "session_id": record.session_id,
            "started_at": record.started_at,
            "ended_at": record.ended_at,
            "provider": record.provider,
            "broker": record.broker,
            "live_execution": record.live_execution,
            "symbols": record.symbols,
            "last_state": record.last_state,
            "last_error": record.last_error,
            "preflight_summary": record.preflight_summary,
        }


class SupabaseLiveRuntimeSessionRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._conn: Any = None
        self._schema_checked = False

    def save(self, record: LiveRuntimeSessionRecord) -> None:
        preflight_json = (
            json.dumps(record.preflight_summary, default=str)
            if record.preflight_summary is not None
            else None
        )
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO live_runtime_sessions
                    (
                        session_id,
                        started_at,
                        ended_at,
                        provider,
                        broker,
                        live_execution,
                        symbols,
                        last_state,
                        last_error,
                        preflight_summary
                    )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (session_id) DO UPDATE SET
                    started_at        = EXCLUDED.started_at,
                    ended_at          = EXCLUDED.ended_at,
                    provider          = EXCLUDED.provider,
                    broker            = EXCLUDED.broker,
                    live_execution    = EXCLUDED.live_execution,
                    symbols           = EXCLUDED.symbols,
                    last_state        = EXCLUDED.last_state,
                    last_error        = EXCLUDED.last_error,
                    preflight_summary = EXCLUDED.preflight_summary
                """,
                (
                    record.session_id,
                    record.started_at,
                    record.ended_at,
                    record.provider,
                    record.broker,
                    record.live_execution,
                    record.symbols,
                    record.last_state,
                    record.last_error,
                    preflight_json,
                ),
            )

    def get(self, session_id: str) -> LiveRuntimeSessionRecord | None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                SELECT
                    session_id,
                    started_at,
                    ended_at,
                    provider,
                    broker,
                    live_execution,
                    symbols,
                    last_state,
                    last_error,
                    preflight_summary
                FROM live_runtime_sessions
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return _deserialize_db_row(row)

    def list(self, limit: int = 20) -> list[LiveRuntimeSessionRecord]:
        return self.search(
            LiveRuntimeSessionFilter(page=1, page_size=max(limit, 1))
        ).records

    def search(
        self,
        query: LiveRuntimeSessionFilter | None = None,
    ) -> LiveRuntimeSessionListResult:
        resolved = _normalize_query(query)
        conditions: list[str] = []
        params: list[object] = []
        if resolved.start is not None:
            conditions.append("started_at >= %s")
            params.append(resolved.start)
        if resolved.end is not None:
            conditions.append("started_at <= %s")
            params.append(resolved.end)
        if resolved.provider is not None:
            conditions.append("provider = %s")
            params.append(resolved.provider)
        if resolved.broker is not None:
            conditions.append("broker = %s")
            params.append(resolved.broker)
        if resolved.live_execution is not None:
            conditions.append("live_execution = %s")
            params.append(resolved.live_execution)
        if resolved.state is not None:
            conditions.append("last_state = %s")
            params.append(resolved.state)
        if resolved.symbol is not None:
            conditions.append("%s = ANY(symbols)")
            params.append(resolved.symbol)
        if resolved.has_error is True:
            conditions.append("last_error IS NOT NULL")
        elif resolved.has_error is False:
            conditions.append("last_error IS NULL")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        direction = "ASC" if _normalize_sort(resolved.sort) == "asc" else "DESC"
        offset = (resolved.page - 1) * resolved.page_size
        with self._get_conn().cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM live_runtime_sessions {where}", params)
            total: int = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT
                    session_id,
                    started_at,
                    ended_at,
                    provider,
                    broker,
                    live_execution,
                    symbols,
                    last_state,
                    last_error,
                    preflight_summary
                FROM live_runtime_sessions
                {where}
                ORDER BY started_at {direction} NULLS LAST
                LIMIT %s
                OFFSET %s
                """,
                [*params, resolved.page_size, offset],
            )
            rows = cur.fetchall()
        return LiveRuntimeSessionListResult(
            records=[_deserialize_db_row(row) for row in rows],
            total=total,
            page=resolved.page,
            page_size=resolved.page_size,
        )

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            import psycopg

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
                CREATE TABLE IF NOT EXISTS live_runtime_sessions (
                    session_id         TEXT PRIMARY KEY,
                    started_at         TIMESTAMPTZ NOT NULL,
                    ended_at           TIMESTAMPTZ,
                    provider           TEXT NOT NULL,
                    broker             TEXT NOT NULL,
                    live_execution     TEXT NOT NULL,
                    symbols            TEXT[] NOT NULL DEFAULT '{}',
                    last_state         TEXT NOT NULL,
                    last_error         TEXT,
                    preflight_summary  JSONB,
                    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_live_runtime_sessions_started_at
                ON live_runtime_sessions (started_at DESC)
                """
            )
        self._schema_checked = True


def create_live_runtime_session_repository() -> LiveRuntimeSessionRepository:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return SupabaseLiveRuntimeSessionRepository(database_url)
    base_dir = Path(os.getenv("TRADING_SYSTEM_LIVE_SESSIONS_DIR", "data/live_sessions"))
    return FileLiveRuntimeSessionRepository(base_dir)


def _deserialize_session(data: dict[str, Any]) -> LiveRuntimeSessionRecord:
    return LiveRuntimeSessionRecord(
        session_id=data["session_id"],
        started_at=data["started_at"],
        ended_at=data.get("ended_at"),
        provider=data["provider"],
        broker=data["broker"],
        live_execution=data["live_execution"],
        symbols=list(data.get("symbols", [])),
        last_state=data.get("last_state", "unknown"),
        last_error=data.get("last_error"),
        preflight_summary=data.get("preflight_summary"),
    )


def _deserialize_db_row(row: tuple[Any, ...]) -> LiveRuntimeSessionRecord:
    (
        session_id,
        started_at,
        ended_at,
        provider,
        broker,
        live_execution,
        symbols,
        last_state,
        last_error,
        preflight_summary,
    ) = row
    summary = preflight_summary
    if summary is not None and not isinstance(summary, dict):
        summary = json.loads(summary)
    return LiveRuntimeSessionRecord(
        session_id=session_id,
        started_at=_serialize_timestamp(started_at),
        ended_at=_serialize_timestamp(ended_at) if ended_at else None,
        provider=provider,
        broker=broker,
        live_execution=live_execution,
        symbols=list(symbols or []),
        last_state=last_state,
        last_error=last_error,
        preflight_summary=summary,
    )


def _serialize_timestamp(value: Any) -> str:
    return value.isoformat().replace("+00:00", "Z") if hasattr(value, "isoformat") else str(value)


def _normalize_query(
    query: LiveRuntimeSessionFilter | None,
) -> LiveRuntimeSessionFilter:
    if query is None:
        return LiveRuntimeSessionFilter()
    return LiveRuntimeSessionFilter(
        start=query.start,
        end=query.end,
        provider=_blank_to_none(query.provider),
        broker=_blank_to_none(query.broker),
        live_execution=_blank_to_none(query.live_execution),
        state=_blank_to_none(query.state),
        symbol=_blank_to_none(query.symbol.upper() if query.symbol else None),
        has_error=query.has_error,
        sort=_normalize_sort(query.sort),
        page=max(query.page, 1),
        page_size=max(1, min(query.page_size, 5000)),
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_sort(sort: str) -> str:
    return "asc" if sort == "asc" else "desc"


def _filter_session_entries(
    entries: list[dict[str, Any]],
    query: LiveRuntimeSessionFilter,
) -> list[dict[str, Any]]:
    start_dt = _parse_optional_datetime(query.start)
    end_dt = _parse_optional_datetime(query.end)
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        started_at = _parse_optional_datetime(entry.get("started_at"))
        if start_dt is not None and (started_at is None or started_at < start_dt):
            continue
        if end_dt is not None and (started_at is None or started_at > end_dt):
            continue
        if query.provider is not None and entry.get("provider") != query.provider:
            continue
        if query.broker is not None and entry.get("broker") != query.broker:
            continue
        if (
            query.live_execution is not None
            and entry.get("live_execution") != query.live_execution
        ):
            continue
        if query.state is not None and entry.get("last_state") != query.state:
            continue
        if query.symbol is not None and query.symbol not in entry.get("symbols", []):
            continue
        has_error = bool(entry.get("last_error"))
        if query.has_error is not None and has_error is not query.has_error:
            continue
        filtered.append(entry)
    return filtered


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
