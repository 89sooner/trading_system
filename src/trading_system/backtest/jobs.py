from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from trading_system.core.compat import UTC

BACKTEST_JOB_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


@dataclass(slots=True, frozen=True)
class BacktestJobProgress:
    processed_bars: int = 0
    total_bars: int = 0
    percent: float = 0.0
    last_bar_timestamp: str | None = None
    updated_at: str | None = None


@dataclass(slots=True, frozen=True)
class BacktestJobRecord:
    run_id: str
    status: str
    payload: dict
    created_at: str
    available_at: str
    attempt_count: int = 0
    max_attempts: int = 3
    worker_id: str | None = None
    lease_expires_at: str | None = None
    last_heartbeat_at: str | None = None
    progress: BacktestJobProgress = field(default_factory=BacktestJobProgress)
    cancel_requested: bool = False
    error: str | None = None

    @classmethod
    def queued(
        cls,
        *,
        run_id: str,
        payload: dict,
        created_at: datetime | str | None = None,
        max_attempts: int = 3,
    ) -> "BacktestJobRecord":
        timestamp = _timestamp_to_json(created_at or datetime.now(UTC))
        return cls(
            run_id=run_id,
            status="queued",
            payload=payload,
            created_at=timestamp,
            available_at=timestamp,
            max_attempts=max_attempts,
        )


@dataclass(slots=True, frozen=True)
class BacktestJobSnapshot:
    queued_count: int
    running_count: int
    stale_count: int
    cancelled_count: int
    oldest_queued_age_seconds: float | None


class BacktestJobRepository(Protocol):
    def enqueue(self, job: BacktestJobRecord) -> None:
        ...

    def get_job(self, run_id: str) -> BacktestJobRecord | None:
        ...

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> BacktestJobRecord | None:
        ...

    def heartbeat(
        self,
        run_id: str,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> BacktestJobRecord | None:
        ...

    def update_progress(
        self,
        run_id: str,
        progress: BacktestJobProgress,
        *,
        worker_id: str | None = None,
    ) -> BacktestJobRecord | None:
        ...

    def request_cancel(self, run_id: str) -> BacktestJobRecord | None:
        ...

    def complete(self, run_id: str) -> BacktestJobRecord | None:
        ...

    def fail(self, run_id: str, error: str) -> BacktestJobRecord | None:
        ...

    def cancel(self, run_id: str, reason: str | None = None) -> BacktestJobRecord | None:
        ...

    def snapshot(self, *, now: datetime | None = None) -> BacktestJobSnapshot:
        ...

    def clear_jobs(self) -> None:
        ...


def is_terminal_job_status(status: str) -> bool:
    return status in BACKTEST_JOB_TERMINAL_STATUSES


def mark_job_running(
    job: BacktestJobRecord,
    *,
    worker_id: str,
    lease_seconds: int,
    now: datetime | None = None,
) -> BacktestJobRecord:
    current = now or datetime.now(UTC)
    return _replace_job(
        job,
        status="running",
        worker_id=worker_id,
        attempt_count=job.attempt_count + 1,
        lease_expires_at=_timestamp_to_json(current + timedelta(seconds=lease_seconds)),
        last_heartbeat_at=_timestamp_to_json(current),
        error=None,
    )


def job_is_claimable(job: BacktestJobRecord, *, now: datetime | None = None) -> bool:
    if job.cancel_requested or is_terminal_job_status(job.status):
        return False
    current = now or datetime.now(UTC)
    if _parse_timestamp(job.available_at) > current:
        return False
    if job.status == "queued":
        return job.attempt_count < job.max_attempts
    if job.status != "running":
        return False
    if job.lease_expires_at is None:
        return job.attempt_count < job.max_attempts
    return (
        _parse_timestamp(job.lease_expires_at) <= current
        and job.attempt_count < job.max_attempts
    )


def job_is_stale(job: BacktestJobRecord, *, now: datetime | None = None) -> bool:
    if job.status != "running" or job.lease_expires_at is None:
        return False
    current = now or datetime.now(UTC)
    return _parse_timestamp(job.lease_expires_at) <= current


def serialize_job(job: BacktestJobRecord) -> dict:
    return {
        "run_id": job.run_id,
        "status": job.status,
        "payload": job.payload,
        "created_at": job.created_at,
        "available_at": job.available_at,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "worker_id": job.worker_id,
        "lease_expires_at": job.lease_expires_at,
        "last_heartbeat_at": job.last_heartbeat_at,
        "progress": {
            "processed_bars": job.progress.processed_bars,
            "total_bars": job.progress.total_bars,
            "percent": job.progress.percent,
            "last_bar_timestamp": job.progress.last_bar_timestamp,
            "updated_at": job.progress.updated_at,
        },
        "cancel_requested": job.cancel_requested,
        "error": job.error,
    }


def deserialize_job(data: dict) -> BacktestJobRecord:
    progress_raw = data.get("progress") or {}
    return BacktestJobRecord(
        run_id=data["run_id"],
        status=data["status"],
        payload=dict(data.get("payload") or {}),
        created_at=data["created_at"],
        available_at=data.get("available_at") or data["created_at"],
        attempt_count=int(data.get("attempt_count") or 0),
        max_attempts=int(data.get("max_attempts") or 3),
        worker_id=data.get("worker_id"),
        lease_expires_at=data.get("lease_expires_at"),
        last_heartbeat_at=data.get("last_heartbeat_at"),
        progress=BacktestJobProgress(
            processed_bars=int(progress_raw.get("processed_bars") or 0),
            total_bars=int(progress_raw.get("total_bars") or 0),
            percent=float(progress_raw.get("percent") or 0.0),
            last_bar_timestamp=progress_raw.get("last_bar_timestamp"),
            updated_at=progress_raw.get("updated_at"),
        ),
        cancel_requested=bool(data.get("cancel_requested", False)),
        error=data.get("error"),
    )


def _replace_job(job: BacktestJobRecord, **changes: object) -> BacktestJobRecord:
    values = serialize_job(job)
    values.update(changes)
    return deserialize_job(values)


def _timestamp_to_json(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return value


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
