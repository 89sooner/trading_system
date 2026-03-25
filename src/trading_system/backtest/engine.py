from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from trading_system.analytics.metrics import cumulative_return
from trading_system.core.types import MarketBar
from trading_system.execution.step import TradingContext as BacktestContext
from trading_system.execution.step import execute_trading_step
from trading_system.portfolio.book import PortfolioBook
from trading_system.strategy.base import Strategy


@dataclass(slots=True)
class BacktestResult:
    final_portfolio: PortfolioBook
    equity_timestamps: list[datetime]
    equity_curve: list[Decimal]
    processed_bars: int
    executed_trades: int
    rejected_signals: int
    signal_events: list[dict[str, Any]]
    orders: list[dict[str, Any]]
    risk_rejections: list[dict[str, Any]]

    @property
    def total_return(self) -> Decimal:
        return cumulative_return(self.equity_curve)


def run_backtest(
    bars: Iterable[MarketBar],
    strategy: Strategy,
    context: BacktestContext,
    *,
    strategy_by_symbol: dict[str, Strategy] | None = None,
) -> BacktestResult:
    equity_timestamps: list[datetime] = []
    equity_curve: list[Decimal] = []
    processed_bars = 0
    executed_trades = 0
    rejected_signals = 0
    last_prices: dict[str, Decimal] = {}
    signal_events: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    risk_rejections: list[dict[str, Any]] = []

    for bar in bars:
        processed_bars += 1
        active_strategy = (
            strategy_by_symbol.get(bar.symbol, strategy)
            if strategy_by_symbol
            else strategy
        )
        events = execute_trading_step(bar, active_strategy, context)
        
        if events.signal:
            _record_event(signal_events, "strategy.signal", events.signal)
        if events.order_created:
            _record_event(orders, "order.created", events.order_created)
        if events.order_filled:
            executed_trades += 1
            _record_event(orders, "order.filled", events.order_filled)
        if events.order_rejected:
            _record_event(orders, "order.rejected", events.order_rejected)
        if events.risk_rejected:
            rejected_signals += 1
            _record_event(risk_rejections, "risk.rejected", events.risk_rejected)

        last_prices[bar.symbol] = bar.close
        equity_timestamps.append(bar.timestamp)
        equity_curve.append(_equity_for_portfolio(context.portfolio, last_prices))

    return BacktestResult(
        final_portfolio=context.portfolio,
        equity_timestamps=equity_timestamps,
        equity_curve=equity_curve,
        processed_bars=processed_bars,
        executed_trades=executed_trades,
        rejected_signals=rejected_signals,
        signal_events=signal_events,
        orders=orders,
        risk_rejections=risk_rejections,
    )


def _equity_for_portfolio(portfolio: PortfolioBook, marks: dict[str, Decimal]) -> Decimal:
    equity = portfolio.cash
    for symbol, quantity in portfolio.positions.items():
        mark_price = marks.get(symbol)
        if mark_price is None:
            continue
        equity += quantity * mark_price
    return equity





def _record_event(target: list[dict[str, Any]], event_name: str, payload: dict[str, Any]) -> None:
    target.append({"event": event_name, "payload": payload})
