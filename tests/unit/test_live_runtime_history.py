from __future__ import annotations

from unittest.mock import MagicMock

from trading_system.app.live_runtime_history import (
    FileLiveRuntimeSessionRepository,
    LiveRuntimeSessionRecord,
    SupabaseLiveRuntimeSessionRepository,
)


def _record(
    session_id: str = "live_1",
    started_at: str = "2026-04-19T00:00:00Z",
) -> LiveRuntimeSessionRecord:
    return LiveRuntimeSessionRecord(
        session_id=session_id,
        started_at=started_at,
        ended_at="2026-04-19T00:05:00Z",
        provider="kis",
        broker="kis",
        live_execution="paper",
        symbols=["005930"],
        last_state="stopped",
        last_error=None,
        preflight_summary={"message": "ok", "ready": True},
    )


def test_file_live_runtime_session_repository_roundtrip(tmp_path) -> None:
    repo = FileLiveRuntimeSessionRepository(tmp_path)
    repo.save(_record())

    fetched = repo.get("live_1")

    assert fetched is not None
    assert fetched.provider == "kis"
    assert fetched.preflight_summary == {"message": "ok", "ready": True}


def test_file_live_runtime_session_repository_lists_latest_first(tmp_path) -> None:
    repo = FileLiveRuntimeSessionRepository(tmp_path)
    repo.save(_record("live_1", "2026-04-19T00:00:00Z"))
    repo.save(_record("live_2", "2026-04-19T00:10:00Z"))

    items = repo.list(limit=1)

    assert len(items) == 1
    assert items[0].session_id == "live_2"


def test_supabase_live_runtime_session_repository_ensures_schema() -> None:
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.closed = False
    repo = SupabaseLiveRuntimeSessionRepository("postgresql://fake/db")
    repo._conn = mock_conn

    repo.save(_record())

    calls = [call.args[0] for call in mock_cursor.execute.call_args_list]
    assert any("CREATE TABLE IF NOT EXISTS live_runtime_sessions" in sql for sql in calls)
    assert any("idx_live_runtime_sessions_started_at" in sql for sql in calls)
