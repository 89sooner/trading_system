import time
from contextlib import contextmanager

from fastapi.testclient import TestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app


def _base_payload() -> dict:
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


def _wait_for_terminal_run(client: TestClient, run_id: str, timeout: float = 3.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/backtests/{run_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"succeeded", "failed"}:
            return body
        time.sleep(0.05)
    raise AssertionError(f"Run {run_id} did not reach terminal state within {timeout}s")


@contextmanager
def _client():
    with TestClient(create_app()) as client:
        yield client


def test_create_then_get_backtest_run_returns_serialized_result_and_metadata() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    with _client() as client:
        create_response = client.post("/api/v1/backtests", json=_base_payload())

        assert create_response.status_code == 202
        assert create_response.json()["status"] == "queued"
        run_id = create_response.json()["run_id"]
        body = _wait_for_terminal_run(client, run_id)
        assert body["run_id"] == run_id
        assert body["status"] == "succeeded"
        assert body["mode"] == "backtest"
        assert body["input_symbols"] == ["BTCUSDT"]
        assert body["started_at"].endswith("Z")
        assert body["finished_at"] is not None
        assert body["finished_at"].endswith("Z")

        result = body["result"]
        assert set(result.keys()) == {
            "summary",
            "equity_curve",
            "drawdown_curve",
            "signals",
            "orders",
            "risk_rejections",
        }
        assert isinstance(result["summary"]["return"], str)
        assert isinstance(result["summary"]["max_drawdown"], str)
        assert isinstance(result["summary"]["volatility"], str)
        assert isinstance(result["summary"]["win_rate"], str)
        assert all(isinstance(point["timestamp"], str) for point in result["equity_curve"])
        assert all(isinstance(point["equity"], str) for point in result["equity_curve"])
        assert all(isinstance(point["timestamp"], str) for point in result["drawdown_curve"])
        assert all(isinstance(point["drawdown"], str) for point in result["drawdown_curve"])


def test_get_backtest_run_returns_404_for_unknown_run_id() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    with _client() as client:
        response = client.get("/api/v1/backtests/does-not-exist")

        assert response.status_code == 404
        assert response.json() == {"detail": "Backtest run not found"}
