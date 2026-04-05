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


def test_backtest_result_schema_is_stable_for_visualization_clients() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    client = TestClient(create_app())

    create_response = client.post("/api/v1/backtests", json=_base_payload())
    run_id = create_response.json()["run_id"]
    get_response = client.get(f"/api/v1/backtests/{run_id}")

    assert get_response.status_code == 200
    result = get_response.json()["result"]
    assert set(result.keys()) == {
        "summary",
        "equity_curve",
        "drawdown_curve",
        "signals",
        "orders",
        "risk_rejections",
    }
    assert set(result["summary"].keys()) == {"return", "max_drawdown", "volatility", "win_rate"}
    assert all(set(point.keys()) == {"timestamp", "equity"} for point in result["equity_curve"])
    assert all(set(point.keys()) == {"timestamp", "drawdown"} for point in result["drawdown_curve"])
    assert all(set(event.keys()) == {"event", "payload"} for event in result["orders"])
    assert all(set(event.keys()) == {"event", "payload"} for event in result["risk_rejections"])
    assert all(set(event.keys()) == {"event", "payload"} for event in result["signals"])


def test_backtest_result_schema_has_matching_curve_lengths() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    client = TestClient(create_app())

    create_response = client.post("/api/v1/backtests", json=_base_payload())
    run_id = create_response.json()["run_id"]
    get_response = client.get(f"/api/v1/backtests/{run_id}")

    result = get_response.json()["result"]
    assert len(result["equity_curve"]) == len(result["drawdown_curve"])


def test_live_preflight_schema_supports_multi_symbol_details(monkeypatch) -> None:
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
    client = TestClient(create_app())
    payload = _base_payload()
    payload["mode"] = "live"
    payload["provider"] = "kis"
    payload["broker"] = "kis"
    payload["symbols"] = ["005930", "035720"]

    response = client.post("/api/v1/live/preflight", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "status",
        "message",
        "ready",
        "reasons",
        "quote_summary",
        "quote_summaries",
        "symbol_count",
        "paper_result",
    }
    assert body["symbol_count"] == 2
    assert len(body["quote_summaries"]) == 2
