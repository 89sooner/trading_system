from __future__ import annotations

from types import SimpleNamespace

import pytest

from trading_system.api.errors import RequestValidationError
from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.schemas import BacktestRetentionPruneRequestDTO
from trading_system.backtest.dispatcher import BacktestDispatcherSnapshot
from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.file_repository import FileBacktestRunRepository
from trading_system.backtest.jobs import BacktestJobRecord
from trading_system.backtest.repository import InMemoryBacktestRunRepository


class FakeDispatcher:
    def snapshot(self) -> BacktestDispatcherSnapshot:
        return BacktestDispatcherSnapshot(running=True, queue_depth=2, max_queue_size=32)


def test_dispatcher_status_maps_snapshot():
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(backtest_dispatcher=FakeDispatcher()))
    )

    response = backtest_routes.get_backtest_dispatcher_status(request)

    assert response.running is True
    assert response.queue_depth == 2
    assert response.max_queue_size == 32


def test_retention_preview_and_prune_require_confirmation():
    repo = InMemoryBacktestRunRepository()
    repo.save(
        BacktestRunDTO.failed(
            run_id="old-run",
            started_at="2024-01-01T00:00:00Z",
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
            error="old",
        )
    )
    original_repo = backtest_routes._RUN_REPOSITORY
    backtest_routes._RUN_REPOSITORY = repo
    try:
        preview = backtest_routes.preview_backtest_retention(
            cutoff="2025-01-01T00:00:00Z",
            status="failed",
        )
        with pytest.raises(RequestValidationError):
            backtest_routes.prune_backtest_retention(
                BacktestRetentionPruneRequestDTO(
                    cutoff="2025-01-01T00:00:00Z",
                    status="failed",
                )
            )
        pruned = backtest_routes.prune_backtest_retention(
            BacktestRetentionPruneRequestDTO(
                cutoff="2025-01-01T00:00:00Z",
                status="failed",
                confirm="DELETE",
            )
        )
    finally:
        backtest_routes._RUN_REPOSITORY = original_repo

    assert preview.run_ids == ["old-run"]
    assert pruned.deleted_count == 1
    assert repo.get("old-run") is None


def test_cancel_queued_backtest_marks_run_and_job_cancelled(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    repo.save(
        BacktestRunDTO.queued(
            run_id="run-1",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    repo.enqueue(
        BacktestJobRecord.queued(
            run_id="run-1",
            payload={"mode": "backtest"},
            created_at="2024-01-01T00:00:00Z",
        )
    )
    original_run_repo = backtest_routes._RUN_REPOSITORY
    original_job_repo = backtest_routes._JOB_REPOSITORY
    backtest_routes._RUN_REPOSITORY = repo
    backtest_routes._JOB_REPOSITORY = repo
    try:
        response = backtest_routes.cancel_backtest_run("run-1")
    finally:
        backtest_routes._RUN_REPOSITORY = original_run_repo
        backtest_routes._JOB_REPOSITORY = original_job_repo

    assert response.status == "cancelled"
    assert repo.get("run-1").status == "cancelled"
    assert repo.get_job("run-1").status == "cancelled"
