import asyncio

import pytest
from tests.support.asgi import AsyncASGITestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app
from trading_system.backtest.dto import BacktestRunDTO

pytestmark = pytest.mark.anyio


def _build_client() -> AsyncASGITestClient:
    backtest_routes._RUN_REPOSITORY.clear()
    import os
    os.environ["DATABASE_URL"] = ""
    return AsyncASGITestClient(create_app())


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
    backtest_routes._RUN_REPOSITORY.clear()
    import os
    os.environ["DATABASE_URL"] = ""
    return AsyncASGITestClient(create_app())


async def test_post_backtests_and_get_run_result() -> None:
    async with _client() as client:
        response = await client.post("/api/v1/backtests", json=_base_payload(mode="backtest"))

        assert response.status_code == 202
        assert response.json()["status"] == "queued"
        run_id = response.json()["run_id"]
        body = await _wait_for_terminal_run(client, run_id)
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


async def test_live_preflight_returns_ok_message(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "dummy-key")
    async with _client() as client:
        response = await client.post("/api/v1/live/preflight", json=_base_payload(mode="live"))

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "preflight passed" in response.json()["message"]
        assert response.json()["symbol_count"] == 1
        assert response.json()["checks"]
        assert response.json()["next_allowed_actions"] == ["paper"]


async def test_settings_validation_errors_return_422() -> None:
    async with _client() as client:
        payload = _base_payload(mode="backtest")
        payload["risk"]["max_order_size"] = "2"

        response = await client.post("/api/v1/backtests", json=payload)

        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "settings_validation_error"
        assert "--max-order-size cannot exceed --max-position." in body["message"]


async def test_backtest_accepts_multiple_symbols() -> None:
    async with _client() as client:
        payload = _base_payload(mode="backtest")
        payload["symbols"] = ["BTCUSDT", "ETHUSDT"]

        response = await client.post("/api/v1/backtests", json=payload)

        assert response.status_code == 202


async def test_live_preflight_returns_readiness_without_executing(monkeypatch) -> None:
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
    async with _client() as client:
        payload = _base_payload(mode="live", provider="kis", broker="kis")
        payload["symbols"] = ["005930"]
        payload["live_execution"] = "live"
        payload["risk"]["max_order_size"] = "1"
        payload["backtest"]["trade_quantity"] = "1"

        response = await client.post("/api/v1/live/preflight", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert "ready" in body
        assert "reasons" in body
        assert "blocking_reasons" in body
        assert "warnings" in body
        assert "checks" in body
        assert "symbol_checks" in body
        assert "next_allowed_actions" in body
        assert body["symbol_count"] == 1
        assert body["quote_summary"]["symbol"] == "005930"


async def test_live_preflight_accepts_multiple_symbols_for_kis(monkeypatch) -> None:
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
    async with _client() as client:
        payload = _base_payload(mode="live", provider="kis", broker="kis")
        payload["symbols"] = ["005930", "035720"]

        response = await client.post("/api/v1/live/preflight", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["symbol_count"] == 2
        assert body["quote_summary"]["symbol"] == "005930"
        assert [quote["symbol"] for quote in body["quote_summaries"]] == ["005930", "035720"]
        assert [check["symbol"] for check in body["symbol_checks"]] == ["005930", "035720"]


@pytest.mark.anyio
async def test_create_app_defers_recovery_until_lifespan_start() -> None:
    original_repo = backtest_routes._RUN_REPOSITORY
    from trading_system.backtest.repository import InMemoryBacktestRunRepository

    repo = InMemoryBacktestRunRepository()
    repo.save(
        BacktestRunDTO.queued(
            run_id="queued-run",
            started_at="2024-01-01T00:00:00Z",
            input_symbols=["BTCUSDT"],
            mode="backtest",
        )
    )
    backtest_routes._RUN_REPOSITORY = repo
    try:
        app = create_app()
        assert repo.get("queued-run") is not None
        assert repo.get("queued-run").status == "queued"

        async with app.router.lifespan_context(app):
            recovered = repo.get("queued-run")
            assert recovered is not None
            assert recovered.status == "queued"
            assert app.state.backtest_dispatcher.is_running() is True

        assert app.state.backtest_dispatcher.is_running() is False
    finally:
        backtest_routes._RUN_REPOSITORY = original_repo
