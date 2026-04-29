from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional import for mocked tests
    psycopg = None  # type: ignore[assignment]

from trading_system.backtest.dto import BacktestRunDTO, BacktestRunMetadataDTO
from trading_system.backtest.file_repository import _deserialize_result
from trading_system.backtest.jobs import (
    BacktestJobProgress,
    BacktestJobRecord,
    BacktestJobSnapshot,
    deserialize_job,
    serialize_job,
)
from trading_system.core.compat import UTC

_log = logging.getLogger(__name__)


class SupabaseBacktestRunRepository:
    """BacktestRunRepository backed by Supabase (PostgreSQL via psycopg3).

    The database connection is established lazily on first use so that
    importing this module or instantiating the repository does not block
    application startup when DATABASE_URL is set.
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._conn = None
        self._schema_checked = False

    def _get_conn(self):
        """Return the live connection, (re-)connecting if necessary."""
        if self._conn is None or self._conn.closed:
            if psycopg is None:
                raise ModuleNotFoundError("psycopg is required for SupabaseBacktestRunRepository.")
            self._conn = psycopg.connect(self._database_url, autocommit=True)
            self._schema_checked = False
        self._ensure_schema()
        return self._conn

    def _ensure_schema(self) -> None:
        if self._schema_checked:
            return
        with self._conn.cursor() as cur:
            cur.execute("ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS metadata JSONB")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_jobs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    available_at TIMESTAMPTZ NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    worker_id TEXT,
                    lease_expires_at TIMESTAMPTZ,
                    last_heartbeat_at TIMESTAMPTZ,
                    progress JSONB,
                    cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
                    error TEXT
                )
                """
            )
        self._schema_checked = True

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    def save(self, run: BacktestRunDTO) -> None:
        result_json = None
        if run.result is not None:
            import dataclasses
            result_json = json.dumps(dataclasses.asdict(run.result), default=str)
        metadata_json = None
        if run.metadata is not None:
            import dataclasses
            metadata_json = json.dumps(dataclasses.asdict(run.metadata), default=str)

        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO backtest_runs
                    (
                        run_id, status, started_at, finished_at, input_symbols, mode,
                        metadata, result, error
                    )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status        = EXCLUDED.status,
                    started_at    = EXCLUDED.started_at,
                    finished_at   = EXCLUDED.finished_at,
                    input_symbols = EXCLUDED.input_symbols,
                    mode          = EXCLUDED.mode,
                    metadata      = EXCLUDED.metadata,
                    result        = EXCLUDED.result,
                    error         = EXCLUDED.error
                """,
                (
                    run.run_id,
                    run.status,
                    run.started_at or None,
                    run.finished_at or None,
                    list(run.input_symbols),
                    run.mode,
                    metadata_json,
                    result_json,
                    run.error,
                ),
            )

    def get(self, run_id: str) -> BacktestRunDTO | None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                "SELECT run_id, status, started_at, finished_at, input_symbols, mode, "
                "metadata, result, error"
                " FROM backtest_runs WHERE run_id = %s",
                (run_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return _deserialize_row(row)

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        mode: str | None = None,
    ) -> tuple[list[BacktestRunDTO], int]:
        conditions: list[str] = []
        params: list[object] = []

        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        if mode is not None:
            conditions.append("mode = %s")
            params.append(mode)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        offset = (page - 1) * page_size

        with self._get_conn().cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM backtest_runs {where}", params)
            total: int = cur.fetchone()[0]  # type: ignore[index]

            cols = (
                "run_id, status, started_at, finished_at, input_symbols, mode, "
                "metadata, result, error"
            )
            cur.execute(
                f"SELECT {cols} FROM backtest_runs {where}"
                f" ORDER BY started_at DESC NULLS LAST"
                f" LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            )
            rows = cur.fetchall()

        dtos = [_deserialize_row(row) for row in rows]
        return dtos, total

    def delete(self, run_id: str) -> bool:
        with self._get_conn().cursor() as cur:
            cur.execute("DELETE FROM backtest_runs WHERE run_id = %s", (run_id,))
            return cur.rowcount > 0

    def clear(self) -> None:
        with self._get_conn().cursor() as cur:
            cur.execute("DELETE FROM backtest_runs")

    def rebuild_index(self) -> None:
        """No-op: PostgreSQL does not need index rebuilding."""
        _log.debug("rebuild_index called on SupabaseBacktestRunRepository — no-op")

    # ------------------------------------------------------------------
    # Backtest job repository implementation
    # ------------------------------------------------------------------

    def enqueue(self, job: BacktestJobRecord) -> None:
        data = serialize_job(job)
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO backtest_jobs (
                    run_id, status, payload, created_at, available_at,
                    attempt_count, max_attempts, worker_id, lease_expires_at,
                    last_heartbeat_at, progress, cancel_requested, error
                )
                VALUES (
                    %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s, %s
                )
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    payload = EXCLUDED.payload,
                    created_at = EXCLUDED.created_at,
                    available_at = EXCLUDED.available_at,
                    attempt_count = EXCLUDED.attempt_count,
                    max_attempts = EXCLUDED.max_attempts,
                    worker_id = EXCLUDED.worker_id,
                    lease_expires_at = EXCLUDED.lease_expires_at,
                    last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                    progress = EXCLUDED.progress,
                    cancel_requested = EXCLUDED.cancel_requested,
                    error = EXCLUDED.error
                """,
                _job_params_from_data(data),
            )

    def get_job(self, run_id: str) -> BacktestJobRecord | None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                SELECT run_id, status, payload, created_at, available_at,
                       attempt_count, max_attempts, worker_id, lease_expires_at,
                       last_heartbeat_at, progress, cancel_requested, error
                FROM backtest_jobs
                WHERE run_id = %s
                """,
                (run_id,),
            )
            row = cur.fetchone()
        return _deserialize_job_row(row) if row is not None else None

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> BacktestJobRecord | None:
        current = now or datetime.now(UTC)
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                WITH candidate AS (
                    SELECT run_id
                    FROM backtest_jobs
                    WHERE cancel_requested = FALSE
                      AND status IN ('queued', 'running')
                      AND available_at <= %s
                      AND attempt_count < max_attempts
                      AND (
                          status = 'queued'
                          OR lease_expires_at IS NULL
                          OR lease_expires_at <= %s
                      )
                    ORDER BY available_at ASC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE backtest_jobs AS job
                SET status = 'running',
                    worker_id = %s,
                    attempt_count = job.attempt_count + 1,
                    lease_expires_at = %s,
                    last_heartbeat_at = %s,
                    error = NULL
                FROM candidate
                WHERE job.run_id = candidate.run_id
                RETURNING job.run_id, job.status, job.payload, job.created_at, job.available_at,
                          job.attempt_count, job.max_attempts, job.worker_id,
                          job.lease_expires_at, job.last_heartbeat_at, job.progress,
                          job.cancel_requested, job.error
                """,
                (
                    current,
                    current,
                    worker_id,
                    current + timedelta(seconds=lease_seconds),
                    current,
                ),
            )
            row = cur.fetchone()
        return _deserialize_job_row(row) if row is not None else None

    def heartbeat(
        self,
        run_id: str,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> BacktestJobRecord | None:
        current = now or datetime.now(UTC)
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                UPDATE backtest_jobs
                SET lease_expires_at = %s,
                    last_heartbeat_at = %s
                WHERE run_id = %s AND worker_id = %s AND status = 'running'
                RETURNING run_id, status, payload, created_at, available_at,
                          attempt_count, max_attempts, worker_id, lease_expires_at,
                          last_heartbeat_at, progress, cancel_requested, error
                """,
                (
                    current + timedelta(seconds=lease_seconds),
                    current,
                    run_id,
                    worker_id,
                ),
            )
            row = cur.fetchone()
        return _deserialize_job_row(row) if row is not None else None

    def update_progress(
        self,
        run_id: str,
        progress: BacktestJobProgress,
        *,
        worker_id: str | None = None,
    ) -> BacktestJobRecord | None:
        data = serialize_job(
            BacktestJobRecord.queued(run_id=run_id, payload={})
        )
        data["progress"] = {
            "processed_bars": progress.processed_bars,
            "total_bars": progress.total_bars,
            "percent": progress.percent,
            "last_bar_timestamp": progress.last_bar_timestamp,
            "updated_at": progress.updated_at,
        }
        conditions = ["run_id = %s"]
        params: list[object] = [json.dumps(data["progress"]), run_id]
        if worker_id is not None:
            conditions.append("worker_id = %s")
            params.append(worker_id)
        with self._get_conn().cursor() as cur:
            cur.execute(
                f"""
                UPDATE backtest_jobs
                SET progress = %s::jsonb
                WHERE {' AND '.join(conditions)}
                RETURNING run_id, status, payload, created_at, available_at,
                          attempt_count, max_attempts, worker_id, lease_expires_at,
                          last_heartbeat_at, progress, cancel_requested, error
                """,
                params,
            )
            row = cur.fetchone()
        return _deserialize_job_row(row) if row is not None else None

    def request_cancel(self, run_id: str) -> BacktestJobRecord | None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                UPDATE backtest_jobs
                SET cancel_requested = TRUE
                WHERE run_id = %s
                RETURNING run_id, status, payload, created_at, available_at,
                          attempt_count, max_attempts, worker_id, lease_expires_at,
                          last_heartbeat_at, progress, cancel_requested, error
                """,
                (run_id,),
            )
            row = cur.fetchone()
        return _deserialize_job_row(row) if row is not None else None

    def complete(self, run_id: str) -> BacktestJobRecord | None:
        return self._mark_job_terminal(run_id, status="succeeded", error=None)

    def fail(self, run_id: str, error: str) -> BacktestJobRecord | None:
        return self._mark_job_terminal(run_id, status="failed", error=error)

    def cancel(self, run_id: str, reason: str | None = None) -> BacktestJobRecord | None:
        return self._mark_job_terminal(
            run_id,
            status="cancelled",
            error=reason or "Backtest cancelled.",
        )

    def snapshot(self, *, now: datetime | None = None) -> BacktestJobSnapshot:
        current = now or datetime.now(UTC)
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'queued' AND cancel_requested = FALSE),
                    COUNT(*) FILTER (WHERE status = 'running'),
                    COUNT(*) FILTER (
                        WHERE status = 'running'
                          AND lease_expires_at IS NOT NULL
                          AND lease_expires_at <= %s
                    ),
                    COUNT(*) FILTER (
                        WHERE cancel_requested = TRUE AND status <> 'cancelled'
                    ),
                    MIN(created_at) FILTER (
                        WHERE status = 'queued' AND cancel_requested = FALSE
                    )
                FROM backtest_jobs
                """,
                (current,),
            )
            row = cur.fetchone()
        oldest_age = None
        if row and row[4] is not None:
            oldest_age = max(0.0, (current - _as_utc_datetime(row[4])).total_seconds())
        return BacktestJobSnapshot(
            queued_count=int(row[0] or 0),
            running_count=int(row[1] or 0),
            stale_count=int(row[2] or 0),
            cancelled_count=int(row[3] or 0),
            oldest_queued_age_seconds=oldest_age,
        )

    def clear_jobs(self) -> None:
        with self._get_conn().cursor() as cur:
            cur.execute("DELETE FROM backtest_jobs")

    def _mark_job_terminal(
        self,
        run_id: str,
        *,
        status: str,
        error: str | None,
    ) -> BacktestJobRecord | None:
        with self._get_conn().cursor() as cur:
            cur.execute(
                """
                UPDATE backtest_jobs
                SET status = %s,
                    lease_expires_at = NULL,
                    cancel_requested = CASE
                        WHEN %s = 'cancelled' THEN TRUE
                        ELSE cancel_requested
                    END,
                    error = %s
                WHERE run_id = %s
                RETURNING run_id, status, payload, created_at, available_at,
                          attempt_count, max_attempts, worker_id, lease_expires_at,
                          last_heartbeat_at, progress, cancel_requested, error
                """,
                (status, status, error, run_id),
            )
            row = cur.fetchone()
        return _deserialize_job_row(row) if row is not None else None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _deserialize_row(row: tuple) -> BacktestRunDTO:
    (
        run_id,
        status,
        started_at,
        finished_at,
        input_symbols,
        mode,
        metadata_raw,
        result_raw,
        error,
    ) = row

    result = None
    if result_raw is not None:
        data = result_raw if isinstance(result_raw, dict) else json.loads(result_raw)
        result = _deserialize_result(data)
    metadata = None
    if metadata_raw is not None:
        parsed = metadata_raw if isinstance(metadata_raw, dict) else json.loads(metadata_raw)
        metadata = BacktestRunMetadataDTO(
            provider=parsed.get("provider"),
            broker=parsed.get("broker"),
            strategy_profile_id=parsed.get("strategy_profile_id"),
            pattern_set_id=parsed.get("pattern_set_id"),
            source=parsed.get("source"),
            requested_by=parsed.get("requested_by"),
            notes=parsed.get("notes"),
        )

    return BacktestRunDTO(
        run_id=run_id,
        status=status,
        started_at=_serialize_db_timestamp(started_at),
        finished_at=_serialize_db_timestamp(finished_at) if finished_at else None,
        input_symbols=list(input_symbols or []),
        mode=mode or "",
        metadata=metadata,
        result=result,
        error=error,
    )


def _serialize_db_timestamp(value: datetime | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _job_params_from_data(data: dict) -> tuple:
    return (
        data["run_id"],
        data["status"],
        json.dumps(data["payload"], default=str),
        data["created_at"],
        data["available_at"],
        data["attempt_count"],
        data["max_attempts"],
        data["worker_id"],
        data["lease_expires_at"],
        data["last_heartbeat_at"],
        json.dumps(data["progress"], default=str),
        data["cancel_requested"],
        data["error"],
    )


def _deserialize_job_row(row: tuple) -> BacktestJobRecord:
    (
        run_id,
        status,
        payload,
        created_at,
        available_at,
        attempt_count,
        max_attempts,
        worker_id,
        lease_expires_at,
        last_heartbeat_at,
        progress,
        cancel_requested,
        error,
    ) = row
    return deserialize_job(
        {
            "run_id": run_id,
            "status": status,
            "payload": payload if isinstance(payload, dict) else json.loads(payload or "{}"),
            "created_at": _serialize_db_timestamp(created_at),
            "available_at": _serialize_db_timestamp(available_at),
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
            "worker_id": worker_id,
            "lease_expires_at": (
                _serialize_db_timestamp(lease_expires_at) if lease_expires_at else None
            ),
            "last_heartbeat_at": (
                _serialize_db_timestamp(last_heartbeat_at) if last_heartbeat_at else None
            ),
            "progress": (
                progress if isinstance(progress, dict) else json.loads(progress or "{}")
            ),
            "cancel_requested": cancel_requested,
            "error": error,
        }
    )


def _as_utc_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
