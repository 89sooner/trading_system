from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _configure_import_path() -> None:
    src_path = str(_repo_root() / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


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


def _enqueue_job(runs_dir: Path, run_id: str) -> None:
    _configure_import_path()
    from trading_system.backtest.dto import BacktestRunDTO
    from trading_system.backtest.file_repository import FileBacktestRunRepository
    from trading_system.backtest.jobs import BacktestJobRecord
    from trading_system.core.compat import UTC

    repo = FileBacktestRunRepository(runs_dir)
    started_at = datetime.now(UTC)
    repo.save(
        BacktestRunDTO.queued(
            run_id=run_id,
            started_at=started_at,
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    repo.enqueue(
        BacktestJobRecord.queued(
            run_id=run_id,
            payload=_payload(),
            created_at=started_at,
        )
    )


def _verify_job(runs_dir: Path, run_id: str) -> None:
    _configure_import_path()
    from trading_system.backtest.file_repository import FileBacktestRunRepository

    repo = FileBacktestRunRepository(runs_dir)
    run = repo.get(run_id)
    job = repo.get_job(run_id)
    if run is None:
        raise RuntimeError(f"Backtest run {run_id} was not persisted.")
    if job is None:
        raise RuntimeError(f"Backtest job {run_id} was not persisted.")
    if run.status != "succeeded":
        raise RuntimeError(f"Expected run status succeeded, got {run.status}.")
    if job.status != "succeeded":
        raise RuntimeError(f"Expected job status succeeded, got {job.status}.")
    if job.progress.percent != 100.0:
        raise RuntimeError(f"Expected job progress 100.0, got {job.progress.percent}.")


def _worker_env(runs_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = ""
    env["TRADING_SYSTEM_RUNS_DIR"] = str(runs_dir)
    env["TRADING_SYSTEM_ORDER_AUDIT_DIR"] = str(runs_dir / "order_audit")
    src_path = str(_repo_root() / "src")
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_path if not current_pythonpath else f"{src_path}{os.pathsep}{current_pythonpath}"
    )
    return env


def run_smoke(runs_dir: Path, *, keep_artifacts: bool = False) -> Path:
    run_id = "worker-smoke-run"
    _enqueue_job(runs_dir, run_id)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_system.app.backtest_worker",
            "--worker-id",
            "smoke-worker",
            "--once",
            "--lease-seconds",
            "30",
        ],
        cwd=_repo_root(),
        env=_worker_env(runs_dir),
        check=True,
    )
    _verify_job(runs_dir, run_id)
    if keep_artifacts:
        return runs_dir
    return runs_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke test the durable backtest worker.")
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Optional runs directory. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep the temporary runs directory and print its path.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.runs_dir is not None:
        args.runs_dir.mkdir(parents=True, exist_ok=True)
        result_dir = run_smoke(args.runs_dir, keep_artifacts=True)
        print(f"worker smoke passed: {result_dir}")
        return

    if args.keep_artifacts:
        result_dir = run_smoke(
            Path(tempfile.mkdtemp(prefix="trading-system-worker-smoke-")),
            keep_artifacts=True,
        )
        print(f"worker smoke passed: {result_dir}")
        return

    with tempfile.TemporaryDirectory(prefix="trading-system-worker-smoke-") as temp_dir:
        run_smoke(Path(temp_dir))
        print("worker smoke passed")


if __name__ == "__main__":
    main()
