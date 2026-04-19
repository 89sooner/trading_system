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
    import os

    os.environ["DATABASE_URL"] = ""
    with TestClient(create_app()) as client:
        yield client


def test_backtest_result_schema_is_stable_for_visualization_clients() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    with _client() as client:
        create_response = client.post("/api/v1/backtests", json=_base_payload())
        run_id = create_response.json()["run_id"]
        result = _wait_for_terminal_run(client, run_id)["result"]
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
        assert all(
            set(point.keys()) == {"timestamp", "drawdown"}
            for point in result["drawdown_curve"]
        )
        assert all(set(event.keys()) == {"event", "payload"} for event in result["orders"])
        assert all(set(event.keys()) == {"event", "payload"} for event in result["risk_rejections"])
        assert all(set(event.keys()) == {"event", "payload"} for event in result["signals"])


def test_backtest_result_schema_has_matching_curve_lengths() -> None:
    backtest_routes._RUN_REPOSITORY.clear()
    with _client() as client:
        create_response = client.post("/api/v1/backtests", json=_base_payload())
        run_id = create_response.json()["run_id"]
        result = _wait_for_terminal_run(client, run_id)["result"]
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
    with _client() as client:
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
            "blocking_reasons",
            "warnings",
            "quote_summary",
            "quote_summaries",
            "symbol_count",
            "checks",
            "symbol_checks",
            "next_allowed_actions",
            "checked_at",
            "paper_result",
        }
        assert body["symbol_count"] == 2
        assert len(body["quote_summaries"]) == 2
