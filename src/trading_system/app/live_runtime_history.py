from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


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


class LiveRuntimeSessionRepository(Protocol):
    def save(self, record: LiveRuntimeSessionRecord) -> None:
        ...

    def get(self, session_id: str) -> LiveRuntimeSessionRecord | None:
        ...

    def list(self, limit: int = 20) -> list[LiveRuntimeSessionRecord]:
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
        with self._lock:
            index = self._read_index()
        sessions = sorted(
            index.get("sessions", []),
            key=lambda item: item.get("started_at", ""),
            reverse=True,
        )
        selected = sessions[: max(limit, 1)]
        return [
            LiveRuntimeSessionRecord(
                session_id=item["session_id"],
                started_at=item["started_at"],
                ended_at=item.get("ended_at"),
                provider=item["provider"],
                broker=item["broker"],
                live_execution=item["live_execution"],
                symbols=item.get("symbols", []),
                last_state=item.get("last_state", "unknown"),
                last_error=item.get("last_error"),
                preflight_summary=item.get("preflight_summary"),
            )
            for item in selected
        ]

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
                ORDER BY started_at DESC NULLS LAST
                LIMIT %s
                """,
                (max(limit, 1),),
            )
            rows = cur.fetchall()
        return [_deserialize_db_row(row) for row in rows]

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            import psycopg

            self._conn = psycopg.connect(self._database_url, autocommit=True)
        return self._conn


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
