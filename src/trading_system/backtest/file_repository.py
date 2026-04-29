from __future__ import annotations

import dataclasses
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from trading_system.backtest.dto import (
    BacktestResultDTO,
    BacktestRunDTO,
    BacktestRunMetadataDTO,
    DrawdownPointDTO,
    EquityPointDTO,
    EventDTO,
    SummaryDTO,
)
from trading_system.backtest.jobs import (
    BacktestJobProgress,
    BacktestJobRecord,
    BacktestJobSnapshot,
    deserialize_job,
    job_is_claimable,
    job_is_stale,
    mark_job_running,
    serialize_job,
)
from trading_system.core.compat import UTC


class FileBacktestRunRepository:
    def __init__(self, base_dir: Path | str = "data/runs") -> None:
        self._base_dir = Path(base_dir)
        self._lock = threading.Lock()
        os.makedirs(self._base_dir, exist_ok=True)
        self._ensure_index()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _index_path(self) -> Path:
        return self._base_dir / "_index.json"

    def _jobs_index_path(self) -> Path:
        return self._base_dir / "_jobs_index.json"

    def _run_path(self, run_id: str) -> Path:
        return self._base_dir / f"{run_id}.json"

    def _ensure_index(self) -> None:
        if not self._index_path().exists():
            self._write_index({"runs": []})
        if not self._jobs_index_path().exists():
            self._write_jobs_index({"jobs": []})

    def _read_index(self) -> dict:
        try:
            return json.loads(self._index_path().read_text())
        except Exception:
            return {"runs": []}

    def _write_index(self, data: dict) -> None:
        """Write index atomically using a unique temp file."""
        tmp = self._base_dir / f"_index_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(data, default=str))
            os.replace(tmp, self._index_path())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _read_jobs_index(self) -> dict:
        try:
            return json.loads(self._jobs_index_path().read_text())
        except Exception:
            return {"jobs": []}

    def _write_jobs_index(self, data: dict) -> None:
        tmp = self._base_dir / f"_jobs_index_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(data, default=str))
            os.replace(tmp, self._jobs_index_path())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _index_entry(self, run: BacktestRunDTO) -> dict:
        return {
            "run_id": run.run_id,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "input_symbols": run.input_symbols,
            "mode": run.mode,
            "metadata": dataclasses.asdict(run.metadata) if run.metadata is not None else None,
        }

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    def save(self, run: BacktestRunDTO) -> None:
        # Write the per-run file first (unique path, no lock needed).
        data = dataclasses.asdict(run)
        run_path = self._run_path(run.run_id)
        tmp = self._base_dir / f"{run.run_id}_{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(json.dumps(data, default=str))
            os.replace(tmp, run_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

        # Update shared index under lock.
        entry = self._index_entry(run)
        with self._lock:
            index = self._read_index()
            existing_ids = {r["run_id"] for r in index["runs"]}
            if run.run_id in existing_ids:
                index["runs"] = [
                    entry if r["run_id"] == run.run_id else r for r in index["runs"]
                ]
            else:
                index["runs"].append(entry)
            self._write_index(index)

    def get(self, run_id: str) -> BacktestRunDTO | None:
        path = self._run_path(run_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return _deserialize_run(data)

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        mode: str | None = None,
    ) -> tuple[list[BacktestRunDTO], int]:
        with self._lock:
            index = self._read_index()
        runs = index.get("runs", [])
        if status is not None:
            runs = [r for r in runs if r.get("status") == status]
        if mode is not None:
            runs = [r for r in runs if r.get("mode") == mode]
        runs = sorted(runs, key=lambda r: r.get("started_at", ""), reverse=True)
        total = len(runs)
        start = (page - 1) * page_size
        page_runs = runs[start : start + page_size]
        dtos = [
            BacktestRunDTO(
                run_id=r["run_id"],
                status=r["status"],
                started_at=r["started_at"],
                finished_at=r.get("finished_at"),
                input_symbols=r.get("input_symbols", []),
                mode=r.get("mode", ""),
                metadata=_deserialize_metadata(r.get("metadata")),
            )
            for r in page_runs
        ]
        return dtos, total

    def delete(self, run_id: str) -> bool:
        with self._lock:
            path = self._run_path(run_id)
            if not path.exists():
                return False
            path.unlink()
            index = self._read_index()
            index["runs"] = [r for r in index["runs"] if r["run_id"] != run_id]
            self._write_index(index)
            return True

    def clear(self) -> None:
        with self._lock:
            for p in self._base_dir.glob("*.json"):
                if p.name not in {"_index.json", "_jobs_index.json"}:
                    p.unlink()
            # Also clean up any stray .tmp files.
            for p in self._base_dir.glob("*.tmp"):
                p.unlink(missing_ok=True)
            self._write_index({"runs": []})
            self._jobs_index_path().unlink(missing_ok=True)

    def rebuild_index(self) -> None:
        with self._lock:
            entries = []
            for p in self._base_dir.glob("*.json"):
                if p.name == "_index.json":
                    continue
                try:
                    data = json.loads(p.read_text())
                    entries.append({
                        "run_id": data["run_id"],
                        "status": data["status"],
                        "started_at": data.get("started_at", ""),
                        "finished_at": data.get("finished_at"),
                        "input_symbols": data.get("input_symbols", []),
                        "mode": data.get("mode", ""),
                        "metadata": data.get("metadata"),
                    })
                except Exception:
                    continue
            self._write_index({"runs": entries})

    # ------------------------------------------------------------------
    # Backtest job repository implementation
    # ------------------------------------------------------------------

    def enqueue(self, job: BacktestJobRecord) -> None:
        with self._lock:
            index = self._read_jobs_index()
            jobs = [
                serialize_job(job) if row.get("run_id") == job.run_id else row
                for row in index.get("jobs", [])
            ]
            if not any(row.get("run_id") == job.run_id for row in jobs):
                jobs.append(serialize_job(job))
            self._write_jobs_index({"jobs": jobs})

    def get_job(self, run_id: str) -> BacktestJobRecord | None:
        with self._lock:
            index = self._read_jobs_index()
        for row in index.get("jobs", []):
            if row.get("run_id") == run_id:
                return deserialize_job(row)
        return None

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> BacktestJobRecord | None:
        current = now or datetime.now(UTC)
        with self._lock:
            index = self._read_jobs_index()
            jobs = [deserialize_job(row) for row in index.get("jobs", [])]
            claimable = [job for job in jobs if job_is_claimable(job, now=current)]
            if not claimable:
                return None
            job = sorted(claimable, key=lambda item: (item.available_at, item.created_at))[0]
            running = mark_job_running(
                job,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
                now=current,
            )
            jobs = [running if item.run_id == job.run_id else item for item in jobs]
            self._write_jobs_index({"jobs": [serialize_job(item) for item in jobs]})
            return running

    def heartbeat(
        self,
        run_id: str,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> BacktestJobRecord | None:
        current = now or datetime.now(UTC)
        with self._lock:
            jobs = [deserialize_job(row) for row in self._read_jobs_index().get("jobs", [])]
            updated: BacktestJobRecord | None = None
            for index, job in enumerate(jobs):
                if job.run_id != run_id or job.worker_id != worker_id:
                    continue
                updated = mark_job_running(
                    dataclasses.replace(job, attempt_count=max(job.attempt_count - 1, 0)),
                    worker_id=worker_id,
                    lease_seconds=lease_seconds,
                    now=current,
                )
                updated = dataclasses.replace(updated, attempt_count=job.attempt_count)
                jobs[index] = updated
                break
            if updated is None:
                return None
            self._write_jobs_index({"jobs": [serialize_job(item) for item in jobs]})
            return updated

    def update_progress(
        self,
        run_id: str,
        progress: BacktestJobProgress,
        *,
        worker_id: str | None = None,
    ) -> BacktestJobRecord | None:
        with self._lock:
            jobs = [deserialize_job(row) for row in self._read_jobs_index().get("jobs", [])]
            updated: BacktestJobRecord | None = None
            for index, job in enumerate(jobs):
                if job.run_id != run_id:
                    continue
                if worker_id is not None and job.worker_id != worker_id:
                    return None
                updated = dataclasses.replace(job, progress=progress)
                jobs[index] = updated
                break
            if updated is None:
                return None
            self._write_jobs_index({"jobs": [serialize_job(item) for item in jobs]})
            return updated

    def request_cancel(self, run_id: str) -> BacktestJobRecord | None:
        with self._lock:
            jobs = [deserialize_job(row) for row in self._read_jobs_index().get("jobs", [])]
            updated: BacktestJobRecord | None = None
            for index, job in enumerate(jobs):
                if job.run_id != run_id:
                    continue
                updated = dataclasses.replace(job, cancel_requested=True)
                jobs[index] = updated
                break
            if updated is None:
                return None
            self._write_jobs_index({"jobs": [serialize_job(item) for item in jobs]})
            return updated

    def complete(self, run_id: str) -> BacktestJobRecord | None:
        return self._mark_terminal(run_id, status="succeeded", error=None)

    def fail(self, run_id: str, error: str) -> BacktestJobRecord | None:
        return self._mark_terminal(run_id, status="failed", error=error)

    def cancel(self, run_id: str, reason: str | None = None) -> BacktestJobRecord | None:
        return self._mark_terminal(
            run_id,
            status="cancelled",
            error=reason or "Backtest cancelled.",
        )

    def snapshot(self, *, now: datetime | None = None) -> BacktestJobSnapshot:
        current = now or datetime.now(UTC)
        with self._lock:
            jobs = [deserialize_job(row) for row in self._read_jobs_index().get("jobs", [])]
        queued = [job for job in jobs if job.status == "queued" and not job.cancel_requested]
        running = [job for job in jobs if job.status == "running"]
        stale = [job for job in running if job_is_stale(job, now=current)]
        cancelled = [job for job in jobs if job.cancel_requested and job.status != "cancelled"]
        oldest_age = None
        if queued:
            oldest = min(_parse_timestamp(job.created_at) for job in queued)
            oldest_age = max(0.0, (current - oldest).total_seconds())
        return BacktestJobSnapshot(
            queued_count=len(queued),
            running_count=len(running),
            stale_count=len(stale),
            cancelled_count=len(cancelled),
            oldest_queued_age_seconds=oldest_age,
        )

    def clear_jobs(self) -> None:
        with self._lock:
            self._write_jobs_index({"jobs": []})

    def _mark_terminal(
        self,
        run_id: str,
        *,
        status: str,
        error: str | None,
    ) -> BacktestJobRecord | None:
        with self._lock:
            jobs = [deserialize_job(row) for row in self._read_jobs_index().get("jobs", [])]
            updated: BacktestJobRecord | None = None
            for index, job in enumerate(jobs):
                if job.run_id != run_id:
                    continue
                updated = dataclasses.replace(
                    job,
                    status=status,
                    lease_expires_at=None,
                    cancel_requested=(status == "cancelled" or job.cancel_requested),
                    error=error,
                )
                jobs[index] = updated
                break
            if updated is None:
                return None
            self._write_jobs_index({"jobs": [serialize_job(item) for item in jobs]})
            return updated


# ------------------------------------------------------------------
# Deserialization helpers
# ------------------------------------------------------------------


def _deserialize_run(data: dict) -> BacktestRunDTO:
    result = None
    if data.get("result") is not None:
        result = _deserialize_result(data["result"])
    return BacktestRunDTO(
        run_id=data["run_id"],
        status=data["status"],
        started_at=data["started_at"],
        finished_at=data.get("finished_at"),
        input_symbols=data.get("input_symbols", []),
        mode=data.get("mode", ""),
        metadata=_deserialize_metadata(data.get("metadata")),
        result=result,
        error=data.get("error"),
    )


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _deserialize_metadata(data: dict | None) -> BacktestRunMetadataDTO | None:
    if not isinstance(data, dict):
        return None
    return BacktestRunMetadataDTO(
        provider=data.get("provider"),
        broker=data.get("broker"),
        strategy_profile_id=data.get("strategy_profile_id"),
        pattern_set_id=data.get("pattern_set_id"),
        source=data.get("source"),
        requested_by=data.get("requested_by"),
        notes=data.get("notes"),
    )


def _deserialize_result(data: dict) -> BacktestResultDTO:
    summary_raw = data.get("summary", {})
    summary = SummaryDTO(
        return_value=summary_raw.get("return_value", "0"),
        max_drawdown=summary_raw.get("max_drawdown", "0"),
        volatility=summary_raw.get("volatility", "0"),
        win_rate=summary_raw.get("win_rate", "0"),
    )
    equity_curve = [
        EquityPointDTO(timestamp=p["timestamp"], equity=p["equity"])
        for p in data.get("equity_curve", [])
    ]
    drawdown_curve = [
        DrawdownPointDTO(timestamp=p["timestamp"], drawdown=p["drawdown"])
        for p in data.get("drawdown_curve", [])
    ]
    signals = [
        EventDTO(event=e["event"], payload=e.get("payload", {}))
        for e in data.get("signals", [])
    ]
    orders = [
        EventDTO(event=e["event"], payload=e.get("payload", {}))
        for e in data.get("orders", [])
    ]
    risk_rejections = [
        EventDTO(event=e["event"], payload=e.get("payload", {}))
        for e in data.get("risk_rejections", [])
    ]
    return BacktestResultDTO(
        summary=summary,
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
        signals=signals,
        orders=orders,
        risk_rejections=risk_rejections,
    )
