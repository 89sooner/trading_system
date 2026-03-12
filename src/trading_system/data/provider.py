from collections.abc import Iterable
from typing import Protocol

from trading_system.core.types import MarketBar


class MarketDataProvider(Protocol):
    def load_bars(self, symbol: str) -> Iterable[MarketBar]:
        """Return historical or live-like bars for the given symbol."""
