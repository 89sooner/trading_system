from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from trading_system.backtest.dto import BacktestRunDTO, BacktestRunMetadataDTO
from trading_system.backtest.jobs import BacktestJobRecord, BacktestJobRepository
from trading_system.backtest.repository import BacktestRunRepository
from trading_system.core.compat import UTC

_INTERRUPTED_RUN_ERROR = "Backtest interrupted by previous server lifecycle."
_STOP = object()
_log = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class QueuedBacktestRun:
    run_id: str
    started_at: str
    input_symbols: tuple[str, ...]
    mode: str
    payload: object
    metadata: object | None = None


@dataclass(slots=True, frozen=True)
class BacktestDispatcherSnapshot:
    running: bool
    queue_depth: int
    max_queue_size: int
    durable_queued_count: int = 0
    durable_running_count: int = 0
    durable_stale_count: int = 0
    oldest_queued_age_seconds: float | None = None


class BacktestRunDispatcher:
    def __init__(
        self,
        *,
        repo_factory: Callable[[], BacktestRunRepository],
        executor: Callable[[QueuedBacktestRun], BacktestRunDTO],
        job_repo_factory: Callable[[], BacktestJobRepository] | None = None,
        job_executor: Callable[[BacktestJobRecord, str, int], BacktestRunDTO] | None = None,
        max_queue_size: int = 32,
        worker_id: str = "api-dispatcher",
        lease_seconds: int = 30,
        poll_interval: float = 0.1,
    ) -> None:
        self._repo_factory = repo_factory
        self._executor = executor
        self._job_repo_factory = job_repo_factory
        self._job_executor = job_executor
        self._queue: queue.Queue[QueuedBacktestRun | object] = queue.Queue(maxsize=max_queue_size)
        self._max_queue_size = max_queue_size
        self._worker: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._poll_interval = poll_interval

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_requested.clear()
        self._worker = threading.Thread(
            target=self._run_worker,
            name="backtest-run-dispatcher",
            daemon=True,
        )
        self._worker.start()

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def snapshot(self) -> BacktestDispatcherSnapshot:
        if self._job_repo_factory is not None:
            job_snapshot = self._job_repo_factory().snapshot()
            return BacktestDispatcherSnapshot(
                running=self.is_running(),
                queue_depth=job_snapshot.queued_count,
                max_queue_size=self._max_queue_size,
                durable_queued_count=job_snapshot.queued_count,
                durable_running_count=job_snapshot.running_count,
                durable_stale_count=job_snapshot.stale_count,
                oldest_queued_age_seconds=job_snapshot.oldest_queued_age_seconds,
            )
        return BacktestDispatcherSnapshot(
            running=self.is_running(),
            queue_depth=self._queue.qsize(),
            max_queue_size=self._max_queue_size,
        )

    def submit(self, item: QueuedBacktestRun) -> None:
        if self._worker is None or not self._worker.is_alive():
            raise RuntimeError("Backtest dispatcher is not running.")
        if self._job_repo_factory is not None:
            return
        try:
            self._queue.put_nowait(item)
        except queue.Full as exc:
            raise RuntimeError("Backtest queue is full. Retry later.") from exc

    def shutdown(self, timeout: float = 5.0) -> None:
        if self._worker is None:
            return
        self._stop_requested.set()
        try:
            self._queue.put_nowait(_STOP)
        except queue.Full:
            pass
        self._worker.join(timeout=timeout)
        if self._worker.is_alive():
            _log.warning("Backtest dispatcher did not stop within %.2fs", timeout)
            return
        self._worker = None

    def recover_interrupted_runs(self) -> None:
        if self._job_repo_factory is not None:
            return
        repo = self._repo_factory()
        for pending_status in ("queued", "running"):
            while True:
                runs, _total = repo.list(page=1, page_size=100, status=pending_status)
                if not runs:
                    break
                for run in runs:
                    repo.save(
                        BacktestRunDTO.failed(
                            run_id=run.run_id,
                            started_at=run.started_at,
                            finished_at=datetime.now(UTC),
                            input_symbols=run.input_symbols,
                            mode=run.mode,
                            error=_INTERRUPTED_RUN_ERROR,
                        )
                    )

    def _run_worker(self) -> None:
        if self._job_repo_factory is not None and self._job_executor is not None:
            self._run_durable_worker()
            return
        while True:
            if self._stop_requested.is_set():
                break
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is _STOP:
                break
            assert isinstance(item, QueuedBacktestRun)
            try:
                repo = self._repo_factory()
                repo.save(
                    BacktestRunDTO.running(
                        run_id=item.run_id,
                        started_at=item.started_at,
                        input_symbols=item.input_symbols,
                        mode=item.mode,
                        metadata=(
                            item.metadata
                            if isinstance(item.metadata, BacktestRunMetadataDTO)
                            else None
                        ),
                    )
                )
                final_run = self._executor(item)
                repo.save(final_run)
            except Exception as exc:
                _log.exception("Backtest worker failed for run %s", item.run_id)
                self._persist_failed_run(item, str(exc))

    def _persist_failed_run(self, item: QueuedBacktestRun, error: str) -> None:
        try:
            self._repo_factory().save(
                BacktestRunDTO.failed(
                    run_id=item.run_id,
                    started_at=item.started_at,
                    finished_at=datetime.now(UTC),
                    input_symbols=item.input_symbols,
                    mode=item.mode,
                    error=error,
                )
            )
        except Exception:
            _log.exception("Failed to persist terminal failure for run %s", item.run_id)

    def _run_durable_worker(self) -> None:
        assert self._job_repo_factory is not None
        assert self._job_executor is not None
        while not self._stop_requested.is_set():
            job_repo = self._job_repo_factory()
            job = job_repo.claim_next(
                worker_id=self._worker_id,
                lease_seconds=self._lease_seconds,
            )
            if job is None:
                time.sleep(self._poll_interval)
                continue
            try:
                self._job_executor(job, self._worker_id, self._lease_seconds)
            except Exception as exc:
                _log.exception("Backtest durable worker failed for run %s", job.run_id)
                try:
                    self._job_repo_factory().fail(job.run_id, str(exc))
                except Exception:
                    _log.exception("Failed to mark durable job %s failed", job.run_id)
