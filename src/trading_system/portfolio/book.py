from dataclasses import dataclass, field
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(slots=True)
class PortfolioBook:
    cash: Decimal
    positions: dict[str, Decimal] = field(default_factory=dict)
    average_costs: dict[str, Decimal] = field(default_factory=dict)
    realized_pnl: dict[str, Decimal] = field(default_factory=dict)
    fees_paid: dict[str, Decimal] = field(default_factory=dict)
    keep_flat_positions: bool = False

    def apply_fill(
        self,
        symbol: str,
        signed_quantity: Decimal,
        fill_price: Decimal,
        fee: Decimal = ZERO,
    ) -> None:
        previous_quantity = self.positions.get(symbol, ZERO)
        next_quantity = previous_quantity + signed_quantity
        average_cost = self.average_costs.get(symbol, ZERO)

        self.cash -= signed_quantity * fill_price
        self.cash -= fee
        self.fees_paid[symbol] = self.fees_paid.get(symbol, ZERO) + fee

        if previous_quantity == ZERO or _same_side(previous_quantity, signed_quantity):
            self._apply_open_or_increase(
                symbol,
                previous_quantity,
                signed_quantity,
                fill_price,
                next_quantity,
            )
            return

        closed_quantity = min(abs(previous_quantity), abs(signed_quantity))
        trade_pnl = _realized_trade_pnl(
            previous_quantity,
            average_cost,
            fill_price,
            closed_quantity,
        )
        self.realized_pnl[symbol] = self.realized_pnl.get(symbol, ZERO) + trade_pnl

        if next_quantity == ZERO:
            self._set_flat_position(symbol)
            return

        if _same_side(previous_quantity, next_quantity):
            self.positions[symbol] = next_quantity
            return

        self.positions[symbol] = next_quantity
        self.average_costs[symbol] = fill_price

    def unrealized_pnl(self, marks: dict[str, Decimal]) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for symbol, quantity in self.positions.items():
            if symbol not in marks:
                continue
            average_cost = self.average_costs.get(symbol, ZERO)
            result[symbol] = (marks[symbol] - average_cost) * quantity
        return result

    def total_fees_paid(self) -> Decimal:
        return sum(self.fees_paid.values(), start=ZERO)

    def _apply_open_or_increase(
        self,
        symbol: str,
        previous_quantity: Decimal,
        signed_quantity: Decimal,
        fill_price: Decimal,
        next_quantity: Decimal,
    ) -> None:
        if next_quantity == ZERO:
            self._set_flat_position(symbol)
            return

        if previous_quantity == ZERO:
            self.positions[symbol] = next_quantity
            self.average_costs[symbol] = fill_price
            return

        previous_notional = abs(previous_quantity) * self.average_costs.get(symbol, ZERO)
        trade_notional = abs(signed_quantity) * fill_price
        self.positions[symbol] = next_quantity
        self.average_costs[symbol] = (previous_notional + trade_notional) / abs(next_quantity)

    def _set_flat_position(self, symbol: str) -> None:
        if self.keep_flat_positions:
            self.positions[symbol] = ZERO
            self.average_costs[symbol] = ZERO
            return

        self.positions.pop(symbol, None)
        self.average_costs.pop(symbol, None)


def _same_side(left: Decimal, right: Decimal) -> bool:
    return (left > ZERO and right > ZERO) or (left < ZERO and right < ZERO)


def _realized_trade_pnl(
    previous_quantity: Decimal,
    average_cost: Decimal,
    fill_price: Decimal,
    closed_quantity: Decimal,
) -> Decimal:
    if previous_quantity > ZERO:
        return (fill_price - average_cost) * closed_quantity
    return (average_cost - fill_price) * closed_quantity
