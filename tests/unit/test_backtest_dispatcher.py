from __future__ import annotations

import threading
import time
from decimal import Decimal

from trading_system.app.settings import (
    AppMode,
    AppSettings,
    BacktestSettings,
    LiveExecutionMode,
    RiskSettings,
)
from trading_system.backtest.dispatcher import BacktestRunDispatcher, QueuedBacktestRun
from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.repository import InMemoryBacktestRunRepository


def _make_settings() -> AppSettings:
    return AppSettings(
        mode=AppMode.BACKTEST,
        symbols=("BTCUSDT",),
        provider="mock",
        broker="paper",
        live_execution=LiveExecutionMode.PREFLIGHT,
        risk=RiskSettings(
            max_position=Decimal("1"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("0.25"),
        ),
        backtest=BacktestSettings(
            starting_cash=Decimal("10000"),
            fee_bps=Decimal("5"),
            trade_quantity=Decimal("0.1"),
        ),
    )


def test_dispatcher_processes_queued_run_to_terminal_state() -> None:
    repo = InMemoryBacktestRunRepository()

    def _executor(item: QueuedBacktestRun) -> BacktestRunDTO:
        return BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=item.input_symbols,
            mode=item.mode,
            error="forced",
        )

    dispatcher = BacktestRunDispatcher(repo_factory=lambda: repo, executor=_executor)
    dispatcher.start()
    repo.save(
        BacktestRunDTO.queued(
            run_id="run-1",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    dispatcher.submit(
        QueuedBacktestRun(
            run_id="run-1",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=("BTCUSDT",),
            mode="backtest",
            payload=_make_settings(),
        )
    )

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        run = repo.get("run-1")
        if run is not None and run.status == "failed":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Dispatcher did not finish queued run")

    assert run is not None
    assert run.error == "forced"
    dispatcher.shutdown()


def test_dispatcher_recovery_marks_pending_runs_failed() -> None:
    repo = InMemoryBacktestRunRepository()
    repo.save(
        BacktestRunDTO.running(
            run_id="running-run",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    dispatcher = BacktestRunDispatcher(
        repo_factory=lambda: repo,
        executor=lambda item: BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=item.input_symbols,
            mode=item.mode,
            error="unused",
        ),
    )

    dispatcher.recover_interrupted_runs()

    recovered = repo.get("running-run")
    assert recovered is not None
    assert recovered.status == "failed"
    assert recovered.error == "Backtest interrupted by previous server lifecycle."


def test_dispatcher_recovery_marks_all_pending_runs_across_multiple_pages_failed() -> None:
    repo = InMemoryBacktestRunRepository()
    for index in range(150):
        repo.save(
            BacktestRunDTO.queued(
                run_id=f"queued-{index}",
                started_at="2024-01-01T00:00:00Z",
                input_symbols=["BTCUSDT"],
                mode="backtest",
            )
        )
    for index in range(150):
        repo.save(
            BacktestRunDTO.running(
                run_id=f"running-{index}",
                started_at="2024-01-01T00:00:00Z",
                input_symbols=["BTCUSDT"],
                mode="backtest",
            )
        )

    dispatcher = BacktestRunDispatcher(
        repo_factory=lambda: repo,
        executor=lambda item: BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=item.input_symbols,
            mode=item.mode,
            error="unused",
        ),
    )

    dispatcher.recover_interrupted_runs()

    _queued_runs, queued_total = repo.list(status="queued", page_size=500)
    _running_runs, running_total = repo.list(status="running", page_size=500)
    failed_runs, failed_total = repo.list(status="failed", page_size=500)

    assert queued_total == 0
    assert running_total == 0
    assert failed_total == 300
    assert all(
        run.error == "Backtest interrupted by previous server lifecycle."
        for run in failed_runs
    )


def test_dispatcher_survives_running_state_persist_failure() -> None:
    class RunningSaveFailureRepo(InMemoryBacktestRunRepository):
        def __init__(self) -> None:
            super().__init__()
            self._failed_once = False

        def save(self, run: BacktestRunDTO) -> None:
            if run.run_id == "run-1" and run.status == "running" and not self._failed_once:
                self._failed_once = True
                raise RuntimeError("boom on running save")
            super().save(run)

    repo = RunningSaveFailureRepo()
    dispatcher = BacktestRunDispatcher(
        repo_factory=lambda: repo,
        executor=lambda item: BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=item.input_symbols,
            mode=item.mode,
            error=f"done-{item.run_id}",
        ),
    )
    dispatcher.start()
    repo.save(
        BacktestRunDTO.queued(
            run_id="run-1",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    repo.save(
        BacktestRunDTO.queued(
            run_id="run-2",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    dispatcher.submit(
        QueuedBacktestRun(
            run_id="run-1",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=("BTCUSDT",),
            mode="backtest",
            payload=_make_settings(),
        )
    )
    dispatcher.submit(
        QueuedBacktestRun(
            run_id="run-2",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=("BTCUSDT",),
            mode="backtest",
            payload=_make_settings(),
        )
    )

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        run_1 = repo.get("run-1")
        run_2 = repo.get("run-2")
        if (
            run_1 is not None
            and run_1.status == "failed"
            and run_2 is not None
            and run_2.status == "failed"
        ):
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Dispatcher did not recover from running-save failure")

    assert dispatcher.is_running() is True
    assert run_1 is not None
    assert run_1.error == "boom on running save"
    assert run_2 is not None
    assert run_2.error == "done-run-2"
    dispatcher.shutdown()


def test_dispatcher_survives_executor_exception_and_marks_run_failed() -> None:
    repo = InMemoryBacktestRunRepository()

    def _executor(item: QueuedBacktestRun) -> BacktestRunDTO:
        if item.run_id == "run-1":
            raise RuntimeError("executor blew up")
        return BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=item.input_symbols,
            mode=item.mode,
            error=f"done-{item.run_id}",
        )

    dispatcher = BacktestRunDispatcher(repo_factory=lambda: repo, executor=_executor)
    dispatcher.start()
    for run_id in ("run-1", "run-2"):
        repo.save(
            BacktestRunDTO.queued(
                run_id=run_id,
                started_at="2024-01-01T00:00:00Z",
                input_symbols=["BTCUSDT"],
                mode="backtest",
            )
        )
        dispatcher.submit(
            QueuedBacktestRun(
                run_id=run_id,
                started_at="2024-01-01T00:00:00Z",
                input_symbols=("BTCUSDT",),
                mode="backtest",
                payload=_make_settings(),
            )
        )

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        run_1 = repo.get("run-1")
        run_2 = repo.get("run-2")
        if (
            run_1 is not None
            and run_1.status == "failed"
            and run_2 is not None
            and run_2.status == "failed"
        ):
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Dispatcher did not recover from executor exception")

    assert dispatcher.is_running() is True
    assert run_1 is not None
    assert run_1.error == "executor blew up"
    assert run_2 is not None
    assert run_2.error == "done-run-2"
    dispatcher.shutdown()


def test_dispatcher_shutdown_stops_cleanly_when_queue_is_full() -> None:
    repo = InMemoryBacktestRunRepository()
    unblock = threading.Event()

    def _executor(item: QueuedBacktestRun) -> BacktestRunDTO:
        if item.run_id == "run-1":
            unblock.wait(timeout=1.0)
        return BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=item.input_symbols,
            mode=item.mode,
            error=f"done-{item.run_id}",
        )

    dispatcher = BacktestRunDispatcher(
        repo_factory=lambda: repo,
        executor=_executor,
        max_queue_size=1,
    )
    dispatcher.start()
    repo.save(
        BacktestRunDTO.queued(
            run_id="run-1",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    dispatcher.submit(
        QueuedBacktestRun(
            run_id="run-1",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=("BTCUSDT",),
            mode="backtest",
            payload=_make_settings(),
        )
    )

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        run_1 = repo.get("run-1")
        if run_1 is not None and run_1.status == "running":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("run-1 did not enter running state")

    repo.save(
        BacktestRunDTO.queued(
            run_id="run-2",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    dispatcher.submit(
        QueuedBacktestRun(
            run_id="run-2",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=("BTCUSDT",),
            mode="backtest",
            payload=_make_settings(),
        )
    )

    shutdown_thread = threading.Thread(target=dispatcher.shutdown, kwargs={"timeout": 1.0})
    shutdown_thread.start()
    time.sleep(0.1)
    unblock.set()
    shutdown_thread.join(timeout=1.5)

    assert shutdown_thread.is_alive() is False
    assert dispatcher.is_running() is False
    run_1 = repo.get("run-1")
    run_2 = repo.get("run-2")
    assert run_1 is not None
    assert run_1.status == "failed"
    assert run_2 is not None
    assert run_2.status == "queued"
