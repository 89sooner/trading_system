from dataclasses import dataclass
from decimal import Decimal
from typing import Any

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
from trading_system.execution.orders import OrderRequest, OrderSide
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.risk.portfolio_limits import PortfolioRiskLimits
from trading_system.strategy.base import Strategy


@dataclass(slots=True)
class TradingContext:
    portfolio: PortfolioBook
    risk_limits: RiskLimits
    broker: BrokerSimulator
    logger: StructuredLogger | None = None
    portfolio_risk: PortfolioRiskLimits | None = None


@dataclass(slots=True)
class StepEvents:
    signal: dict[str, Any] | None = None
    order_created: dict[str, Any] | None = None
    order_filled: dict[str, Any] | None = None
    order_rejected: dict[str, Any] | None = None
    risk_rejected: dict[str, Any] | None = None


def execute_trading_step(bar: MarketBar, strategy: Strategy, context: TradingContext) -> StepEvents:
    events = StepEvents()

    # --- Portfolio-level drawdown guard --------------------------------
    if context.portfolio_risk is not None:
        total_realized = sum(context.portfolio.realized_pnl.values(), start=Decimal("0"))
        current_equity = context.portfolio.cash + total_realized
        context.portfolio_risk.update_peak(current_equity)
        if context.portfolio_risk.is_daily_limit_breached(current_equity):
            _emit_event(
                context.logger,
                "risk.daily_limit_breached",
                {
                    "symbol": bar.symbol,
                    "current_equity": str(current_equity),
                    "session_peak": str(context.portfolio_risk.session_peak_equity),
                },
            )
            return events

    signal = strategy.evaluate(bar)
    if signal.side.value != "hold":
        # Convert quantity to string to ensure stable JSON emission
        events.signal = {
            "symbol": bar.symbol,
            "strategy": strategy.name,
            "side": signal.side.value,
            "quantity": str(signal.quantity),
            "reason": signal.reason,
        }
        _emit_event(context.logger, "strategy.signal", events.signal)

    order = signal_to_order_request(bar.symbol, signal)
    if order is None:
        return events

    events.order_created = event_payload(
        OrderCreatedEvent(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
        )
    )
    _emit_event(context.logger, "order.created", events.order_created)

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
            events.order_filled = event_payload(
                OrderFilledEvent(
                    symbol=fill.symbol,
                    side=fill.side.value,
                    requested_quantity=fill.requested_quantity,
                    filled_quantity=fill.filled_quantity,
                    fill_price=fill.fill_price,
                    fee=fill.fee,
                    status=fill.status.value,
                )
            )
            _emit_event(context.logger, "order.filled", events.order_filled)
        else:
            events.order_rejected = event_payload(
                OrderRejectedEvent(
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=order.quantity,
                    reason="unfilled",
                )
            )
            _emit_event(context.logger, "order.rejected", events.order_rejected)
    else:
        events.risk_rejected = event_payload(
            RiskRejectedEvent(
                symbol=order.symbol,
                requested_quantity=signed_quantity,
                current_position=current_position,
                price=bar.close,
            )
        )
        _emit_event(context.logger, "risk.rejected", events.risk_rejected)

    # --- SL/TP auto-close ------------------------------------------------
    if context.portfolio_risk is not None:
        _check_sl_tp(bar, context)

    return events


def _check_sl_tp(bar: MarketBar, context: TradingContext) -> None:
    """Auto-close long positions that have hit SL or TP thresholds."""
    pr = context.portfolio_risk
    if pr is None:
        return
    for symbol, qty in list(context.portfolio.positions.items()):
        if symbol != bar.symbol or qty <= Decimal("0"):
            continue
        avg_cost = context.portfolio.average_costs.get(symbol, Decimal("0"))
        sl_hit = pr.sl_triggered(avg_cost, bar.close, qty)
        tp_hit = pr.tp_triggered(avg_cost, bar.close, qty)
        if not (sl_hit or tp_hit):
            continue
        reason = "sl_triggered" if sl_hit else "tp_triggered"
        close_order = OrderRequest(symbol=symbol, side=OrderSide.SELL, quantity=abs(qty))
        _emit_event(
            context.logger,
            f"risk.{reason}",
            {"symbol": symbol, "avg_cost": str(avg_cost), "mark": str(bar.close)},
        )
        fill = context.broker.submit_order(close_order, bar)
        if fill.filled_quantity > 0:
            context.portfolio.apply_fill(
                fill.symbol, fill.signed_quantity, fill.fill_price, fee=fill.fee
            )
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


def _emit_event(
    logger: StructuredLogger | None,
    event_name: str,
    payload: dict[str, Any],
) -> None:
    if logger is None:
        return
    logger.emit(event_name, severity=20, payload=payload)
