from __future__ import annotations

import argparse
import signal
import socket
from threading import Event
from uuid import uuid4

from trading_system.api.routes import backtest as backtest_routes
from trading_system.config.env import load_runtime_env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run durable backtest jobs from storage")
    parser.add_argument("--worker-id", default=None, help="Stable worker identifier")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Seconds between polls")
    parser.add_argument("--lease-seconds", type=int, default=30, help="Job lease duration")
    parser.add_argument("--once", action="store_true", help="Exit after one poll or job")
    parser.add_argument("--max-jobs", type=int, default=None, help="Maximum jobs to execute")
    return parser


def _install_shutdown_handlers(stop_requested: Event) -> None:
    def _request_stop(signum, frame) -> None:  # noqa: ARG001
        stop_requested.set()

    try:
        signal.signal(signal.SIGINT, _request_stop)
        signal.signal(signal.SIGTERM, _request_stop)
    except ValueError:
        # Signal handlers can only be registered from the main thread.
        return


def run(argv: list[str] | None = None) -> int:
    load_runtime_env()
    args = build_parser().parse_args(argv)
    worker_id = args.worker_id or f"{socket.gethostname()}-{uuid4().hex[:8]}"
    stop_requested = Event()
    _install_shutdown_handlers(stop_requested)
    completed = 0

    while not stop_requested.is_set():
        job = backtest_routes._JOB_REPOSITORY.claim_next(
            worker_id=worker_id,
            lease_seconds=args.lease_seconds,
        )
        if job is None:
            if args.once:
                return 0
            stop_requested.wait(args.poll_interval)
            continue

        backtest_routes.execute_backtest_job(job, worker_id, args.lease_seconds)
        completed += 1
        if args.once:
            return 0
        if args.max_jobs is not None and completed >= args.max_jobs:
            return 0
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
