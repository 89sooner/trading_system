from __future__ import annotations

from datetime import datetime, timedelta

from trading_system.backtest.file_repository import FileBacktestRunRepository
from trading_system.backtest.jobs import BacktestJobProgress, BacktestJobRecord
from trading_system.core.compat import UTC


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


def test_file_job_repository_claims_one_worker_at_a_time(tmp_path) -> None:
    repo = FileBacktestRunRepository(tmp_path)
    repo.enqueue(
        BacktestJobRecord.queued(
            run_id="run-1",
            payload=_payload(),
            created_at="2024-01-01T00:00:00Z",
        )
    )

    claimed = repo.claim_next(
        worker_id="worker-a",
        lease_seconds=30,
        now=datetime(2024, 1, 1, tzinfo=UTC),
    )
    second_claim = repo.claim_next(
        worker_id="worker-b",
        lease_seconds=30,
        now=datetime(2024, 1, 1, tzinfo=UTC),
    )

    assert claimed is not None
    assert claimed.worker_id == "worker-a"
    assert claimed.status == "running"
    assert second_claim is None


def test_file_job_repository_reclaims_expired_lease(tmp_path) -> None:
    repo = FileBacktestRunRepository(tmp_path)
    repo.enqueue(
        BacktestJobRecord.queued(
            run_id="run-1",
            payload=_payload(),
            created_at="2024-01-01T00:00:00Z",
        )
    )
    started = datetime(2024, 1, 1, tzinfo=UTC)
    first = repo.claim_next(worker_id="worker-a", lease_seconds=5, now=started)

    reclaimed = repo.claim_next(
        worker_id="worker-b",
        lease_seconds=5,
        now=started + timedelta(seconds=6),
    )

    assert first is not None
    assert reclaimed is not None
    assert reclaimed.worker_id == "worker-b"
    assert reclaimed.attempt_count == 2


def test_file_job_repository_tracks_progress_and_cancel(tmp_path) -> None:
    repo = FileBacktestRunRepository(tmp_path)
    repo.enqueue(BacktestJobRecord.queued(run_id="run-1", payload=_payload()))
    claimed = repo.claim_next(worker_id="worker-a", lease_seconds=30)
    assert claimed is not None

    progress = BacktestJobProgress(
        processed_bars=5,
        total_bars=10,
        percent=50.0,
        last_bar_timestamp="2024-01-01T00:05:00Z",
        updated_at="2024-01-01T00:00:01Z",
    )
    updated = repo.update_progress("run-1", progress, worker_id="worker-a")
    cancelled = repo.request_cancel("run-1")

    assert updated is not None
    assert updated.progress.percent == 50.0
    assert cancelled is not None
    assert cancelled.cancel_requested is True


def test_file_job_snapshot_counts_stale_and_oldest_queued(tmp_path) -> None:
    repo = FileBacktestRunRepository(tmp_path)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo.enqueue(
        BacktestJobRecord.queued(
            run_id="queued",
            payload=_payload(),
            created_at=base,
        )
    )
    repo.enqueue(
        BacktestJobRecord.queued(
            run_id="running",
            payload=_payload(),
            created_at=base,
        )
    )
    repo.claim_next(worker_id="worker-a", lease_seconds=5, now=base)

    snapshot = repo.snapshot(now=base + timedelta(seconds=10))

    assert snapshot.queued_count == 1
    assert snapshot.running_count == 1
    assert snapshot.stale_count == 1
    assert snapshot.oldest_queued_age_seconds == 10.0
