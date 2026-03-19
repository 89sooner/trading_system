from fastapi.testclient import TestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app


def _build_client() -> TestClient:
    backtest_routes._RUN_REPOSITORY.clear()
    return TestClient(create_app())


def _base_payload(mode: str, *, provider: str = "mock", broker: str = "paper") -> dict:
    return {
        "mode": mode,
        "symbols": ["BTCUSDT"],
        "provider": provider,
        "broker": broker,
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
    assert body["mode"] == "backtest"
    assert body["input_symbols"] == ["BTCUSDT"]
    result = body["result"]
    assert set(result.keys()) == {
        "summary",
        "equity_curve",
        "drawdown_curve",
        "signals",
        "orders",
        "risk_rejections",
    }
    assert len(result["equity_curve"]) > 0


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


def test_invalid_symbols_return_standardized_400() -> None:
    client = _build_client()
    payload = _base_payload(mode="backtest")
    payload["symbols"] = ["BTCUSDT", "ETHUSDT"]

    response = client.post("/api/v1/backtests", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "error_code": "invalid_symbols",
        "message": "Exactly one symbol is required for this API runtime.",
    }


def test_live_execution_requires_opt_in_flag(monkeypatch) -> None:
    class _StubServicesKisClient:
        def preflight_symbol(self, symbol: str):
            class Quote:
                def __init__(self, quote_symbol: str) -> None:
                    self.symbol = quote_symbol
                    self.price = "70000"
                    self.volume = "1000"

            return Quote(symbol)

    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubServicesKisClient(),
    )
    monkeypatch.setenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "false")
    client = _build_client()
    payload = _base_payload(mode="live", provider="kis", broker="kis")
    payload["symbols"] = ["005930"]
    payload["live_execution"] = "live"

    response = client.post("/api/v1/live/preflight", json=payload)

    assert response.status_code == 500
    assert response.json()["error_code"] == "runtime_error"
