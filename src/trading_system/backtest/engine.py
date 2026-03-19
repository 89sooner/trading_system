from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from trading_system.analytics.metrics import cumulative_return
from trading_system.core.ops import (
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
        signal = strategy.evaluate(bar)
        if signal.side.value != "hold":
            signal_payload = {
                "symbol": bar.symbol,
                "strategy": strategy.name,
                "side": signal.side.value,
                "quantity": signal.quantity,
                "reason": signal.reason,
            }
            _emit_event(context.logger, "strategy.signal", signal_payload)
            _record_event(signal_events, "strategy.signal", signal_payload)
        order = signal_to_order_request(bar.symbol, signal)

        if order is not None:
            order_created_payload = event_payload(
                OrderCreatedEvent(
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=order.quantity,
                )
            )
            _emit_event(
                context.logger,
                "order.created",
                order_created_payload,
            )
            _record_event(orders, "order.created", order_created_payload)
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
                    _emit_event(
                        context.logger,
                        "order.filled",
                        event_payload(
                            OrderFilledEvent(
                                symbol=fill.symbol,
                                side=fill.side.value,
                                requested_quantity=fill.requested_quantity,
                                filled_quantity=fill.filled_quantity,
                                fill_price=fill.fill_price,
                                fee=fill.fee,
                                status=fill.status.value,
                            )
                        ),
                    )
                    _record_event(
                        orders,
                        "order.filled",
                        event_payload(
                            OrderFilledEvent(
                                symbol=fill.symbol,
                                side=fill.side.value,
                                requested_quantity=fill.requested_quantity,
                                filled_quantity=fill.filled_quantity,
                                fill_price=fill.fill_price,
                                fee=fill.fee,
                                status=fill.status.value,
                            )
                        ),
                    )
                else:
                    _emit_event(
                        context.logger,
                        "order.rejected",
                        event_payload(
                            OrderRejectedEvent(
                                symbol=order.symbol,
                                side=order.side.value,
                                quantity=order.quantity,
                                reason="unfilled",
                            )
                        ),
                    )
                    _record_event(
                        orders,
                        "order.rejected",
                        event_payload(
                            OrderRejectedEvent(
                                symbol=order.symbol,
                                side=order.side.value,
                                quantity=order.quantity,
                                reason="unfilled",
                            )
                        ),
                    )
            else:
                rejected_signals += 1
                _emit_event(
                    context.logger,
                    "risk.rejected",
                    event_payload(
                        RiskRejectedEvent(
                            symbol=order.symbol,
                            requested_quantity=signed_quantity,
                            current_position=current_position,
                            price=bar.close,
                        )
                    ),
                )
                _record_event(
                    risk_rejections,
                    "risk.rejected",
                    event_payload(
                        RiskRejectedEvent(
                            symbol=order.symbol,
                            requested_quantity=signed_quantity,
                            current_position=current_position,
                            price=bar.close,
                        )
                    ),
                )

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


def _emit_event(
    logger: StructuredLogger | None,
    event_name: str,
    payload: dict[str, Any],
) -> None:
    if logger is None:
        return
    logger.emit(event_name, severity=20, payload=payload)


def _record_event(target: list[dict[str, Any]], event_name: str, payload: dict[str, Any]) -> None:
    target.append({"event": event_name, "payload": payload})
