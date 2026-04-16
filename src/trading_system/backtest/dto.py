from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_system.analytics.view_models import EventViewModel, build_backtest_analytics_view_model
from trading_system.backtest.engine import BacktestResult
from trading_system.core.compat import UTC


@dataclass(slots=True, frozen=True)
class SummaryDTO:
    return_value: str
    max_drawdown: str
    volatility: str
    win_rate: str


@dataclass(slots=True, frozen=True)
class EquityPointDTO:
    timestamp: str
    equity: str


@dataclass(slots=True, frozen=True)
class DrawdownPointDTO:
    timestamp: str
    drawdown: str


@dataclass(slots=True, frozen=True)
class EventDTO:
    event: str
    payload: dict[str, str]


@dataclass(slots=True, frozen=True)
class BacktestResultDTO:
    summary: SummaryDTO
    equity_curve: list[EquityPointDTO]
    drawdown_curve: list[DrawdownPointDTO]
    signals: list[EventDTO]
    orders: list[EventDTO]
    risk_rejections: list[EventDTO]

    @classmethod
    def from_result(cls, result: BacktestResult) -> "BacktestResultDTO":
        analytics = build_backtest_analytics_view_model(
            timestamps=result.equity_timestamps,
            equity_curve=result.equity_curve,
            orders=[_event_to_view_model(event) for event in result.orders],
            risk_rejections=[_event_to_view_model(event) for event in result.risk_rejections],
        )
        return cls(
            summary=SummaryDTO(
                return_value=_decimal_to_json(analytics.summary.return_value),
                max_drawdown=_decimal_to_json(analytics.summary.max_drawdown),
                volatility=_decimal_to_json(analytics.summary.volatility),
                win_rate=_decimal_to_json(analytics.summary.win_rate),
            ),
            equity_curve=[
                EquityPointDTO(timestamp=point.timestamp, equity=_decimal_to_json(point.equity))
                for point in analytics.equity_curve
            ],
            drawdown_curve=[
                DrawdownPointDTO(
                    timestamp=point.timestamp,
                    drawdown=_decimal_to_json(point.drawdown),
                )
                for point in analytics.drawdown_curve
            ],
            signals=[_event_to_dto(_event_to_view_model(event)) for event in result.signal_events],
            orders=[_event_to_dto(event) for event in analytics.orders],
            risk_rejections=[_event_to_dto(event) for event in analytics.risk_rejections],
        )


@dataclass(slots=True, frozen=True)
class BacktestRunDTO:
    run_id: str
    status: str
    started_at: str
    finished_at: str | None
    input_symbols: list[str]
    mode: str
    result: BacktestResultDTO | None = None
    error: str | None = None

    @classmethod
    def queued(
        cls,
        *,
        run_id: str,
        started_at: datetime | str,
        input_symbols: tuple[str, ...] | list[str],
        mode: str,
    ) -> "BacktestRunDTO":
        return cls(
            run_id=run_id,
            status="queued",
            started_at=_timestamp_to_json(started_at),
            finished_at=None,
            input_symbols=list(input_symbols),
            mode=mode,
        )

    @classmethod
    def running(
        cls,
        *,
        run_id: str,
        started_at: datetime | str,
        input_symbols: tuple[str, ...] | list[str],
        mode: str,
    ) -> "BacktestRunDTO":
        return cls(
            run_id=run_id,
            status="running",
            started_at=_timestamp_to_json(started_at),
            finished_at=None,
            input_symbols=list(input_symbols),
            mode=mode,
        )

    @classmethod
    def succeeded(
        cls,
        *,
        run_id: str,
        started_at: datetime | str,
        finished_at: datetime | str,
        input_symbols: tuple[str, ...] | list[str],
        mode: str,
        result: BacktestResult,
    ) -> "BacktestRunDTO":
        return cls(
            run_id=run_id,
            status="succeeded",
            started_at=_timestamp_to_json(started_at),
            finished_at=_timestamp_to_json(finished_at),
            input_symbols=list(input_symbols),
            mode=mode,
            result=BacktestResultDTO.from_result(result),
        )

    @classmethod
    def failed(
        cls,
        *,
        run_id: str,
        started_at: datetime | str,
        finished_at: datetime | str,
        input_symbols: tuple[str, ...] | list[str],
        mode: str,
        error: str,
    ) -> "BacktestRunDTO":
        return cls(
            run_id=run_id,
            status="failed",
            started_at=_timestamp_to_json(started_at),
            finished_at=_timestamp_to_json(finished_at),
            input_symbols=list(input_symbols),
            mode=mode,
            error=error,
        )


def _decimal_to_json(value: Decimal) -> str:
    return format(value, "f")


def _event_to_view_model(event: dict[str, object]) -> EventViewModel:
    raw_payload = event.get("payload", {})
    if not isinstance(raw_payload, Mapping):
        raw_payload = {}
    return EventViewModel(
        event=str(event["event"]),
        payload={str(key): value for key, value in raw_payload.items()},
    )


def _event_to_dto(event: EventViewModel) -> EventDTO:
    return EventDTO(
        event=event.event,
        payload={key: _value_to_json(value) for key, value in event.payload.items()},
    )


def _value_to_json(value: object) -> str:
    if isinstance(value, Decimal):
        return _decimal_to_json(value)
    return str(value)


def _datetime_to_json(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.isoformat().replace("+00:00", "Z")


def _timestamp_to_json(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return _datetime_to_json(value)
    return value
