from __future__ import annotations

from types import SimpleNamespace

import pytest

from trading_system.api.errors import RequestValidationError
from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.schemas import BacktestRetentionPruneRequestDTO
from trading_system.backtest.dispatcher import BacktestDispatcherSnapshot
from trading_system.backtest.dto import BacktestRunDTO
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
