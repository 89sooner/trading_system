from __future__ import annotations

from trading_system.app.live_runtime_history import (
    FileLiveRuntimeSessionRepository,
    LiveRuntimeSessionRecord,
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
