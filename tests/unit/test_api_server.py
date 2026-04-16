import time
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app
from trading_system.backtest.dto import BacktestRunDTO


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
    backtest_routes._RUN_REPOSITORY.clear()
    with TestClient(create_app()) as client:
        yield client


def test_post_backtests_and_get_run_result() -> None:
    with _client() as client:
        response = client.post("/api/v1/backtests", json=_base_payload(mode="backtest"))

        assert response.status_code == 202
        assert response.json()["status"] == "queued"
        run_id = response.json()["run_id"]
        body = _wait_for_terminal_run(client, run_id)
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
    with _client() as client:
        response = client.post("/api/v1/live/preflight", json=_base_payload(mode="live"))

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "preflight passed" in response.json()["message"]
        assert response.json()["symbol_count"] == 1


def test_settings_validation_errors_return_422() -> None:
    with _client() as client:
        payload = _base_payload(mode="backtest")
        payload["risk"]["max_order_size"] = "2"

        response = client.post("/api/v1/backtests", json=payload)

        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "settings_validation_error"
        assert "--max-order-size cannot exceed --max-position." in body["message"]


def test_backtest_accepts_multiple_symbols() -> None:
    with _client() as client:
        payload = _base_payload(mode="backtest")
        payload["symbols"] = ["BTCUSDT", "ETHUSDT"]

        response = client.post("/api/v1/backtests", json=payload)

        assert response.status_code == 202


def test_live_preflight_returns_readiness_without_executing(monkeypatch) -> None:
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
    with _client() as client:
        payload = _base_payload(mode="live", provider="kis", broker="kis")
        payload["symbols"] = ["005930"]
        payload["live_execution"] = "live"

        response = client.post("/api/v1/live/preflight", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert "ready" in body
        assert "reasons" in body
        assert body["symbol_count"] == 1
        assert body["quote_summary"]["symbol"] == "005930"


def test_live_preflight_accepts_multiple_symbols_for_kis(monkeypatch) -> None:
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
    with _client() as client:
        payload = _base_payload(mode="live", provider="kis", broker="kis")
        payload["symbols"] = ["005930", "035720"]

        response = client.post("/api/v1/live/preflight", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["symbol_count"] == 2
        assert body["quote_summary"]["symbol"] == "005930"
        assert [quote["symbol"] for quote in body["quote_summaries"]] == ["005930", "035720"]


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
            assert recovered.status == "failed"
            assert app.state.backtest_dispatcher.is_running() is True

        assert app.state.backtest_dispatcher.is_running() is False
    finally:
        backtest_routes._RUN_REPOSITORY = original_repo
