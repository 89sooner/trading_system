"""Dashboard API routes — live loop status, positions, event feed, control."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from trading_system.api.schemas import (
    ControlActionDTO,
    ControlResponseDTO,
    DashboardStatusDTO,
    EventFeedDTO,
    EventRecordDTO,
    PositionDTO,
    PositionsResponseDTO,
)
from trading_system.app.state import AppRunnerState
from trading_system.core.compat import UTC

if TYPE_CHECKING:
    from trading_system.app.loop import LiveTradingLoop

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_loop(request: Request) -> "LiveTradingLoop | None":
    return getattr(request.app.state, "live_loop", None)


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status", response_model=DashboardStatusDTO)
async def get_status(loop: LoopDep) -> DashboardStatusDTO:
    """Return the current state and heartbeat of the live trading loop."""
    started_at = getattr(loop, "_started_at", None)
    uptime = (
        (datetime.now(UTC) - started_at).total_seconds()
        if started_at is not None
        else None
    )
    last_hb = loop._last_heartbeat  # noqa: SLF001
    return DashboardStatusDTO(
        state=loop.state.value,
        last_heartbeat=last_hb.isoformat() if last_hb is not None else None,
        uptime_seconds=uptime,
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
async def control_loop(body: ControlActionDTO, loop: LoopDep) -> ControlResponseDTO:
    """Pause, resume, or reset the live trading loop."""
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
