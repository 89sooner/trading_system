from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_system.backtest.engine import BacktestResult


@dataclass(slots=True, frozen=True)
class BacktestResultDTO:
    processed_bars: int
    executed_trades: int
    rejected_signals: int
    cash: str
    positions: dict[str, str]
    total_return: str
    equity_curve: list[str]

    @classmethod
    def from_result(cls, result: BacktestResult) -> "BacktestResultDTO":
        return cls(
            processed_bars=result.processed_bars,
            executed_trades=result.executed_trades,
            rejected_signals=result.rejected_signals,
            cash=_decimal_to_json(result.final_portfolio.cash),
            positions={
                symbol: _decimal_to_json(quantity)
                for symbol, quantity in result.final_portfolio.positions.items()
            },
            total_return=_decimal_to_json(result.total_return),
            equity_curve=[_decimal_to_json(point) for point in result.equity_curve],
        )


@dataclass(slots=True, frozen=True)
class BacktestRunDTO:
    run_id: str
    status: str
    started_at: str
    finished_at: str
    input_symbols: list[str]
    mode: str
    result: BacktestResultDTO | None = None
    error: str | None = None

    @classmethod
    def succeeded(
        cls,
        *,
        run_id: str,
        started_at: datetime,
        finished_at: datetime,
        input_symbols: tuple[str, ...],
        mode: str,
        result: BacktestResult,
    ) -> "BacktestRunDTO":
        return cls(
            run_id=run_id,
            status="succeeded",
            started_at=_datetime_to_json(started_at),
            finished_at=_datetime_to_json(finished_at),
            input_symbols=list(input_symbols),
            mode=mode,
            result=BacktestResultDTO.from_result(result),
        )


def _decimal_to_json(value: Decimal) -> str:
    return format(value, "f")


def _datetime_to_json(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.isoformat().replace("+00:00", "Z")
