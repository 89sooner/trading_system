from __future__ import annotations

from unittest.mock import MagicMock

from trading_system.execution.order_audit import (
    FileOrderAuditRepository,
    OrderAuditRecord,
    SupabaseOrderAuditRepository,
)


def _record(**kwargs) -> OrderAuditRecord:
    defaults = dict(
        record_id="oa_1",
        scope="backtest",
        owner_id="run-1",
        event="order.filled",
        symbol="BTCUSDT",
        side="buy",
        requested_quantity="1",
        filled_quantity="1",
        price="100",
        status="filled",
        reason=None,
        timestamp="2024-01-01T00:00:00Z",
        payload={"symbol": "BTCUSDT", "status": "filled"},
        broker_order_id=None,
    )
    defaults.update(kwargs)
    return OrderAuditRecord(**defaults)


def _make_supabase_repo():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.closed = False

    repo = SupabaseOrderAuditRepository("postgresql://fake/db")
    repo._conn = mock_conn
    return repo, mock_cursor


def test_file_order_audit_repository_appends_and_filters(tmp_path):
    repo = FileOrderAuditRepository(tmp_path)
    repo.append(_record(record_id="oa_1", owner_id="run-1", symbol="BTCUSDT"))
    repo.append(_record(record_id="oa_2", owner_id="run-2", symbol="ETHUSDT"))

    records = repo.list(scope="backtest", owner_id="run-1")

    assert len(records) == 1
    assert records[0].record_id == "oa_1"
    assert records[0].payload["status"] == "filled"


def test_supabase_order_audit_repository_creates_schema_on_append():
    repo, cursor = _make_supabase_repo()

    repo.append(_record())

    calls = [call.args[0] for call in cursor.execute.call_args_list]
    assert any("CREATE TABLE IF NOT EXISTS order_audit_records" in sql for sql in calls)
    assert any("INSERT INTO order_audit_records" in sql for sql in calls)


def test_supabase_order_audit_repository_list_deserializes_rows():
    repo, cursor = _make_supabase_repo()
    cursor.fetchall.return_value = [
        (
            "oa_1",
            "backtest",
            "run-1",
            "order.filled",
            "BTCUSDT",
            "buy",
            "1",
            "1",
            "100",
            "filled",
            None,
            "2024-01-01T00:00:00Z",
            {"symbol": "BTCUSDT"},
            None,
        )
    ]

    records = repo.list(scope="backtest", owner_id="run-1")

    assert len(records) == 1
    assert records[0].record_id == "oa_1"
    assert records[0].symbol == "BTCUSDT"
