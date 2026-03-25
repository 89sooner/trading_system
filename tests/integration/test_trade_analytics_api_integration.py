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
            "fee_bps": "0",
            "trade_quantity": "0.1",
        },
    }


def test_trade_analytics_route_returns_stats_for_backtest_run() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    client = TestClient(create_app())

    create_response = client.post("/api/v1/backtests", json=_base_payload())
    run_id = create_response.json()["run_id"]

    analytics_response = client.get(f"/api/v1/analytics/backtests/{run_id}/trades")

    assert analytics_response.status_code == 200
    body = analytics_response.json()
    assert set(body.keys()) == {"stats", "trades"}
    assert set(body["stats"].keys()) == {
        "trade_count",
        "win_rate",
        "risk_reward_ratio",
        "max_drawdown",
        "average_time_in_market_seconds",
    }
