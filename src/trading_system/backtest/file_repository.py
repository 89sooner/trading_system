from __future__ import annotations

import dataclasses
import json
import os
import threading
import uuid
from pathlib import Path

from trading_system.backtest.dto import (
    BacktestResultDTO,
    BacktestRunDTO,
    DrawdownPointDTO,
    EquityPointDTO,
    EventDTO,
    SummaryDTO,
)


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

    def _run_path(self, run_id: str) -> Path:
        return self._base_dir / f"{run_id}.json"

    def _ensure_index(self) -> None:
        if not self._index_path().exists():
            self._write_index({"runs": []})

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

    def _index_entry(self, run: BacktestRunDTO) -> dict:
        return {
            "run_id": run.run_id,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "input_symbols": run.input_symbols,
            "mode": run.mode,
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
                finished_at=r.get("finished_at", ""),
                input_symbols=r.get("input_symbols", []),
                mode=r.get("mode", ""),
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
                if p.name != "_index.json":
                    p.unlink()
            # Also clean up any stray .tmp files.
            for p in self._base_dir.glob("*.tmp"):
                p.unlink(missing_ok=True)
            self._write_index({"runs": []})

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
                        "finished_at": data.get("finished_at", ""),
                        "input_symbols": data.get("input_symbols", []),
                        "mode": data.get("mode", ""),
                    })
                except Exception:
                    continue
            self._write_index({"runs": entries})


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
        finished_at=data.get("finished_at", ""),
        input_symbols=data.get("input_symbols", []),
        mode=data.get("mode", ""),
        result=result,
        error=data.get("error"),
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
