"""Dashboard API routes — live loop status, positions, event feed, control."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from trading_system.api.schemas import (
    ControlActionDTO,
    ControlResponseDTO,
    DashboardIncidentDTO,
    DashboardStatusDTO,
    EquityPointTimeseriesDTO,
    EquityTimeseriesDTO,
    EventFeedDTO,
    EventRecordDTO,
    LastPreflightDTO,
    PositionDTO,
    PositionsResponseDTO,
)
from trading_system.app.state import AppRunnerState
from trading_system.core.compat import UTC
from trading_system.integrations.kis import is_krx_market_open

if TYPE_CHECKING:
    from trading_system.app.live_runtime_controller import LiveRuntimeController
    from trading_system.app.loop import LiveTradingLoop

_MAX_SSE_CONNECTIONS = 10
_active_sse_connections = 0

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_loop(request: Request) -> "LiveTradingLoop | None":
    return getattr(request.app.state, "live_loop", None)


def _get_controller(request: Request) -> "LiveRuntimeController | None":
    return getattr(request.app.state, "live_runtime_controller", None)


def _require_loop(request: Request) -> "LiveTradingLoop":
    loop = _get_loop(request)
    if loop is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No live trading loop is running.",
        )
    return loop


LoopDep = Annotated["LiveTradingLoop", Depends(_require_loop)]
OptionalLoopDep = Annotated["LiveTradingLoop | None", Depends(_get_loop)]


def _latest_incident(
    loop: "LiveTradingLoop | None",
    last_error: str | None,
) -> DashboardIncidentDTO | None:
    if loop is None:
        if last_error is None:
            return None
        return DashboardIncidentDTO(
            event="controller.error",
            severity="ERROR",
            timestamp=datetime.now(UTC).isoformat(),
            summary=last_error,
        )

    records = loop.services.logger.recent_events(limit=100)
    for record in reversed(records):
        severity = record.severity.upper()
        if (
            severity in {"WARNING", "ERROR", "CRITICAL"}
            or record.event.startswith("risk.")
            or record.event.startswith("portfolio.reconciliation.")
            or record.event.startswith("system.error")
        ):
            summary = record.event
            for key in ("reason", "error", "action", "state"):
                value = record.payload.get(key)
                if value not in (None, ""):
                    summary = str(value)
                    break
            return DashboardIncidentDTO(
                event=record.event,
                severity=severity,
                timestamp=record.timestamp,
                summary=summary,
            )
    return None


def _controller_state_detail(state: str | None, active: bool) -> str | None:
    if state is None:
        return None
    if state == "active":
        return (
            "Runtime session is attached and processing ticks."
            if active
            else "Runtime thread is active."
        )
    if state == "starting":
        return "Runtime thread started and is waiting for the live loop to attach."
    if state == "error":
        return "Runtime controller recorded a startup or shutdown error."
    if state == "idle":
        return "No runtime session is currently attached to this API process."
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status", response_model=DashboardStatusDTO)
async def get_status(request: Request, loop: OptionalLoopDep) -> DashboardStatusDTO:
    """Return the current state and heartbeat of the live trading loop."""
    controller = _get_controller(request)
    snapshot = controller.snapshot() if controller is not None else None
    last_preflight = (
        LastPreflightDTO(
            checked_at=snapshot.last_preflight.checked_at,
            ready=snapshot.last_preflight.ready,
            message=snapshot.last_preflight.message,
            provider=snapshot.last_preflight.provider,
            broker=snapshot.last_preflight.broker,
            symbols=snapshot.last_preflight.symbols,
            blocking_reasons=snapshot.last_preflight.blocking_reasons,
            warnings=snapshot.last_preflight.warnings,
            next_allowed_actions=snapshot.last_preflight.next_allowed_actions,
        )
        if snapshot is not None and snapshot.last_preflight is not None
        else None
    )
    if loop is None:
        return DashboardStatusDTO(
            state=AppRunnerState.STOPPED.value,
            last_heartbeat=None,
            uptime_seconds=None,
            controller_state=snapshot.controller_state if snapshot is not None else "idle",
            controller_state_detail=_controller_state_detail(
                snapshot.controller_state if snapshot is not None else "idle",
                False,
            ),
            active=snapshot.active if snapshot is not None else False,
            session_id=snapshot.session_id if snapshot is not None else None,
            live_execution=snapshot.live_execution if snapshot is not None else None,
            last_error=snapshot.last_error if snapshot is not None else None,
            provider=snapshot.provider if snapshot is not None else None,
            broker=snapshot.broker if snapshot is not None else None,
            symbols=snapshot.symbols if snapshot is not None else None,
            stop_supported=snapshot.stop_supported if snapshot is not None else False,
            last_preflight=last_preflight,
            latest_incident=_latest_incident(
                None,
                snapshot.last_error if snapshot is not None else None,
            ),
        )

    started_at = getattr(loop, "_started_at", None)
    uptime = (
        (datetime.now(UTC) - started_at).total_seconds()
        if started_at is not None
        else None
    )
    last_hb = loop._last_heartbeat  # noqa: SLF001
    runtime = getattr(loop, "runtime", None)
    recon_at = getattr(runtime, "last_reconciliation_at", None) if runtime else None
    recon_status = getattr(runtime, "last_reconciliation_status", None) if runtime else None
    services = getattr(loop, "services", None)
    provider = getattr(services, "provider", None) if services else None
    broker = getattr(services, "broker", None) if services else None
    symbols = list(getattr(services, "symbols", ())) if services else None

    market_session: str | None = None
    if provider == "kis":
        market_session = "open" if is_krx_market_open() else "closed"

    return DashboardStatusDTO(
        state=loop.state.value,
        last_heartbeat=last_hb.isoformat() if last_hb is not None else None,
        uptime_seconds=uptime,
        controller_state=snapshot.controller_state if snapshot is not None else None,
        controller_state_detail=_controller_state_detail(
            snapshot.controller_state if snapshot is not None else "active",
            True,
        ),
        active=True,
        session_id=snapshot.session_id if snapshot is not None else None,
        live_execution=snapshot.live_execution if snapshot is not None else None,
        last_error=snapshot.last_error if snapshot is not None else None,
        provider=provider,
        broker=broker,
        symbols=symbols if symbols else None,
        market_session=market_session,
        last_reconciliation_at=recon_at.isoformat() if recon_at is not None else None,
        last_reconciliation_status=recon_status,
        stop_supported=snapshot.stop_supported if snapshot is not None else True,
        last_preflight=last_preflight,
        latest_incident=_latest_incident(
            loop,
            snapshot.last_error if snapshot is not None else None,
        ),
    )


@router.get("/positions", response_model=PositionsResponseDTO)
async def get_positions(loop: LoopDep) -> PositionsResponseDTO:
    """Return active positions and cash from the portfolio book."""
    book = loop.services.portfolio
    marks = getattr(loop.runtime, "last_marks", {})
    unrealized = book.unrealized_pnl(marks)
    dtos: list[PositionDTO] = []
    for symbol, qty in book.positions.items():
        avg_cost = book.average_costs.get(symbol, ZERO)
        dtos.append(
            PositionDTO(
                symbol=symbol,
                quantity=str(qty),
                average_cost=str(avg_cost),
                unrealized_pnl=str(unrealized[symbol]) if symbol in unrealized else None,
            )
        )
    return PositionsResponseDTO(positions=dtos, cash=str(book.cash))


@router.get("/events", response_model=EventFeedDTO)
async def get_events(
    loop: LoopDep,
    limit: int = 50,
) -> EventFeedDTO:
    """Return the last *limit* events from the in-memory ring buffer."""
    limit = max(1, min(limit, 500))
    records = loop.services.logger.recent_events(limit=limit)
    dtos = [
        EventRecordDTO(
            event=r.event,
            severity=r.severity,
            correlation_id=r.correlation_id,
            timestamp=r.timestamp,
            payload=r.payload,
        )
        for r in records
    ]
    return EventFeedDTO(events=dtos, total=len(dtos))


@router.post("/control", response_model=ControlResponseDTO, status_code=status.HTTP_200_OK)
async def control_loop(
    body: ControlActionDTO,
    request: Request,
    loop: OptionalLoopDep,
) -> ControlResponseDTO:
    """Pause, resume, reset, or stop the live trading loop."""
    controller = _get_controller(request)

    if body.action == "stop":
        if controller is not None and controller.has_active_session():
            controller.stop(requested_by="api")
            return ControlResponseDTO(status="ok", state=AppRunnerState.STOPPED.value)
        if loop is not None:
            loop.services.logger.emit(
                "system.control",
                severity=30,
                payload={"action": "stop", "requested_by": "api"},
            )
            loop.state = AppRunnerState.STOPPED
            return ControlResponseDTO(status="ok", state=AppRunnerState.STOPPED.value)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No live runtime session is active.",
        )

    if loop is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No live trading loop is running.",
        )

    if body.action == "pause":
        if loop.state == AppRunnerState.RUNNING:
            loop.state = AppRunnerState.PAUSED
            loop.services.logger.emit(
                "system.control",
                severity=30,
                payload={"action": "pause", "requested_by": "api"},
            )
    elif body.action == "resume":
        if loop.state == AppRunnerState.PAUSED:
            loop.state = AppRunnerState.RUNNING
            loop.services.logger.emit(
                "system.control",
                severity=20,
                payload={"action": "resume", "requested_by": "api"},
            )
    elif body.action == "reset":
        if loop.state == AppRunnerState.EMERGENCY:
            loop.state = AppRunnerState.PAUSED
            loop.services.logger.emit(
                "system.control",
                severity=30,
                payload={"action": "reset", "requested_by": "api"},
            )
    return ControlResponseDTO(status="ok", state=loop.state.value)


@router.get("/equity", response_model=EquityTimeseriesDTO)
async def get_equity(loop: LoopDep, limit: int = 300) -> EquityTimeseriesDTO:
    """Return server-side equity timeseries from JSONL file."""
    limit = max(1, min(limit, 1000))
    equity_writer = getattr(loop, "equity_writer", None)
    if equity_writer is None:
        return EquityTimeseriesDTO(session_id="", points=[], total=0)
    points_data = equity_writer.read_recent(limit)
    points = [
        EquityPointTimeseriesDTO(
            timestamp=p["timestamp"],
            equity=p["equity"],
            cash=p["cash"],
            positions_value=p["positions_value"],
        )
        for p in points_data
    ]
    return EquityTimeseriesDTO(
        session_id=equity_writer.session_id,
        points=points,
        total=len(points),
    )


@router.get("/stream")
async def stream_events(request: Request):
    """SSE endpoint — real-time event stream for the dashboard.

    Authentication is handled by the security middleware, which accepts the
    ``api_key`` query parameter for this path so that browser EventSource
    clients (which cannot set custom headers) can connect.
    """
    global _active_sse_connections  # noqa: PLW0603

    # Connection limit
    if _active_sse_connections >= _MAX_SSE_CONNECTIONS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many SSE connections."},
        )

    from sse_starlette.sse import EventSourceResponse

    live_loop = _get_loop(request)
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    def on_event(record) -> None:
        try:
            queue.put_nowait(record)
        except asyncio.QueueFull:
            pass

    if live_loop is not None:
        live_loop.services.logger.subscribe(on_event)

    _active_sse_connections += 1

    async def generator():
        global _active_sse_connections  # noqa: PLW0603
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    record = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_name = record.event
                    if event_name.startswith("sse."):
                        sse_type = event_name[4:]
                    else:
                        sse_type = "event"
                    yield {
                        "event": sse_type,
                        "data": json.dumps(
                            {"event": record.event, "payload": record.payload},
                            default=str,
                        ),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "{}"}
        finally:
            if live_loop is not None:
                live_loop.services.logger.unsubscribe(on_event)
            _active_sse_connections -= 1

    return EventSourceResponse(generator())
