"""Unit tests for the live dashboard API routes."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from trading_system.api.server import create_app
from trading_system.app.state import AppRunnerState
from trading_system.core.ops import EventRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_loop(state: AppRunnerState = AppRunnerState.RUNNING) -> MagicMock:
    loop = MagicMock()
    loop.state = state
    loop._last_heartbeat = None  # noqa: SLF001
    loop._started_at = None  # noqa: SLF001

    # Services mock
    portfolio = MagicMock()
    portfolio.cash = Decimal("9800.00")
    portfolio.positions = {"BTCUSDT": Decimal("0.2")}
    portfolio.average_costs = {"BTCUSDT": Decimal("50000")}
    loop.services.portfolio = portfolio

    # Logger with empty buffer
    logger = MagicMock()
    logger.recent_events.return_value = []
    loop.services.logger = logger

    return loop


def _make_client(loop=None) -> TestClient:
    app = create_app(live_loop=loop)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


class TestDashboardStatus:
    def test_no_loop_returns_503(self) -> None:
        client = _make_client(loop=None)
        resp = client.get("/api/v1/dashboard/status")
        assert resp.status_code == 503

    def test_running_loop_returns_state(self) -> None:
        loop = _make_loop(AppRunnerState.RUNNING)
        client = _make_client(loop)
        resp = client.get("/api/v1/dashboard/status")
        assert resp.status_code == 200
        assert resp.json()["state"] == "running"

    def test_paused_loop_returns_state(self) -> None:
        loop = _make_loop(AppRunnerState.PAUSED)
        client = _make_client(loop)
        resp = client.get("/api/v1/dashboard/status")
        assert resp.status_code == 200
        assert resp.json()["state"] == "paused"


# ---------------------------------------------------------------------------
# GET /positions
# ---------------------------------------------------------------------------


class TestDashboardPositions:
    def test_no_loop_returns_503(self) -> None:
        client = _make_client(loop=None)
        resp = client.get("/api/v1/dashboard/positions")
        assert resp.status_code == 503

    def test_returns_positions_and_cash(self) -> None:
        loop = _make_loop()
        client = _make_client(loop)
        resp = client.get("/api/v1/dashboard/positions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["cash"] == "9800.00"
        assert len(body["positions"]) == 1
        assert body["positions"][0]["symbol"] == "BTCUSDT"
        assert body["positions"][0]["quantity"] == "0.2"


# ---------------------------------------------------------------------------
# GET /events
# ---------------------------------------------------------------------------


class TestDashboardEvents:
    def test_returns_empty_feed(self) -> None:
        loop = _make_loop()
        loop.services.logger.recent_events.return_value = []
        client = _make_client(loop)
        resp = client.get("/api/v1/dashboard/events")
        assert resp.status_code == 200
        assert resp.json()["events"] == []
        assert resp.json()["total"] == 0

    def test_returns_event_records(self) -> None:
        loop = _make_loop()
        record = EventRecord(
            event="strategy.signal",
            severity="INFO",
            correlation_id="abc123",
            timestamp="2025-01-01T00:00:00+00:00",
            payload={"side": "buy"},
        )
        loop.services.logger.recent_events.return_value = [record]
        client = _make_client(loop)
        resp = client.get("/api/v1/dashboard/events?limit=10")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 1
        assert events[0]["event"] == "strategy.signal"


# ---------------------------------------------------------------------------
# POST /control
# ---------------------------------------------------------------------------


class TestDashboardControl:
    def test_pause_running_loop(self) -> None:
        loop = _make_loop(AppRunnerState.RUNNING)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "pause"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.PAUSED

    def test_resume_paused_loop(self) -> None:
        loop = _make_loop(AppRunnerState.PAUSED)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "resume"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.RUNNING

    def test_reset_emergency_loop_to_paused(self) -> None:
        loop = _make_loop(AppRunnerState.EMERGENCY)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "reset"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.PAUSED

    def test_invalid_action_returns_422(self) -> None:
        loop = _make_loop()
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "explode"})
        assert resp.status_code == 422

    def test_stop_action_returns_422(self) -> None:
        loop = _make_loop(AppRunnerState.RUNNING)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "stop"})
        assert resp.status_code == 422

    # ── Idempotent / no-op transitions ──────────────────────────────────

    def test_pause_already_paused_is_noop(self) -> None:
        loop = _make_loop(AppRunnerState.PAUSED)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "pause"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.PAUSED

    def test_resume_already_running_is_noop(self) -> None:
        loop = _make_loop(AppRunnerState.RUNNING)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "resume"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.RUNNING

    def test_reset_when_not_emergency_is_noop(self) -> None:
        loop = _make_loop(AppRunnerState.RUNNING)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "reset"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.RUNNING

    def test_pause_during_emergency_is_noop(self) -> None:
        loop = _make_loop(AppRunnerState.EMERGENCY)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "pause"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.EMERGENCY

    def test_resume_during_emergency_is_noop(self) -> None:
        loop = _make_loop(AppRunnerState.EMERGENCY)
        client = _make_client(loop)
        resp = client.post("/api/v1/dashboard/control", json={"action": "resume"})
        assert resp.status_code == 200
        assert loop.state == AppRunnerState.EMERGENCY
