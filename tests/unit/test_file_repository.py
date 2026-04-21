"""Unit tests for FileBacktestRunRepository."""
from __future__ import annotations

from trading_system.backtest.dto import (
    BacktestResultDTO,
    BacktestRunDTO,
    BacktestRunMetadataDTO,
    DrawdownPointDTO,
    EquityPointDTO,
    EventDTO,
    SummaryDTO,
)
from trading_system.backtest.file_repository import FileBacktestRunRepository


def _make_run(
    run_id: str = "run-1",
    status: str = "succeeded",
    mode: str = "backtest",
    started_at: str = "2024-01-01T00:00:00Z",
    include_result: bool = False,
) -> BacktestRunDTO:
    result = None
    if include_result:
        result = BacktestResultDTO(
            summary=SummaryDTO(
                return_value="0.05",
                max_drawdown="0.02",
                volatility="0.01",
                win_rate="0.6",
            ),
            equity_curve=[EquityPointDTO(timestamp="2024-01-01T00:00:00Z", equity="10500")],
            drawdown_curve=[DrawdownPointDTO(timestamp="2024-01-01T00:00:00Z", drawdown="0.02")],
            signals=[EventDTO(event="signal.buy", payload={"symbol": "AAPL"})],
            orders=[EventDTO(event="order.filled", payload={"symbol": "AAPL"})],
            risk_rejections=[],
        )
    return BacktestRunDTO(
        run_id=run_id,
        status=status,
        started_at=started_at,
        finished_at="2024-01-01T01:00:00Z",
        input_symbols=["AAPL"],
        mode=mode,
        result=result,
    )


def test_save_and_get_roundtrip(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    run = _make_run("run-1", include_result=True)
    repo.save(run)

    retrieved = repo.get("run-1")
    assert retrieved is not None
    assert retrieved.run_id == "run-1"
    assert retrieved.status == "succeeded"
    assert retrieved.result is not None
    assert retrieved.result.summary.return_value == "0.05"
    assert len(retrieved.result.equity_curve) == 1
    assert retrieved.result.equity_curve[0].equity == "10500"


def test_get_missing_returns_none(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    assert repo.get("nonexistent") is None


def test_list_empty_directory(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    runs, total = repo.list()
    assert runs == []
    assert total == 0


def test_list_pagination(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    for i in range(15):
        run = _make_run(
            run_id=f"run-{i:02d}",
            started_at=f"2024-01-{i + 1:02d}T00:00:00Z",
        )
        repo.save(run)

    page1, total = repo.list(page=1, page_size=10)
    assert total == 15
    assert len(page1) == 10

    page2, total2 = repo.list(page=2, page_size=10)
    assert total2 == 15
    assert len(page2) == 5

    # Latest first
    assert page1[0].started_at > page1[-1].started_at


def test_list_status_filter(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    repo.save(_make_run("run-1", status="succeeded"))
    repo.save(_make_run("run-2", status="failed"))
    repo.save(_make_run("run-3", status="succeeded"))

    runs, total = repo.list(status="succeeded")
    assert total == 2
    assert all(r.status == "succeeded" for r in runs)


def test_list_mode_filter(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    repo.save(_make_run("run-1", mode="backtest"))
    repo.save(_make_run("run-2", mode="live"))

    runs, total = repo.list(mode="backtest")
    assert total == 1
    assert runs[0].run_id == "run-1"


def test_delete_removes_run(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    repo.save(_make_run("run-1"))

    result = repo.delete("run-1")
    assert result is True
    assert repo.get("run-1") is None

    runs, total = repo.list()
    assert total == 0


def test_delete_missing_returns_false(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    assert repo.delete("nonexistent") is False


def test_rebuild_index(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    repo.save(_make_run("run-1"))
    repo.save(_make_run("run-2"))

    # Delete the index
    (tmp_path / "_index.json").unlink()

    # Rebuild
    repo.rebuild_index()

    runs, total = repo.list()
    assert total == 2
    run_ids = {r.run_id for r in runs}
    assert run_ids == {"run-1", "run-2"}


def test_clear_removes_all_files(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    repo.save(_make_run("run-1"))
    repo.save(_make_run("run-2"))

    repo.clear()

    json_files = [p for p in tmp_path.glob("*.json") if p.name != "_index.json"]
    assert len(json_files) == 0
    _, total = repo.list()
    assert total == 0


def test_save_updates_existing_in_index(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    run = _make_run("run-1", status="running")
    repo.save(run)

    updated = BacktestRunDTO(
        run_id="run-1",
        status="succeeded",
        started_at=run.started_at,
        finished_at="2024-01-01T01:00:00Z",
        input_symbols=["AAPL"],
        mode="backtest",
    )
    repo.save(updated)

    runs, total = repo.list()
    assert total == 1
    assert runs[0].status == "succeeded"


def test_pending_run_roundtrip_preserves_nullable_finished_at(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    run = BacktestRunDTO.queued(
        run_id="queued-run",
        started_at="2024-01-01T00:00:00Z",
        input_symbols=["AAPL"],
        mode="backtest",
    )
    repo.save(run)

    retrieved = repo.get("queued-run")
    assert retrieved is not None
    assert retrieved.status == "queued"
    assert retrieved.finished_at is None


def test_save_and_get_roundtrip_preserves_metadata(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    run = BacktestRunDTO(
        run_id="run-meta",
        status="succeeded",
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T01:00:00Z",
        input_symbols=["AAPL"],
        mode="backtest",
        metadata=BacktestRunMetadataDTO(
            provider="mock",
            broker="paper",
            strategy_profile_id="trend-v1",
            source="frontend",
            notes="metadata roundtrip",
        ),
    )
    repo.save(run)

    retrieved = repo.get("run-meta")

    assert retrieved is not None
    assert retrieved.metadata is not None
    assert retrieved.metadata.provider == "mock"
    assert retrieved.metadata.strategy_profile_id == "trend-v1"
    assert retrieved.metadata.notes == "metadata roundtrip"
