from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class PortfolioBook:
    cash: Decimal
    positions: dict[str, Decimal] = field(default_factory=dict)

    def apply_fill(self, symbol: str, signed_quantity: Decimal, fill_price: Decimal) -> None:
        self.positions[symbol] = self.positions.get(symbol, Decimal("0")) + signed_quantity
        self.cash -= signed_quantity * fill_price
