import pytest
from tests.support.asgi import AsyncASGITestClient

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.server import create_app

pytestmark = pytest.mark.anyio


def _payload() -> dict:
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


def _client() -> AsyncASGITestClient:
    backtest_routes._RUN_REPOSITORY.clear()
    return AsyncASGITestClient(create_app())


async def test_api_key_auth_failure_returns_401(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_ALLOWED_API_KEYS", "test-key")
    async with _client() as client:
        response = await client.post("/api/v1/backtests", json=_payload())

        assert response.status_code == 401
        assert response.json() == {
            "error_code": "auth_invalid_api_key",
            "message": "Missing or invalid API key.",
        }


async def test_request_validation_failure_returns_standardized_400(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_ALLOWED_API_KEYS", "test-key")
    async with _client() as client:
        payload = _payload()
        payload["backtest"]["fee_bps"] = "1001"

        response = await client.post(
            "/api/v1/backtests",
            json=payload,
            headers={"X-API-Key": "test-key"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "error_code": "invalid_fee_bps",
            "message": "fee_bps must be between 0 and 1000.",
        }


async def test_rate_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_ALLOWED_API_KEYS", "test-key")
    monkeypatch.setenv("TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS", "60")
    async with _client() as client:
        first_response = await client.post(
            "/api/v1/backtests",
            json=_payload(),
            headers={"X-API-Key": "test-key"},
        )
        second_response = await client.post(
            "/api/v1/backtests",
            json=_payload(),
            headers={"X-API-Key": "test-key"},
        )

        assert first_response.status_code == 202
        assert second_response.status_code == 429
        assert second_response.json() == {
            "error_code": "rate_limit_exceeded",
            "message": "Too many requests. Please retry later.",
        }
