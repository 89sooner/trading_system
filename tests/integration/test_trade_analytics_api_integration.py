import asyncio

import pytest
from tests.support.asgi import AsyncASGITestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app
from trading_system.backtest.dto import BacktestRunDTO

pytestmark = pytest.mark.anyio


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


def _client() -> AsyncASGITestClient:
    return AsyncASGITestClient(create_app())


async def test_trade_analytics_route_returns_stats_for_backtest_run() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    async with _client() as client:
        create_response = await client.post("/api/v1/backtests", json=_base_payload())
        assert create_response.status_code == 202
        run_id = create_response.json()["run_id"]
        await _wait_for_terminal_run(client, run_id)

        analytics_response = await client.get(f"/api/v1/analytics/backtests/{run_id}/trades")

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


async def test_trade_analytics_route_returns_409_for_pending_run() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    backtest_routes._RUN_REPOSITORY.save(
        BacktestRunDTO.queued(
            run_id="queued-run",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    async with _client() as client:
        analytics_response = await client.get("/api/v1/analytics/backtests/queued-run/trades")

        assert analytics_response.status_code == 409
        assert analytics_response.json()["detail"] == "Backtest run is still queued."
