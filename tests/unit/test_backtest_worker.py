from __future__ import annotations

import signal
from datetime import datetime, timedelta
from decimal import Decimal

from trading_system.api.routes import backtest as backtest_routes
from trading_system.app import backtest_worker
from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.engine import BacktestResult
from trading_system.backtest.file_repository import FileBacktestRunRepository
from trading_system.backtest.jobs import BacktestJobRecord
from trading_system.core.compat import UTC
from trading_system.core.types import MarketBar
from trading_system.portfolio.book import PortfolioBook


def _payload() -> dict:
    return {
        "mode": "backtest",
        "symbols": ["BTCUSDT"],
        "provider": "mock",
        "broker": "paper",
        "live_execution": "preflight",
        "risk": {
            "max_position": "1",
            "max_notional": "100000",
            "max_order_size": "0.25",
        },
        "backtest": {
            "starting_cash": "10000",
            "fee_bps": "5",
            "trade_quantity": "0.1",
        },
    }


def test_backtest_worker_once_processes_one_job(tmp_path, monkeypatch) -> None:
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
            payload=_payload(),
            created_at="2024-01-01T00:00:00Z",
        )
    )
    monkeypatch.setattr(backtest_routes, "_RUN_REPOSITORY", repo)
    monkeypatch.setattr(backtest_routes, "_JOB_REPOSITORY", repo)
    monkeypatch.setattr(backtest_routes, "_ORDER_AUDIT_REPOSITORY", None)

    exit_code = backtest_worker.run(["--worker-id", "test-worker", "--once"])

    assert exit_code == 0
    run = repo.get("run-1")
    job = repo.get_job("run-1")
    assert run is not None
    assert run.status == "succeeded"
    assert job is not None
    assert job.status == "succeeded"
    assert job.progress.percent == 100.0


def test_backtest_job_progress_updates_are_throttled(tmp_path, monkeypatch) -> None:
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
            payload=_payload(),
            created_at="2024-01-01T00:00:00Z",
        )
    )
    claimed = repo.claim_next(worker_id="test-worker", lease_seconds=30)
    assert claimed is not None
    monkeypatch.setattr(backtest_routes, "_RUN_REPOSITORY", repo)
    monkeypatch.setattr(backtest_routes, "_JOB_REPOSITORY", repo)
    monkeypatch.setattr(backtest_routes, "_ORDER_AUDIT_REPOSITORY", None)

    progress_writes = 0
    original_update_progress = repo.update_progress

    def _update_progress_spy(*args, **kwargs):
        nonlocal progress_writes
        progress_writes += 1
        return original_update_progress(*args, **kwargs)

    class FakeServices:
        def run(self, *, audit_owner_id, progress_callback, cancel_check):  # noqa: ARG002
            base = datetime(2024, 1, 1, tzinfo=UTC)
            for index in range(1, 1001):
                progress_callback(index, 1000, _bar(base + timedelta(minutes=index)))
            return BacktestResult(
                final_portfolio=PortfolioBook(cash=Decimal("10000")),
                equity_timestamps=[],
                equity_curve=[],
                processed_bars=1000,
                executed_trades=0,
                rejected_signals=0,
                signal_events=[],
                orders=[],
                risk_rejections=[],
            )

    monkeypatch.setattr(repo, "update_progress", _update_progress_spy)
    monkeypatch.setattr(
        backtest_routes,
        "build_services",
        lambda *_args, **_kwargs: FakeServices(),
    )

    final_run = backtest_routes.execute_backtest_job(claimed, "test-worker", 30)
    job = repo.get_job("run-1")

    assert final_run.status == "succeeded"
    assert job is not None
    assert job.progress.percent == 100.0
    assert progress_writes < 200


def test_backtest_worker_shutdown_exits_without_claiming_again(monkeypatch) -> None:
    handlers = {}

    def _signal_spy(sig, handler):
        handlers[sig] = handler

    class EmptyRepository:
        claim_count = 0

        def claim_next(self, *, worker_id, lease_seconds):  # noqa: ARG002
            self.claim_count += 1
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            return None

    repo = EmptyRepository()
    monkeypatch.setattr(backtest_worker.signal, "signal", _signal_spy)
    monkeypatch.setattr(backtest_routes, "_JOB_REPOSITORY", repo)

    exit_code = backtest_worker.run(["--worker-id", "test-worker", "--poll-interval", "30"])

    assert exit_code == 0
    assert repo.claim_count == 1
    assert signal.SIGINT in handlers
    assert signal.SIGTERM in handlers


def _bar(timestamp: datetime) -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("100"),
        close=Decimal("100"),
        volume=Decimal("1"),
    )
