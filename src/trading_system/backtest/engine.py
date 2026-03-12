from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from trading_system.analytics.metrics import cumulative_return
from trading_system.core.types import MarketBar
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import SignalSide, Strategy


@dataclass(slots=True)
class BacktestContext:
    portfolio: PortfolioBook
    risk_limits: RiskLimits
    fee_bps: Decimal


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

    for bar in bars:
        processed_bars += 1
        signal = strategy.evaluate(bar)
        signed_quantity = _signed_quantity(signal.side, signal.quantity)

        if signed_quantity != 0:
            current_position = context.portfolio.positions.get(bar.symbol, Decimal("0"))
            if context.risk_limits.allows_order(current_position, signed_quantity, bar.close):
                context.portfolio.apply_fill(bar.symbol, signed_quantity, bar.close)
                fee = _calculate_fee(signed_quantity, bar.close, context.fee_bps)
                context.portfolio.cash -= fee
                executed_trades += 1
            else:
                rejected_signals += 1

        equity_curve.append(_equity_for_symbol(context.portfolio, bar.symbol, bar.close))

    return BacktestResult(
        final_portfolio=context.portfolio,
        equity_curve=equity_curve,
        processed_bars=processed_bars,
        executed_trades=executed_trades,
        rejected_signals=rejected_signals,
    )


def _signed_quantity(side: SignalSide, quantity: Decimal) -> Decimal:
    if side == SignalSide.BUY:
        return quantity
    if side == SignalSide.SELL:
        return -quantity
    return Decimal("0")


def _calculate_fee(quantity: Decimal, price: Decimal, fee_bps: Decimal) -> Decimal:
    return abs(quantity * price) * fee_bps / Decimal("10000")


def _equity_for_symbol(portfolio: PortfolioBook, symbol: str, mark_price: Decimal) -> Decimal:
    position = portfolio.positions.get(symbol, Decimal("0"))
    return portfolio.cash + (position * mark_price)
