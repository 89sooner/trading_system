from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import trading_system.api.routes.dashboard as dashboard_routes
import trading_system.api.routes.live_runtime as live_runtime_routes
from trading_system.api.schemas import ControlActionDTO, LiveRuntimeStartRequestDTO
from trading_system.app.services import PreflightCheckResult
from trading_system.app.state import AppRunnerState


class _FakeController:
    def __init__(self) -> None:
        self._active = False
        self._session = None
        self.stop_calls = 0

    def has_active_session(self) -> bool:
        return self._active

    def start(self, settings):
        self._active = True
        self._session = SimpleNamespace(
            session_id='live_20260418_000000',
            started_at='2026-04-18T00:00:00Z',
            symbols=list(settings.symbols),
            provider=settings.provider,
            broker=settings.broker,
            live_execution=settings.live_execution.value,
        )
        return self._session

    def stop(self, requested_by: str = 'api') -> None:
        self.stop_calls += 1
        self._active = False

    def snapshot(self):
        if self._active:
            return SimpleNamespace(
                controller_state='active',
                session_id=self._session.session_id,
                live_execution=self._session.live_execution,
                last_error=None,
                provider=self._session.provider,
                symbols=self._session.symbols,
            )
        return SimpleNamespace(
            controller_state='idle',
            session_id=None,
            live_execution=None,
            last_error=None,
            provider=None,
            symbols=None,
        )


def _make_request(controller, live_loop=None):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                live_runtime_controller=controller,
                live_loop=live_loop,
            )
        )
    )


def test_start_route_uses_real_settings_and_returns_session(monkeypatch) -> None:
    controller = _FakeController()
    request = _make_request(controller)
    payload = LiveRuntimeStartRequestDTO(
        symbols=['BTCUSDT'],
        provider='mock',
        broker='paper',
        live_execution='paper',
    )

    monkeypatch.setattr(
        live_runtime_routes,
        'build_services',
        lambda settings: SimpleNamespace(
            preflight_live=lambda: PreflightCheckResult(
                ready=True,
                reasons=[],
                quote_summary=None,
                quote_summaries=None,
                symbol_count=1,
                message='ok',
            )
        ),
    )

    response = live_runtime_routes.start_live_runtime(payload, request)

    assert response.status == 'started'
    assert response.session_id == 'live_20260418_000000'
    assert response.symbols == ['BTCUSDT']
    assert controller.has_active_session() is True


@pytest.mark.anyio
async def test_dashboard_status_and_stop_reflect_controller_state() -> None:
    controller = _FakeController()
    controller._active = True
    controller._session = SimpleNamespace(
        session_id='live_20260418_000000',
        live_execution='paper',
        provider='mock',
        symbols=['BTCUSDT'],
    )
    request = _make_request(controller, live_loop=None)

    status = await dashboard_routes.get_status(request, None)
    assert status.controller_state == 'active'
    assert status.session_id == 'live_20260418_000000'
    assert status.state == AppRunnerState.STOPPED.value

    response = await dashboard_routes.control_loop(
        ControlActionDTO(action='stop'),
        request,
        None,
    )
    assert response.state == AppRunnerState.STOPPED.value
    assert controller.stop_calls == 1


@pytest.mark.anyio
async def test_dashboard_stop_without_active_runtime_returns_409() -> None:
    request = _make_request(_FakeController(), live_loop=None)

    with pytest.raises(HTTPException) as exc:
        await dashboard_routes.control_loop(
            ControlActionDTO(action='stop'),
            request,
            None,
        )

    assert exc.value.status_code == 409
