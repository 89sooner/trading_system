from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from trading_system.app.live_runtime_controller import LiveRuntimeController
from trading_system.app.live_runtime_history import LiveRuntimeSessionRecord
from trading_system.app.services import PreflightCheckResult
from trading_system.app.settings import (
    AppMode,
    AppSettings,
    BacktestSettings,
    LiveExecutionMode,
    RiskSettings,
)
from trading_system.app.state import AppRunnerState


class _FakeLoop:
    def __init__(self) -> None:
        self.state = AppRunnerState.INIT
        self.services = SimpleNamespace(logger=SimpleNamespace(emit=lambda *args, **kwargs: None))

    def run(self) -> None:
        self.state = AppRunnerState.RUNNING
        while self.state != AppRunnerState.STOPPED:
            time.sleep(0.01)


class _FakeServices:
    def __init__(self, loop: _FakeLoop) -> None:
        self._loop = loop

    def build_live_loop(self, session_id: str | None = None) -> _FakeLoop:
        return self._loop


class _HistoryRepo:
    def __init__(self) -> None:
        self.records: list[LiveRuntimeSessionRecord] = []

    def save(self, record: LiveRuntimeSessionRecord) -> None:
        self.records.append(record)

    def get(self, session_id: str):
        for record in reversed(self.records):
            if record.session_id == session_id:
                return record
        return None

    def list(self, limit: int = 20):
        return list(reversed(self.records))[:limit]


def _make_settings() -> AppSettings:
    return AppSettings(
        mode=AppMode.LIVE,
        symbols=("BTCUSDT",),
        provider="mock",
        broker="paper",
        live_execution=LiveExecutionMode.PAPER,
        risk=RiskSettings(max_position=1, max_notional=100000, max_order_size=0.25),
        backtest=BacktestSettings(starting_cash=10000, fee_bps=5, trade_quantity=0.1),
    )


def test_controller_starts_and_stops_single_session() -> None:
    attached: list[object | None] = []
    loop = _FakeLoop()
    controller = LiveRuntimeController(
        services_builder=lambda settings: _FakeServices(loop),
        attach_loop=lambda current: attached.append(current),
    )

    session = controller.start(_make_settings())

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if controller.snapshot().controller_state == 'active':
            break
        time.sleep(0.01)
    else:
        raise AssertionError('controller did not enter active state')

    assert session.live_execution == 'paper'
    assert controller.has_active_session() is True
    assert attached[-1] is loop

    controller.stop(timeout=1.0)

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if controller.has_active_session() is False:
            break
        time.sleep(0.01)
    else:
        raise AssertionError('controller did not stop session')

    assert attached[-1] is None


def test_controller_rejects_duplicate_start() -> None:
    loop = _FakeLoop()
    controller = LiveRuntimeController(
        services_builder=lambda settings: _FakeServices(loop),
        attach_loop=lambda current: None,
    )
    controller.start(_make_settings())
    try:
        with pytest.raises(RuntimeError, match='already active'):
            controller.start(_make_settings())
    finally:
        controller.stop(timeout=1.0)


def test_controller_stop_without_session_raises() -> None:
    controller = LiveRuntimeController(
        services_builder=lambda settings: _FakeServices(_FakeLoop()),
        attach_loop=lambda current: None,
    )

    with pytest.raises(RuntimeError, match='No live runtime session'):
        controller.stop()


def test_controller_records_start_failure() -> None:
    controller = LiveRuntimeController(
        services_builder=lambda settings: (_ for _ in ()).throw(RuntimeError('boom')),
        attach_loop=lambda current: None,
    )

    with pytest.raises(RuntimeError, match='boom'):
        controller.start(_make_settings())

    assert controller.snapshot().controller_state == 'error'
    assert controller.snapshot().last_error == 'boom'


def test_controller_persists_session_history_with_matching_preflight() -> None:
    history = _HistoryRepo()
    loop = _FakeLoop()
    controller = LiveRuntimeController(
        services_builder=lambda settings: _FakeServices(loop),
        attach_loop=lambda current: None,
        history_repository=history,
    )
    settings = _make_settings()
    controller.record_preflight(
        settings,
        PreflightCheckResult(
            ready=True,
            reasons=[],
            quote_summary=None,
            quote_summaries=None,
            symbol_count=1,
            message='ok',
            next_allowed_actions=['paper'],
            checked_at='2026-04-19T00:00:00Z',
        ),
    )

    session = controller.start(settings)
    controller.stop(timeout=1.0)

    saved = history.get(session.session_id)
    assert saved is not None
    assert saved.preflight_summary is not None
    assert saved.preflight_summary['message'] == 'ok'
    assert saved.last_state == 'stopped'
