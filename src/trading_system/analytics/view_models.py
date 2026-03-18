from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_system.analytics.metrics import drawdown_series, performance_metrics


@dataclass(slots=True, frozen=True)
class SummaryViewModel:
    return_value: Decimal
    max_drawdown: Decimal
    volatility: Decimal
    win_rate: Decimal


@dataclass(slots=True, frozen=True)
class EquityPointViewModel:
    timestamp: str
    equity: Decimal


@dataclass(slots=True, frozen=True)
class DrawdownPointViewModel:
    timestamp: str
    drawdown: Decimal


@dataclass(slots=True, frozen=True)
class EventViewModel:
    event: str
    payload: dict[str, Decimal | str]


@dataclass(slots=True, frozen=True)
class BacktestAnalyticsViewModel:
    summary: SummaryViewModel
    equity_curve: list[EquityPointViewModel]
    drawdown_curve: list[DrawdownPointViewModel]
    orders: list[EventViewModel]
    risk_rejections: list[EventViewModel]


def build_backtest_analytics_view_model(
    *,
    timestamps: list[datetime],
    equity_curve: list[Decimal],
    orders: list[EventViewModel],
    risk_rejections: list[EventViewModel],
) -> BacktestAnalyticsViewModel:
    metrics = performance_metrics(equity_curve)
    drawdowns = drawdown_series(equity_curve)
    equity_points = [
        EquityPointViewModel(timestamp=_to_iso8601(timestamp), equity=equity)
        for timestamp, equity in zip(timestamps, equity_curve, strict=True)
    ]
    drawdown_points = [
        DrawdownPointViewModel(timestamp=point.timestamp, drawdown=drawdown)
        for point, drawdown in zip(equity_points, drawdowns, strict=True)
    ]
    return BacktestAnalyticsViewModel(
        summary=SummaryViewModel(
            return_value=metrics.cumulative_return,
            max_drawdown=metrics.max_drawdown,
            volatility=metrics.volatility,
            win_rate=metrics.win_rate,
        ),
        equity_curve=equity_points,
        drawdown_curve=drawdown_points,
        orders=orders,
        risk_rejections=risk_rejections,
    )


def _to_iso8601(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.isoformat().replace("+00:00", "Z")
