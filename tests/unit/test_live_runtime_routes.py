from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import trading_system.api.routes.dashboard as dashboard_routes
import trading_system.api.routes.live_runtime as live_runtime_routes
from trading_system.api.schemas import ControlActionDTO, LiveRuntimeStartRequestDTO
from trading_system.app.services import PreflightCheckResult
from trading_system.app.state import AppRunnerState
from trading_system.core.ops import EventRecord


def _make_request(controller, live_loop=None):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                live_runtime_controller=controller,
                live_loop=live_loop,
            )
        )
    )


@pytest.mark.anyio
async def test_dashboard_stop_uses_controller_when_session_is_active() -> None:
    controller = MagicMock()
    controller.has_active_session.return_value = True
    request = _make_request(controller)

    response = await dashboard_routes.control_loop(
        ControlActionDTO(action='stop'),
        request,
        None,
    )

    assert response.state == AppRunnerState.STOPPED.value
    controller.stop.assert_called_once_with(requested_by='api')


@pytest.mark.anyio
async def test_dashboard_pause_without_loop_returns_503() -> None:
    request = _make_request(None)

    with pytest.raises(HTTPException) as exc:
        await dashboard_routes.control_loop(
            ControlActionDTO(action='pause'),
            request,
            None,
        )

    assert exc.value.status_code == 503


@pytest.mark.anyio
async def test_dashboard_status_without_loop_returns_controller_snapshot() -> None:
    controller = MagicMock()
    controller.snapshot.return_value = SimpleNamespace(
        controller_state='idle',
        active=False,
        session_id=None,
        live_execution=None,
        last_error='boom',
        provider=None,
        broker=None,
        symbols=None,
        stop_supported=False,
        last_preflight=SimpleNamespace(
            checked_at='2026-04-17T00:00:00Z',
            ready=False,
            message='market closed',
            provider='kis',
            broker='kis',
            symbols=['005930'],
            blocking_reasons=['market_closed'],
            warnings=['market_closed'],
            next_allowed_actions=['review'],
        ),
    )
    request = _make_request(controller, live_loop=None)

    response = await dashboard_routes.get_status(request, None)

    assert response.state == AppRunnerState.STOPPED.value
    assert response.controller_state == 'idle'
    assert response.last_error == 'boom'
    assert response.active is False
    assert response.last_preflight is not None
    assert response.last_preflight.provider == 'kis'
    assert response.last_preflight.blocking_reasons == ['market_closed']


@pytest.mark.anyio
async def test_dashboard_status_normalizes_latest_incident_severity() -> None:
    controller = MagicMock()
    controller.snapshot.return_value = SimpleNamespace(
        controller_state='active',
        active=True,
        session_id='live_20260417_000000',
        live_execution='paper',
        last_error=None,
        provider='mock',
        broker='paper',
        symbols=['BTCUSDT'],
        stop_supported=True,
        last_preflight=None,
    )
    loop = MagicMock()
    loop.state = AppRunnerState.RUNNING
    loop._started_at = None  # noqa: SLF001
    loop._last_heartbeat = None  # noqa: SLF001
    loop.runtime.last_reconciliation_at = None
    loop.runtime.last_reconciliation_status = None
    loop.services.provider = 'mock'
    loop.services.broker = 'paper'
    loop.services.symbols = ('BTCUSDT',)
    loop.services.logger.recent_events.return_value = [
        EventRecord(
            event='system.error',
            severity='warning',
            correlation_id='cid-1',
            timestamp='2026-04-17T00:00:00Z',
            payload={'reason': 'simulated warning'},
        )
    ]
    request = _make_request(controller, live_loop=loop)

    response = await dashboard_routes.get_status(request, loop)

    assert response.latest_incident is not None
    assert response.latest_incident.severity == 'WARNING'
    assert response.latest_incident.summary == 'simulated warning'


def test_start_live_runtime_rejects_duplicate_session(monkeypatch) -> None:
    controller = MagicMock()
    controller.has_active_session.return_value = True
    request = _make_request(controller, live_loop=None)
    payload = LiveRuntimeStartRequestDTO(symbols=['BTCUSDT'])

    with pytest.raises(HTTPException) as exc:
        live_runtime_routes.start_live_runtime(payload, request)

    assert exc.value.status_code == 409


def test_start_live_runtime_runs_preflight_and_returns_started(monkeypatch) -> None:
    controller = MagicMock()
    controller.has_active_session.return_value = False
    controller.start.return_value = SimpleNamespace(
        session_id='live_20260417_000000',
        started_at='2026-04-17T00:00:00Z',
        symbols=['BTCUSDT'],
        provider='mock',
        broker='paper',
        live_execution='paper',
    )
    request = _make_request(controller, live_loop=None)
    payload = LiveRuntimeStartRequestDTO(symbols=['BTCUSDT'])
    settings = MagicMock()

    monkeypatch.setattr(live_runtime_routes, '_to_app_settings', lambda incoming: settings)
    monkeypatch.setattr(
        live_runtime_routes,
        'build_services',
        lambda incoming: SimpleNamespace(
            preflight_live=lambda: PreflightCheckResult(
                ready=True,
                reasons=[],
                quote_summary=None,
                quote_summaries=None,
                symbol_count=1,
                message='ok',
                checks=[],
                symbol_checks=[],
                next_allowed_actions=['paper'],
                checked_at='2026-04-17T00:00:00Z',
            )
        ),
    )

    response = live_runtime_routes.start_live_runtime(payload, request)

    assert response.status == 'started'
    assert response.state == 'starting'
    assert response.preflight is not None
    assert response.preflight.next_allowed_actions == ['paper']
    controller.start.assert_called_once_with(settings)


def test_start_live_runtime_rejects_failed_preflight(monkeypatch) -> None:
    controller = MagicMock()
    controller.has_active_session.return_value = False
    request = _make_request(controller, live_loop=None)
    payload = LiveRuntimeStartRequestDTO(symbols=['BTCUSDT'])

    monkeypatch.setattr(live_runtime_routes, '_to_app_settings', lambda incoming: MagicMock())
    monkeypatch.setattr(
        live_runtime_routes,
        'build_services',
        lambda incoming: SimpleNamespace(
            preflight_live=lambda: PreflightCheckResult(
                ready=False,
                reasons=['market_closed'],
                quote_summary=None,
                quote_summaries=None,
                symbol_count=1,
                message='market closed',
                blocking_reasons=['market_closed'],
                warnings=[],
                checks=[],
                symbol_checks=[],
                next_allowed_actions=['review'],
                checked_at='2026-04-17T00:00:00Z',
            )
        ),
    )

    with pytest.raises(HTTPException) as exc:
        live_runtime_routes.start_live_runtime(payload, request)

    assert exc.value.status_code == 409
