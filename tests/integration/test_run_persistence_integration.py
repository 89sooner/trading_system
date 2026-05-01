"""Integration tests for FileBacktestRunRepository persistence.

Validates that:
- A run saved to FileBacktestRunRepository survives repository recreation
  (simulating server restart).
- GET /api/v1/backtests list API returns saved runs with correct pagination
  and status filters.
- GET /api/v1/backtests/{run_id} returns the full persisted run.
"""
from __future__ import annotations

import asyncio

import pytest
from tests.support.asgi import AsyncASGITestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app
from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.file_repository import FileBacktestRunRepository

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _restore_repository():
    """Restore the module-level repository after each test."""
    original_run_repo = backtest_routes._RUN_REPOSITORY
    original_job_repo = backtest_routes._JOB_REPOSITORY
    import os

    old_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = ""
    yield
    backtest_routes._RUN_REPOSITORY = original_run_repo
    backtest_routes._JOB_REPOSITORY = original_job_repo
    if old_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = old_database_url


def _client(repo: FileBacktestRunRepository) -> AsyncASGITestClient:
    backtest_routes._RUN_REPOSITORY = repo
    backtest_routes._JOB_REPOSITORY = repo
    return AsyncASGITestClient(create_app(), raise_app_exceptions=False)


def _minimal_payload() -> dict:
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
        "metadata": {
            "source": "integration-test",
            "notes": "persistence check",
        },
    }


async def _wait_for_terminal_run(
    client: AsyncASGITestClient,
    run_id: str,
    timeout: float = 3.0,
) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(f"/api/v1/backtests/{run_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"succeeded", "failed"}:
            return body
        await asyncio.sleep(0.05)
    raise AssertionError(f"Run {run_id} did not reach terminal state within {timeout}s")


# ---------------------------------------------------------------------------
# Persistence across repository instances (simulates server restart)
# ---------------------------------------------------------------------------


async def test_run_persists_across_repository_recreation(tmp_path):
    """Save a run; recreate the repository; the run should still be listed."""
    repo1 = FileBacktestRunRepository(tmp_path)
    async with _client(repo1) as client1:
        resp = await client1.post("/api/v1/backtests", json=_minimal_payload())
        assert resp.status_code == 202
        run_id = resp.json()["run_id"]
        await _wait_for_terminal_run(client1, run_id)

    # Recreate the repository (simulates server restart)
    repo2 = FileBacktestRunRepository(tmp_path)
    async with _client(repo2) as client2:
        list_resp = await client2.get("/api/v1/backtests")
        assert list_resp.status_code == 200
        run_ids = [r["run_id"] for r in list_resp.json()["runs"]]
        assert run_id in run_ids


async def test_run_detail_persists_across_repository_recreation(tmp_path):
    """Full run result survives repository recreation."""
    repo1 = FileBacktestRunRepository(tmp_path)
    async with _client(repo1) as client1:
        resp = await client1.post("/api/v1/backtests", json=_minimal_payload())
        assert resp.status_code == 202
        run_id = resp.json()["run_id"]
        await _wait_for_terminal_run(client1, run_id)

    repo2 = FileBacktestRunRepository(tmp_path)
    async with _client(repo2) as client2:
        detail = await client2.get(f"/api/v1/backtests/{run_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["run_id"] == run_id
        assert body["status"] == "succeeded"
        assert body["metadata"]["source"] == "integration-test"
        assert body["metadata"]["provider"] == "mock"
        assert body["result"] is not None


# ---------------------------------------------------------------------------
# List API — pagination and filtering
# ---------------------------------------------------------------------------


async def test_list_api_pagination(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    async with _client(repo) as client:
        # Create 3 runs
        for _ in range(3):
            r = await client.post("/api/v1/backtests", json=_minimal_payload())
            assert r.status_code == 202
            await _wait_for_terminal_run(client, r.json()["run_id"])

        resp = await client.get("/api/v1/backtests?page=1&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["runs"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2

        resp2 = await client.get("/api/v1/backtests?page=2&page_size=2")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert len(body2["runs"]) == 1


async def test_list_api_status_filter(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    async with _client(repo) as client:
        # Create one real succeeded run via POST
        r = await client.post("/api/v1/backtests", json=_minimal_payload())
        assert r.status_code == 202
        await _wait_for_terminal_run(client, r.json()["run_id"])

        # Manually add a "failed" run directly to the repo
        failed_run = BacktestRunDTO(
            run_id="manual-failed-run",
            status="failed",
            started_at="2024-01-01T00:00:00Z",
            finished_at="2024-01-01T00:01:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
            error="forced failure",
        )
        repo.save(failed_run)

        succeeded_resp = await client.get("/api/v1/backtests?status=succeeded")
        assert succeeded_resp.status_code == 200
        assert all(r["status"] == "succeeded" for r in succeeded_resp.json()["runs"])

        failed_resp = await client.get("/api/v1/backtests?status=failed")
        assert failed_resp.status_code == 200
        assert any(r["run_id"] == "manual-failed-run" for r in failed_resp.json()["runs"])


async def test_list_api_index_rebuilt_from_files(tmp_path):
    """Deleting _index.json and rebuilding should give correct listing."""
    repo = FileBacktestRunRepository(tmp_path)
    async with _client(repo) as client:
        r = await client.post("/api/v1/backtests", json=_minimal_payload())
        assert r.status_code == 202
        run_id = r.json()["run_id"]
        await _wait_for_terminal_run(client, run_id)

    # Delete the index
    (tmp_path / "_index.json").unlink()

    # Rebuild and re-create repo
    repo2 = FileBacktestRunRepository(tmp_path)
    repo2.rebuild_index()
    async with _client(repo2) as client2:
        list_resp = await client2.get("/api/v1/backtests")
        assert list_resp.status_code == 200
        run_ids = [r["run_id"] for r in list_resp.json()["runs"]]
        assert run_id in run_ids
