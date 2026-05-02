from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import trading_system.api.routes.dashboard as dashboard_routes
import trading_system.api.routes.live_runtime as live_runtime_routes
from trading_system.api.schemas import ControlActionDTO, LiveRuntimeStartRequestDTO
from trading_system.app.services import PreflightCheckResult
from trading_system.app.state import AppRunnerState
from trading_system.execution.broker import OrderCancelResult
from trading_system.execution.live_orders import (
    FileLiveOrderRepository,
    LiveOrderStatus,
    new_live_order_record,
)


class _FakeController:
    def __init__(self) -> None:
        self._active = False
        self._session = None
        self.stop_calls = 0
        self._last_preflight = None

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

    def record_preflight(self, settings, result) -> None:
        self._last_preflight = SimpleNamespace(
            checked_at=result.checked_at,
            ready=result.ready,
            message=result.message,
            provider=settings.provider,
            broker=settings.broker,
            symbols=list(settings.symbols),
            blocking_reasons=list(result.blocking_reasons),
            warnings=list(result.warnings),
            next_allowed_actions=list(result.next_allowed_actions),
        )

    def snapshot(self):
        if self._active:
            return SimpleNamespace(
                controller_state='active',
                active=True,
                session_id=self._session.session_id,
                live_execution=self._session.live_execution,
                last_error=None,
                provider=self._session.provider,
                broker=self._session.broker,
                symbols=self._session.symbols,
                stop_supported=True,
                last_preflight=self._last_preflight,
            )
        return SimpleNamespace(
            controller_state='idle',
            active=False,
            session_id=None,
            live_execution=None,
            last_error=None,
            provider=None,
            broker=None,
            symbols=None,
            stop_supported=False,
            last_preflight=self._last_preflight,
        )


class _FakeHistoryRepo:
    def __init__(self) -> None:
        self._records = []

    def save(self, record) -> None:
        self._records = [item for item in self._records if item.session_id != record.session_id]
        self._records.append(record)

    def get(self, session_id: str):
        for record in self._records:
            if record.session_id == session_id:
                return record
        return None

    def list(self, limit: int = 20):
        return list(reversed(self._records))[:limit]


def _make_request(controller, live_loop=None):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                live_runtime_controller=controller,
                live_loop=live_loop,
                live_runtime_history_repository=_FakeHistoryRepo(),
                live_order_repository=None,
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
                checks=[],
                symbol_checks=[],
                next_allowed_actions=['paper'],
                checked_at='2026-04-18T00:00:00Z',
            )
        ),
    )

    response = live_runtime_routes.start_live_runtime(payload, request)

    assert response.status == 'started'
    assert response.session_id == 'live_20260418_000000'
    assert response.symbols == ['BTCUSDT']
    assert response.preflight is not None
    assert response.preflight.checked_at == '2026-04-18T00:00:00Z'
    assert response.preflight.next_allowed_actions == ['paper']
    assert controller.has_active_session() is True


@pytest.mark.anyio
async def test_dashboard_status_and_stop_reflect_controller_state() -> None:
    controller = _FakeController()
    controller._active = True
    controller._session = SimpleNamespace(
        session_id='live_20260418_000000',
        live_execution='paper',
        provider='mock',
        broker='paper',
        symbols=['BTCUSDT'],
    )
    request = _make_request(controller, live_loop=None)

    status = await dashboard_routes.get_status(request, None)
    assert status.controller_state == 'active'
    assert status.session_id == 'live_20260418_000000'
    assert status.state == AppRunnerState.STOPPED.value
    assert status.active is True
    assert status.stop_supported is True

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


def test_live_runtime_session_routes_return_history() -> None:
    history = _FakeHistoryRepo()
    record = SimpleNamespace(
        session_id='live_20260418_000000',
        started_at='2026-04-18T00:00:00Z',
        ended_at='2026-04-18T00:10:00Z',
        provider='kis',
        broker='kis',
        live_execution='paper',
        symbols=['005930'],
        last_state='stopped',
        last_error=None,
        preflight_summary={'message': 'ok', 'ready': True},
    )
    history.save(record)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                live_runtime_history_repository=history,
            )
        )
    )

    listing = live_runtime_routes.list_live_runtime_sessions(request, limit=10)
    detail = live_runtime_routes.get_live_runtime_session('live_20260418_000000', request)

    assert listing.total == 1
    assert listing.sessions[0].provider == 'kis'
    assert detail.session_id == 'live_20260418_000000'
    assert detail.preflight_summary == {'message': 'ok', 'ready': True}


@pytest.mark.anyio
async def test_dashboard_live_order_list_and_cancel(tmp_path) -> None:
    controller = _FakeController()
    controller._active = True
    controller._session = SimpleNamespace(
        session_id='live_20260418_000000',
        live_execution='live',
        provider='kis',
        broker='kis',
        symbols=['005930'],
    )
    repo = FileLiveOrderRepository(tmp_path)
    record = new_live_order_record(
        session_id='live_20260418_000000',
        symbol='005930',
        side='buy',
        requested_quantity='3',
        filled_quantity='0',
        remaining_quantity='3',
        status=LiveOrderStatus.OPEN.value,
        broker_order_id='90001',
        submitted_at='2026-04-18T00:00:00+00:00',
    )
    repo.upsert(record)
    broker = SimpleNamespace(
        cancel_order=lambda request: OrderCancelResult(
            broker_order_id=request.broker_order_id,
            accepted=True,
            message='accepted',
            result_code='0',
        )
    )
    live_loop = SimpleNamespace(
        services=SimpleNamespace(
            broker_simulator=broker,
            logger=SimpleNamespace(emit=lambda *args, **kwargs: None),
        )
    )
    request = _make_request(controller, live_loop=live_loop)
    request.app.state.live_order_repository = repo

    listing = await dashboard_routes.get_live_orders(request)
    response = await dashboard_routes.cancel_live_order(record.record_id, request, live_loop)

    assert listing.total == 1
    assert listing.orders[0].broker_order_id == '90001'
    assert response.broker_cancel_accepted is True
    assert response.order.status == LiveOrderStatus.CANCEL_REQUESTED.value
