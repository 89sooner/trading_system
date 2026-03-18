from dataclasses import dataclass
from decimal import Decimal
from trading_system.core.compat import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(slots=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: Decimal
    limit_price: Decimal | None = None
