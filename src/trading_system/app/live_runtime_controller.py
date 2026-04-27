from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from trading_system.app.live_runtime_events import (
    LiveRuntimeEventRepository,
    runtime_event_from_log,
    should_archive_runtime_event,
)
from trading_system.app.live_runtime_history import (
    LiveRuntimeSessionRecord,
    LiveRuntimeSessionRepository,
)
from trading_system.app.loop import LiveTradingLoop
from trading_system.app.settings import AppSettings
from trading_system.app.state import AppRunnerState
from trading_system.core.compat import UTC

if TYPE_CHECKING:
    from trading_system.app.services import AppServices, PreflightCheckResult

_log = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class LiveRuntimeSession:
    session_id: str
    live_execution: str
    provider: str
    broker: str
    symbols: list[str]
    started_at: str
    preflight_summary: dict[str, object] | None = None


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
    stop_supported: bool = False
    last_preflight: 'LiveRuntimePreflightSnapshot | None' = None


@dataclass(slots=True, frozen=True)
class LiveRuntimePreflightSnapshot:
    checked_at: str
    ready: bool
    message: str
    provider: str
    broker: str
    symbols: list[str]
    blocking_reasons: list[str]
    warnings: list[str]
    next_allowed_actions: list[str]


class LiveRuntimeController:
    def __init__(
        self,
        *,
        services_builder: Callable[[AppSettings], 'AppServices'],
        attach_loop: Callable[[LiveTradingLoop | None], None],
        history_repository: LiveRuntimeSessionRepository | None = None,
        event_repository: LiveRuntimeEventRepository | None = None,
    ) -> None:
        self._services_builder = services_builder
        self._attach_loop = attach_loop
        self._history_repository = history_repository
        self._event_repository = event_repository
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._active_loop: LiveTradingLoop | None = None
        self._active_session: LiveRuntimeSession | None = None
        self._last_error: str | None = None
        self._last_preflight: LiveRuntimePreflightSnapshot | None = None

    def snapshot(self) -> LiveRuntimeControllerSnapshot:
        with self._lock:
            thread = self._thread
            loop = self._active_loop
            session = self._active_session
            last_error = self._last_error
            last_preflight = self._last_preflight

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
                stop_supported=loop is not None,
                last_preflight=last_preflight,
            )

        if last_error is not None:
            return LiveRuntimeControllerSnapshot(
                controller_state='error',
                active=False,
                last_error=last_error,
                stop_supported=False,
                last_preflight=last_preflight,
            )

        return LiveRuntimeControllerSnapshot(
            controller_state='idle',
            active=False,
            stop_supported=False,
            last_preflight=last_preflight,
        )

    def record_preflight(self, settings: AppSettings, result: 'PreflightCheckResult') -> None:
        with self._lock:
            self._last_preflight = LiveRuntimePreflightSnapshot(
                checked_at=result.checked_at or datetime.now(UTC).isoformat(),
                ready=result.ready,
                message=result.message,
                provider=settings.provider,
                broker=settings.broker,
                symbols=list(settings.symbols),
                blocking_reasons=list(result.blocking_reasons),
                warnings=list(result.warnings),
                next_allowed_actions=list(result.next_allowed_actions),
            )

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
                preflight_summary=self._preflight_payload(settings),
            )
            started = threading.Event()
            self._last_error = None
            self._persist_session(
                session,
                last_state='starting',
                ended_at=None,
                last_error=None,
            )
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
        final_state = 'stopped'
        last_error: str | None = None
        event_callback = None
        event_logger = None
        try:
            services = self._services_builder(settings)
            if settings.live_execution.value == 'live':
                services.validate_live_execution_guards()
            loop = services.build_live_loop(session_id=session.session_id)
            if self._event_repository is not None:
                event_logger = loop.services.logger

                def archive_event(record) -> None:
                    if not should_archive_runtime_event(record):
                        return
                    try:
                        self._event_repository.append(
                            runtime_event_from_log(
                                session_id=session.session_id,
                                record=record,
                            )
                        )
                    except Exception:
                        _log.warning(
                            "Failed to archive live runtime event for session %s",
                            session.session_id,
                            exc_info=True,
                        )

                event_callback = archive_event
                event_logger.subscribe(event_callback)
            with self._lock:
                self._active_loop = loop
            self._attach_loop(loop)
            started.set()
            loop.run()
            final_state = loop.state.value
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
            final_state = 'error'
            last_error = str(exc)
            started.set()
        finally:
            if event_logger is not None and event_callback is not None:
                event_logger.unsubscribe(event_callback)
            self._attach_loop(None)
            self._persist_session(
                session,
                last_state=final_state,
                ended_at=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
                last_error=last_error,
            )
            with self._lock:
                self._active_loop = None
                self._active_session = None
                self._thread = None

    def _preflight_payload(self, settings: AppSettings) -> dict[str, object] | None:
        snapshot = self._last_preflight
        if snapshot is None:
            return None
        if (
            snapshot.provider != settings.provider
            or snapshot.broker != settings.broker
            or snapshot.symbols != list(settings.symbols)
        ):
            return None
        return {
            'checked_at': snapshot.checked_at,
            'ready': snapshot.ready,
            'message': snapshot.message,
            'blocking_reasons': list(snapshot.blocking_reasons),
            'warnings': list(snapshot.warnings),
            'next_allowed_actions': list(snapshot.next_allowed_actions),
        }

    def _persist_session(
        self,
        session: LiveRuntimeSession,
        *,
        last_state: str,
        ended_at: str | None,
        last_error: str | None,
    ) -> None:
        if self._history_repository is None:
            return
        self._history_repository.save(
            LiveRuntimeSessionRecord(
                session_id=session.session_id,
                started_at=session.started_at,
                ended_at=ended_at,
                provider=session.provider,
                broker=session.broker,
                live_execution=session.live_execution,
                symbols=list(session.symbols),
                last_state=last_state,
                last_error=last_error,
                preflight_summary=session.preflight_summary,
            )
        )
