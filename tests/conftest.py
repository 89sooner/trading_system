"""Shared test fixtures."""

import os
import tempfile

import pytest

from trading_system.api.routes import backtest as backtest_routes
from trading_system.backtest.file_repository import FileBacktestRunRepository


@pytest.fixture(autouse=True)
def _bypass_api_key_auth():
    """Disable API key security middleware for all tests.

    Clears both the repo-based key path and the env-var-based allowed keys so
    that .env values (loaded by load_dotenv() in server.py) do not bleed
    across test cases.
    """
    empty_keys = os.path.join(tempfile.gettempdir(), "test_empty_api_keys.json")
    if not os.path.exists(empty_keys):
        with open(empty_keys, "w") as f:
            f.write("[]")

    old_path = os.environ.get("TRADING_SYSTEM_API_KEYS_PATH")
    old_allowed = os.environ.get("TRADING_SYSTEM_ALLOWED_API_KEYS")

    os.environ["TRADING_SYSTEM_API_KEYS_PATH"] = empty_keys
    os.environ["TRADING_SYSTEM_ALLOWED_API_KEYS"] = ""

    yield

    if old_path is None:
        os.environ.pop("TRADING_SYSTEM_API_KEYS_PATH", None)
    else:
        os.environ["TRADING_SYSTEM_API_KEYS_PATH"] = old_path

    if old_allowed is None:
        os.environ.pop("TRADING_SYSTEM_ALLOWED_API_KEYS", None)
    else:
        os.environ["TRADING_SYSTEM_ALLOWED_API_KEYS"] = old_allowed


@pytest.fixture(autouse=True)
def _isolate_runtime_storage(tmp_path):
    """Keep API tests from writing run/job/audit artifacts into repository data."""
    old_runs_dir = os.environ.get("TRADING_SYSTEM_RUNS_DIR")
    old_order_audit_dir = os.environ.get("TRADING_SYSTEM_ORDER_AUDIT_DIR")
    original_run_repo = backtest_routes._RUN_REPOSITORY
    original_job_repo = backtest_routes._JOB_REPOSITORY

    runs_dir = tmp_path / "runs"
    order_audit_dir = tmp_path / "order_audit"
    os.environ["TRADING_SYSTEM_RUNS_DIR"] = str(runs_dir)
    os.environ["TRADING_SYSTEM_ORDER_AUDIT_DIR"] = str(order_audit_dir)
    repo = FileBacktestRunRepository(runs_dir)
    backtest_routes._RUN_REPOSITORY = repo
    backtest_routes._JOB_REPOSITORY = repo

    yield

    backtest_routes._RUN_REPOSITORY = original_run_repo
    backtest_routes._JOB_REPOSITORY = original_job_repo
    if old_runs_dir is None:
        os.environ.pop("TRADING_SYSTEM_RUNS_DIR", None)
    else:
        os.environ["TRADING_SYSTEM_RUNS_DIR"] = old_runs_dir
    if old_order_audit_dir is None:
        os.environ.pop("TRADING_SYSTEM_ORDER_AUDIT_DIR", None)
    else:
        os.environ["TRADING_SYSTEM_ORDER_AUDIT_DIR"] = old_order_audit_dir
