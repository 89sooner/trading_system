from fastapi.testclient import TestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app


def _build_client() -> TestClient:
    backtest_routes._RUNS.clear()
    return TestClient(create_app())


def _base_payload(mode: str) -> dict:
    return {
        "mode": mode,
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


def test_post_backtests_and_get_run_result() -> None:
    client = _build_client()
    response = client.post("/api/v1/backtests", json=_base_payload(mode="backtest"))

    assert response.status_code == 201
    run_id = response.json()["run_id"]

    run_response = client.get(f"/api/v1/backtests/{run_id}")

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "succeeded"
    assert body["result"]["processed_bars"] > 0


def test_live_preflight_returns_ok_message(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "dummy-key")
    client = _build_client()
    response = client.post("/api/v1/live/preflight", json=_base_payload(mode="live"))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "preflight passed" in response.json()["message"]


def test_settings_validation_errors_return_422() -> None:
    client = _build_client()
    payload = _base_payload(mode="backtest")
    payload["risk"]["max_order_size"] = "2"

    response = client.post("/api/v1/backtests", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "settings_validation_error"
    assert "--max-order-size cannot exceed --max-position." in body["message"]


def test_runtime_errors_return_structured_500() -> None:
    client = _build_client()
    payload = _base_payload(mode="backtest")
    payload["symbols"] = ["BTCUSDT", "ETHUSDT"]

    response = client.post("/api/v1/backtests", json=payload)

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error_code": "runtime_error",
        "message": "Current scaffold supports exactly one symbol for backtest mode.",
    }
