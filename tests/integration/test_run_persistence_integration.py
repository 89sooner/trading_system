"""Integration tests for FileBacktestRunRepository persistence.

Validates that:
- A run saved to FileBacktestRunRepository survives repository recreation
  (simulating server restart).
- GET /api/v1/backtests list API returns saved runs with correct pagination
  and status filters.
- GET /api/v1/backtests/{run_id} returns the full persisted run.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app
from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.file_repository import FileBacktestRunRepository


@pytest.fixture(autouse=True)
def _restore_repository():
    """Restore the module-level repository after each test."""
    original = backtest_routes._RUN_REPOSITORY
    yield
    backtest_routes._RUN_REPOSITORY = original


def _make_client(repo: FileBacktestRunRepository) -> TestClient:
    backtest_routes._RUN_REPOSITORY = repo
    return TestClient(create_app(), raise_server_exceptions=False)


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
    }


# ---------------------------------------------------------------------------
# Persistence across repository instances (simulates server restart)
# ---------------------------------------------------------------------------


def test_run_persists_across_repository_recreation(tmp_path):
    """Save a run; recreate the repository; the run should still be listed."""
    repo1 = FileBacktestRunRepository(tmp_path)
    client1 = _make_client(repo1)

    resp = client1.post("/api/v1/backtests", json=_minimal_payload())
    assert resp.status_code == 201
    run_id = resp.json()["run_id"]

    # Recreate the repository (simulates server restart)
    repo2 = FileBacktestRunRepository(tmp_path)
    client2 = _make_client(repo2)

    list_resp = client2.get("/api/v1/backtests")
    assert list_resp.status_code == 200
    run_ids = [r["run_id"] for r in list_resp.json()["runs"]]
    assert run_id in run_ids


def test_run_detail_persists_across_repository_recreation(tmp_path):
    """Full run result survives repository recreation."""
    repo1 = FileBacktestRunRepository(tmp_path)
    client1 = _make_client(repo1)

    resp = client1.post("/api/v1/backtests", json=_minimal_payload())
    assert resp.status_code == 201
    run_id = resp.json()["run_id"]

    repo2 = FileBacktestRunRepository(tmp_path)
    client2 = _make_client(repo2)

    detail = client2.get(f"/api/v1/backtests/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["run_id"] == run_id
    assert body["status"] == "succeeded"
    assert body["result"] is not None


# ---------------------------------------------------------------------------
# List API — pagination and filtering
# ---------------------------------------------------------------------------


def test_list_api_pagination(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    client = _make_client(repo)

    # Create 3 runs
    for _ in range(3):
        r = client.post("/api/v1/backtests", json=_minimal_payload())
        assert r.status_code == 201

    resp = client.get("/api/v1/backtests?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["runs"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2

    resp2 = client.get("/api/v1/backtests?page=2&page_size=2")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["runs"]) == 1


def test_list_api_status_filter(tmp_path):
    repo = FileBacktestRunRepository(tmp_path)
    client = _make_client(repo)

    # Create one real succeeded run via POST
    r = client.post("/api/v1/backtests", json=_minimal_payload())
    assert r.status_code == 201

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

    succeeded_resp = client.get("/api/v1/backtests?status=succeeded")
    assert succeeded_resp.status_code == 200
    assert all(r["status"] == "succeeded" for r in succeeded_resp.json()["runs"])

    failed_resp = client.get("/api/v1/backtests?status=failed")
    assert failed_resp.status_code == 200
    assert any(r["run_id"] == "manual-failed-run" for r in failed_resp.json()["runs"])


def test_list_api_index_rebuilt_from_files(tmp_path):
    """Deleting _index.json and rebuilding should give correct listing."""
    repo = FileBacktestRunRepository(tmp_path)
    client = _make_client(repo)

    r = client.post("/api/v1/backtests", json=_minimal_payload())
    assert r.status_code == 201
    run_id = r.json()["run_id"]

    # Delete the index
    (tmp_path / "_index.json").unlink()

    # Rebuild and re-create repo
    repo2 = FileBacktestRunRepository(tmp_path)
    repo2.rebuild_index()
    client2 = _make_client(repo2)

    list_resp = client2.get("/api/v1/backtests")
    assert list_resp.status_code == 200
    run_ids = [r["run_id"] for r in list_resp.json()["runs"]]
    assert run_id in run_ids
