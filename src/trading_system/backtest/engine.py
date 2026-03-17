from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from trading_system.analytics.metrics import cumulative_return
from trading_system.core.ops import (
    ExceptionEvent,
    OrderCreatedEvent,
    OrderFilledEvent,
    OrderRejectedEvent,
    RiskRejectedEvent,
    StructuredLogger,
    event_payload,
)
from trading_system.core.types import MarketBar
from trading_system.execution.adapters import signal_to_order_request
from trading_system.execution.broker import BrokerSimulator
from trading_system.execution.orders import OrderSide
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import Strategy


@dataclass(slots=True)
class BacktestContext:
    portfolio: PortfolioBook
    risk_limits: RiskLimits
    broker: BrokerSimulator
    logger: StructuredLogger | None = None


@dataclass(slots=True)
class BacktestResult:
    final_portfolio: PortfolioBook
    equity_curve: list[Decimal]
    processed_bars: int
    executed_trades: int
    rejected_signals: int

    @property
    def total_return(self) -> Decimal:
        return cumulative_return(self.equity_curve)


def run_backtest(
    bars: Iterable[MarketBar],
    strategy: Strategy,
    context: BacktestContext,
) -> BacktestResult:
    equity_curve: list[Decimal] = []
    processed_bars = 0
    executed_trades = 0
    rejected_signals = 0
    last_prices: dict[str, Decimal] = {}

    for bar in bars:
        processed_bars += 1
        signal = strategy.evaluate(bar)
        order = signal_to_order_request(bar.symbol, signal)

        if order is not None:
            signed_quantity = order.quantity if order.side == OrderSide.BUY else -order.quantity
            current_position = context.portfolio.positions.get(bar.symbol, Decimal("0"))
            if context.risk_limits.allows_order(current_position, signed_quantity, bar.close):
                fill = context.broker.submit_order(order, bar)
                if fill.filled_quantity > 0:
                    context.portfolio.apply_fill(
                        fill.symbol,
                        fill.signed_quantity,
                        fill.fill_price,
                        fee=fill.fee,
                    )
                    executed_trades += 1
            else:
                rejected_signals += 1

        last_prices[bar.symbol] = bar.close
        equity_curve.append(_equity_for_portfolio(context.portfolio, last_prices))

    return BacktestResult(
        final_portfolio=context.portfolio,
        equity_curve=equity_curve,
        processed_bars=processed_bars,
        executed_trades=executed_trades,
        rejected_signals=rejected_signals,
    )


def _equity_for_portfolio(portfolio: PortfolioBook, marks: dict[str, Decimal]) -> Decimal:
    equity = portfolio.cash
    for symbol, quantity in portfolio.positions.items():
        mark_price = marks.get(symbol)
        if mark_price is None:
            continue
        equity += quantity * mark_price
    return equity
