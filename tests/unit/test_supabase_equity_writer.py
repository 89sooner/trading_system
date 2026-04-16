"""Unit tests for SupabaseEquityWriter using mocked psycopg3 connections."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_writer(session_id: str = "sess-1"):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("equity_snapshots",)  # table exists
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.closed = False  # Prevent _get_conn from reconnecting

    with patch("psycopg.connect", return_value=mock_conn):
        from trading_system.app.supabase_equity_writer import SupabaseEquityWriter
        writer = SupabaseEquityWriter("postgresql://fake/db", session_id)
        writer._get_conn()  # Trigger lazy connection + _ensure_schema_ready inside patch

    return writer, mock_conn, mock_cursor


class TestSessionId:
    def test_session_id_returns_constructor_value(self):
        writer, _, _ = _make_writer("my-session")
        assert writer.session_id == "my-session"

    def test_constructor_validates_equity_table_exists(self):
        _, _, mock_cursor = _make_writer("validated-session")
        first_call = mock_cursor.execute.call_args_list[0]
        sql = first_call.args[0]
        assert "to_regclass" in sql

    def test_constructor_raises_clear_error_when_table_missing(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)  # table not found
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            from trading_system.app.supabase_equity_writer import SupabaseEquityWriter
            writer = SupabaseEquityWriter("postgresql://fake/db", "missing-table")
            with pytest.raises(RuntimeError, match="002_create_equity_snapshots.sql"):
                writer._get_conn()  # Schema check happens lazily on first connection


class TestAppend:
    def test_append_executes_insert(self):
        writer, _, mock_cursor = _make_writer()
        writer.append("2024-01-01T00:00:00", "1000", "500", "500")
        assert mock_cursor.execute.called
        sql, params = mock_cursor.execute.call_args[0]
        assert "INSERT INTO equity_snapshots" in sql
        assert params[0] == "sess-1"
        assert params[1] == "2024-01-01T00:00:00"
        assert params[2] == "1000"


class TestReadRecent:
    def test_read_recent_returns_list_of_dicts(self):
        writer, _, mock_cursor = _make_writer()
        mock_cursor.fetchall.return_value = [
            ("2024-01-01T00:01:00", "1100", "600", "500"),
            ("2024-01-01T00:00:00", "1000", "500", "500"),
        ]
        result = writer.read_recent(limit=10)
        # Re-sorted ascending (oldest first)
        assert len(result) == 2
        assert result[0]["timestamp"] == "2024-01-01T00:00:00"
        assert result[1]["timestamp"] == "2024-01-01T00:01:00"
        assert result[0]["equity"] == "1000"

    def test_read_recent_normalizes_datetime_rows_to_isoformat(self):
        writer, _, mock_cursor = _make_writer()
        mock_cursor.fetchall.return_value = [
            (datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc), "1100", "600", "500"),
            (datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), "1000", "500", "500"),
        ]

        result = writer.read_recent(limit=10)

        assert result[0]["timestamp"] == "2024-01-01T00:00:00+00:00"
        assert result[1]["timestamp"] == "2024-01-01T00:01:00+00:00"

    def test_read_recent_empty_returns_empty_list(self):
        writer, _, mock_cursor = _make_writer()
        mock_cursor.fetchall.return_value = []
        assert writer.read_recent() == []

    def test_read_recent_passes_session_id_and_limit(self):
        writer, _, mock_cursor = _make_writer("sess-x")
        mock_cursor.fetchall.return_value = []
        writer.read_recent(limit=50)
        _, params = mock_cursor.execute.call_args[0]
        assert params[0] == "sess-x"
        assert params[1] == 50


# ---------------------------------------------------------------------------
# Integration-style test — skipped when DATABASE_URL is not set
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") or os.environ.get("RUN_SUPABASE_INTEGRATION_TESTS") != "1",
    reason="Supabase integration test requires DATABASE_URL and RUN_SUPABASE_INTEGRATION_TESTS=1",
)
class TestIntegration:
    def test_append_and_read_roundtrip(self):
        from trading_system.app.supabase_equity_writer import SupabaseEquityWriter
        writer = SupabaseEquityWriter(os.environ["DATABASE_URL"], "integration-equity-test")
        writer.append("2024-01-01T00:00:00", "1000", "500", "500")
        result = writer.read_recent(limit=5)
        assert len(result) >= 1
        assert result[-1]["equity"] == "1000"
