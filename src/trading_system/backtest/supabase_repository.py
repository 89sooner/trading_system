from __future__ import annotations

import json
import logging

import psycopg

from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.file_repository import _deserialize_result

_log = logging.getLogger(__name__)


class SupabaseBacktestRunRepository:
    """BacktestRunRepository backed by Supabase (PostgreSQL via psycopg3)."""

    def __init__(self, database_url: str) -> None:
        self._conn = psycopg.connect(database_url, autocommit=True)

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    def save(self, run: BacktestRunDTO) -> None:
        result_json = None
        if run.result is not None:
            import dataclasses
            result_json = json.dumps(dataclasses.asdict(run.result), default=str)

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO backtest_runs
                    (run_id, status, started_at, finished_at, input_symbols, mode, result, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status        = EXCLUDED.status,
                    started_at    = EXCLUDED.started_at,
                    finished_at   = EXCLUDED.finished_at,
                    input_symbols = EXCLUDED.input_symbols,
                    mode          = EXCLUDED.mode,
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
                    result_json,
                    run.error,
                ),
            )

    def get(self, run_id: str) -> BacktestRunDTO | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT run_id, status, started_at, finished_at, input_symbols, mode, result, error"
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

        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM backtest_runs {where}", params)
            total: int = cur.fetchone()[0]  # type: ignore[index]

            cols = "run_id, status, started_at, finished_at, input_symbols, mode, result, error"
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
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM backtest_runs WHERE run_id = %s", (run_id,))
            return cur.rowcount > 0

    def clear(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM backtest_runs")

    def rebuild_index(self) -> None:
        """No-op: PostgreSQL does not need index rebuilding."""
        _log.debug("rebuild_index called on SupabaseBacktestRunRepository — no-op")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _deserialize_row(row: tuple) -> BacktestRunDTO:
    run_id, status, started_at, finished_at, input_symbols, mode, result_raw, error = row

    result = None
    if result_raw is not None:
        data = result_raw if isinstance(result_raw, dict) else json.loads(result_raw)
        result = _deserialize_result(data)

    return BacktestRunDTO(
        run_id=run_id,
        status=status,
        started_at=str(started_at) if started_at else "",
        finished_at=str(finished_at) if finished_at else "",
        input_symbols=list(input_symbols or []),
        mode=mode or "",
        result=result,
        error=error,
    )
