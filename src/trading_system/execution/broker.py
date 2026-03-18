from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from trading_system.core.compat import StrEnum
from trading_system.core.ops import (
    CircuitBreakerPolicy,
    CircuitBreakerState,
    RetryPolicy,
    TimeoutPolicy,
    execute_with_resilience,
)
from trading_system.core.types import MarketBar
from trading_system.execution.orders import OrderRequest, OrderSide


class FillStatus(StrEnum):
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    UNFILLED = "unfilled"


@dataclass(slots=True)
class FillEvent:
    symbol: str
    side: OrderSide
    requested_quantity: Decimal
    filled_quantity: Decimal
    fill_price: Decimal
    fee: Decimal
    status: FillStatus

    @property
    def signed_quantity(self) -> Decimal:
        return self.filled_quantity if self.side == OrderSide.BUY else -self.filled_quantity


class FillQuantityPolicy(Protocol):
    def fill_quantity(self, order: OrderRequest, bar: MarketBar) -> Decimal:
        """Return absolute filled quantity."""


class SlippagePolicy(Protocol):
    def fill_price(self, order: OrderRequest, bar: MarketBar) -> Decimal:
        """Return the execution price after slippage."""


class CommissionPolicy(Protocol):
    def calculate_fee(
        self,
        order: OrderRequest,
        fill_quantity: Decimal,
        fill_price: Decimal,
    ) -> Decimal:
        """Return absolute fee for the fill."""


@dataclass(slots=True)
class FixedRatioFillPolicy:
    fill_ratio: Decimal = Decimal("1")

    def fill_quantity(self, order: OrderRequest, bar: MarketBar) -> Decimal:
        del bar
        ratio = min(max(self.fill_ratio, Decimal("0")), Decimal("1"))
        return order.quantity * ratio


@dataclass(slots=True)
class BpsSlippagePolicy:
    bps: Decimal = Decimal("0")

    def fill_price(self, order: OrderRequest, bar: MarketBar) -> Decimal:
        if order.side == OrderSide.BUY:
            return bar.close * (Decimal("1") + self.bps / Decimal("10000"))
        return bar.close * (Decimal("1") - self.bps / Decimal("10000"))


@dataclass(slots=True)
class BpsCommissionPolicy:
    bps: Decimal = Decimal("0")

    def calculate_fee(
        self,
        order: OrderRequest,
        fill_quantity: Decimal,
        fill_price: Decimal,
    ) -> Decimal:
        del order
        return abs(fill_quantity * fill_price) * self.bps / Decimal("10000")


class BrokerSimulator(Protocol):
    def submit_order(self, order: OrderRequest, bar: MarketBar) -> FillEvent:
        """Submit one order and return a deterministic fill event."""


@dataclass(slots=True)
class PolicyBrokerSimulator:
    fill_quantity_policy: FillQuantityPolicy
    slippage_policy: SlippagePolicy
    commission_policy: CommissionPolicy

    def submit_order(self, order: OrderRequest, bar: MarketBar) -> FillEvent:
        filled_quantity = self.fill_quantity_policy.fill_quantity(order, bar)
        if filled_quantity <= 0:
            return FillEvent(
                symbol=order.symbol,
                side=order.side,
                requested_quantity=order.quantity,
                filled_quantity=Decimal("0"),
                fill_price=bar.close,
                fee=Decimal("0"),
                status=FillStatus.UNFILLED,
            )

        fill_price = self.slippage_policy.fill_price(order, bar)
        fee = self.commission_policy.calculate_fee(order, filled_quantity, fill_price)
        status = (
            FillStatus.FILLED
            if filled_quantity == order.quantity
            else FillStatus.PARTIALLY_FILLED
        )
        return FillEvent(
            symbol=order.symbol,
            side=order.side,
            requested_quantity=order.quantity,
            filled_quantity=filled_quantity,
            fill_price=fill_price,
            fee=fee,
            status=status,
        )


@dataclass(slots=True)
class ResilientBroker:
    delegate: BrokerSimulator
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    circuit_breaker_policy: CircuitBreakerPolicy = field(default_factory=CircuitBreakerPolicy)
    _circuit_state: CircuitBreakerState = field(default_factory=CircuitBreakerState, init=False)

    def submit_order(self, order: OrderRequest, bar: MarketBar) -> FillEvent:
        return execute_with_resilience(
            operation=f"broker_submit:{order.symbol}",
            callback=lambda: self.delegate.submit_order(order, bar),
            retry=self.retry_policy,
            timeout=self.timeout_policy,
            circuit_breaker=self.circuit_breaker_policy,
            circuit_state=self._circuit_state,
        )
