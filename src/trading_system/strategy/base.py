from dataclasses import dataclass
from decimal import Decimal
from trading_system.core.compat import StrEnum
from typing import Protocol

from trading_system.core.types import MarketBar


class SignalSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(slots=True)
class StrategySignal:
    side: SignalSide
    quantity: Decimal
    reason: str


class Strategy(Protocol):
    name: str

    def evaluate(self, bar: MarketBar) -> StrategySignal:
        """Produce the next desired action for a bar."""
