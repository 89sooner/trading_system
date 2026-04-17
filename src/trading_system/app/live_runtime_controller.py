from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from trading_system.app.loop import LiveTradingLoop
from trading_system.app.settings import AppSettings
from trading_system.app.state import AppRunnerState
from trading_system.core.compat import UTC

if TYPE_CHECKING:
    from trading_system.app.services import AppServices


@dataclass(slots=True, frozen=True)
class LiveRuntimeSession:
    session_id: str
    live_execution: str
    provider: str
    broker: str
    symbols: list[str]
    started_at: str


@dataclass(slots=True, frozen=True)
class LiveRuntimeControllerSnapshot:
    controller_state: str
    active: bool
    session_id: str | None = None
    live_execution: str | None = None
    provider: str | None = None
    broker: str | None = None
    symbols: list[str] | None = None
    started_at: str | None = None
    last_error: str | None = None


class LiveRuntimeController:
    def __init__(
        self,
        *,
        services_builder: Callable[[AppSettings], 'AppServices'],
        attach_loop: Callable[[LiveTradingLoop | None], None],
    ) -> None:
        self._services_builder = services_builder
        self._attach_loop = attach_loop
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._active_loop: LiveTradingLoop | None = None
        self._active_session: LiveRuntimeSession | None = None
        self._last_error: str | None = None

    def snapshot(self) -> LiveRuntimeControllerSnapshot:
        with self._lock:
            thread = self._thread
            loop = self._active_loop
            session = self._active_session
            last_error = self._last_error

        if session is not None and thread is not None and thread.is_alive():
            return LiveRuntimeControllerSnapshot(
                controller_state='active' if loop is not None else 'starting',
                active=loop is not None,
                session_id=session.session_id,
                live_execution=session.live_execution,
                provider=session.provider,
                broker=session.broker,
                symbols=session.symbols,
                started_at=session.started_at,
                last_error=last_error,
            )

        if last_error is not None:
            return LiveRuntimeControllerSnapshot(
                controller_state='error',
                active=False,
                last_error=last_error,
            )

        return LiveRuntimeControllerSnapshot(controller_state='idle', active=False)

    def has_active_session(self) -> bool:
        with self._lock:
            return (
                self._active_session is not None
                and self._thread is not None
                and self._thread.is_alive()
            )

    def start(self, settings: AppSettings) -> LiveRuntimeSession:
        with self._lock:
            if (
                self._active_session is not None
                and self._thread is not None
                and self._thread.is_alive()
            ):
                raise RuntimeError('A live runtime session is already active.')

            session = LiveRuntimeSession(
                session_id=datetime.now(UTC).strftime('live_%Y%m%d_%H%M%S'),
                live_execution=settings.live_execution.value,
                provider=settings.provider,
                broker=settings.broker,
                symbols=list(settings.symbols),
                started_at=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            )
            started = threading.Event()
            self._last_error = None
            thread = threading.Thread(
                target=self._run_session,
                name=f'live-runtime-{session.session_id}',
                daemon=True,
                args=(settings, session, started),
            )
            self._active_session = session
            self._thread = thread
            thread.start()

        started.wait(timeout=2.0)
        snapshot = self.snapshot()
        if snapshot.controller_state == 'error':
            raise RuntimeError(snapshot.last_error or 'Live runtime failed to start.')
        return session

    def stop(self, timeout: float = 5.0, requested_by: str = 'controller') -> None:
        with self._lock:
            loop = self._active_loop
            thread = self._thread
            session = self._active_session

        if session is None or thread is None:
            raise RuntimeError('No live runtime session is active.')
        if loop is None:
            raise RuntimeError('Live runtime session is still starting.')

        loop.services.logger.emit(
            'system.control',
            severity=30,
            payload={'action': 'stop', 'requested_by': requested_by},
        )
        loop.state = AppRunnerState.STOPPED
        thread.join(timeout=timeout)
        if thread.is_alive():
            with self._lock:
                self._last_error = 'Timed out waiting for live runtime to stop.'
            raise RuntimeError('Timed out waiting for live runtime to stop.')

    def _run_session(
        self,
        settings: AppSettings,
        session: LiveRuntimeSession,
        started: threading.Event,
    ) -> None:
        try:
            services = self._services_builder(settings)
            loop = services.build_live_loop(session_id=session.session_id)
            with self._lock:
                self._active_loop = loop
            self._attach_loop(loop)
            started.set()
            loop.run()
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
            started.set()
        finally:
            self._attach_loop(None)
            with self._lock:
                self._active_loop = None
                self._active_session = None
                self._thread = None
