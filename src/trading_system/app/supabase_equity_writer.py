from __future__ import annotations

from datetime import datetime

import psycopg


class SupabaseEquityWriter:
    """EquityWriter backed by Supabase (PostgreSQL via psycopg3)."""

    def __init__(self, database_url: str, session_id: str) -> None:
        self._session_id = session_id
        self._conn = psycopg.connect(database_url, autocommit=True)
        self._ensure_schema_ready()

    @property
    def session_id(self) -> str:
        return self._session_id

    def append(self, timestamp: str, equity: str, cash: str, positions_value: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO equity_snapshots"
                " (session_id, timestamp, equity, cash, positions_value)"
                " VALUES (%s, %s, %s, %s, %s)",
                (self._session_id, timestamp, equity, cash, positions_value),
            )

    def read_recent(self, limit: int = 300) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT timestamp, equity, cash, positions_value"
                " FROM equity_snapshots"
                " WHERE session_id = %s"
                " ORDER BY timestamp DESC"
                " LIMIT %s",
                (self._session_id, limit),
            )
            rows = cur.fetchall()

        # Re-sort ascending (oldest first) to match FileEquityWriter behaviour.
        result = [
            {
                "timestamp": _normalize_timestamp(r[0]),
                "equity": str(r[1]) if r[1] is not None else "",
                "cash": str(r[2]) if r[2] is not None else "",
                "positions_value": str(r[3]) if r[3] is not None else "",
            }
            for r in reversed(rows)
        ]
        return result

    def _ensure_schema_ready(self) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.equity_snapshots')")
                table_name = cur.fetchone()[0]
        except Exception as exc:
            raise RuntimeError(
                "Failed to verify Supabase equity storage. "
                "Check DATABASE_URL connectivity before starting live paper mode."
            ) from exc

        if table_name is None:
            raise RuntimeError(
                "Missing required table 'public.equity_snapshots'. "
                "Apply scripts/migrations/002_create_equity_snapshots.sql before "
                "starting live paper mode with DATABASE_URL."
            )


def _normalize_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
