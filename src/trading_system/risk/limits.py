from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class RiskLimits:
    max_position: Decimal
    max_notional: Decimal
    max_order_size: Decimal

    def allows_order(self, current_position: Decimal, order_size: Decimal, price: Decimal) -> bool:
        if abs(order_size) > self.max_order_size:
            return False

        projected_position = current_position + order_size
        if abs(projected_position) > self.max_position:
            return False

        projected_notional = abs(projected_position * price)
        return projected_notional <= self.max_notional
