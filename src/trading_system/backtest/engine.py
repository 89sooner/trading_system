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

    for bar in bars:
        processed_bars += 1
        try:
            signal = strategy.evaluate(bar)
            order = signal_to_order_request(bar.symbol, signal)
            if order is not None:
                _log_order_created(context, order.symbol, order.side.value, order.quantity)
                if _order_allowed(context, bar.symbol, bar.close, order.side, order.quantity):
                    executed_trades += _apply_fill(context, order, bar)
                else:
                    rejected_signals += 1
            equity_curve.append(_equity_for_symbol(context.portfolio, bar.symbol, bar.close))
        except (RuntimeError, ValueError) as exc:
            _log_exception(context, exc)
            raise

    return BacktestResult(
        final_portfolio=context.portfolio,
        equity_curve=equity_curve,
        processed_bars=processed_bars,
        executed_trades=executed_trades,
        rejected_signals=rejected_signals,
    )


def _order_allowed(
    context: BacktestContext,
    symbol: str,
    price: Decimal,
    side: OrderSide,
    quantity: Decimal,
) -> bool:
    signed_quantity = quantity if side == OrderSide.BUY else -quantity
    current_position = context.portfolio.positions.get(symbol, Decimal("0"))
    allowed = context.risk_limits.allows_order(current_position, signed_quantity, price)
    if allowed:
        return True

    _log_risk_rejected(context, symbol, signed_quantity, current_position, price)
    _log_order_rejected(context, symbol, side.value, quantity, "risk_limits")
    return False


def _apply_fill(context: BacktestContext, order, bar: MarketBar) -> int:
    fill = context.broker.submit_order(order, bar)
    if fill.filled_quantity <= 0:
        _log_order_rejected(context, order.symbol, order.side.value, order.quantity, "unfilled")
        return 0

    context.portfolio.apply_fill(fill.symbol, fill.signed_quantity, fill.fill_price)
    context.portfolio.cash -= fill.fee
    _log_order_filled(
        context,
        fill.symbol,
        fill.side.value,
        fill.requested_quantity,
        fill.filled_quantity,
        fill.fill_price,
        fill.fee,
        fill.status.value,
    )
    return 1


def _log_order_created(context: BacktestContext, symbol: str, side: str, quantity: Decimal) -> None:
    _emit(context, "order.created", event_payload(OrderCreatedEvent(symbol, side, quantity)))


def _log_order_rejected(
    context: BacktestContext,
    symbol: str,
    side: str,
    quantity: Decimal,
    reason: str,
) -> None:
    _emit(
        context,
        "order.rejected",
        event_payload(OrderRejectedEvent(symbol, side, quantity, reason)),
    )


def _log_order_filled(
    context: BacktestContext,
    symbol: str,
    side: str,
    requested_quantity: Decimal,
    filled_quantity: Decimal,
    fill_price: Decimal,
    fee: Decimal,
    status: str,
) -> None:
    _emit(
        context,
        "order.filled",
        event_payload(
            OrderFilledEvent(
                symbol,
                side,
                requested_quantity,
                filled_quantity,
                fill_price,
                fee,
                status,
            )
        ),
    )


def _log_risk_rejected(
    context: BacktestContext,
    symbol: str,
    requested_quantity: Decimal,
    current_position: Decimal,
    price: Decimal,
) -> None:
    _emit(
        context,
        "risk.rejected",
        event_payload(RiskRejectedEvent(symbol, requested_quantity, current_position, price)),
    )


def _log_exception(context: BacktestContext, error: Exception) -> None:
    _emit(context, "exception", event_payload(ExceptionEvent(type(error).__name__, str(error))), 40)


def _emit(
    context: BacktestContext,
    event: str,
    payload: dict[str, object],
    severity: int = 20,
) -> None:
    if context.logger is None:
        return
    context.logger.emit(event, severity=severity, payload=payload)


def _equity_for_symbol(portfolio: PortfolioBook, symbol: str, mark_price: Decimal) -> Decimal:
    position = portfolio.positions.get(symbol, Decimal("0"))
    return portfolio.cash + (position * mark_price)
