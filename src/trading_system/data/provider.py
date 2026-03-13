from collections.abc import Iterable
from csv import DictReader
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from trading_system.core.types import MarketBar


class MarketDataProvider(Protocol):
    def load_bars(self, symbol: str) -> Iterable[MarketBar]:
        """Return historical or live-like bars for the given symbol."""


@dataclass(slots=True)
class InMemoryMarketDataProvider:
    bars_by_symbol: dict[str, list[MarketBar]]

    def load_bars(self, symbol: str) -> Iterable[MarketBar]:
        return list(self.bars_by_symbol.get(symbol, []))


@dataclass(slots=True)
class CsvMarketDataProvider:
    csv_by_symbol: dict[str, Path]

    def load_bars(self, symbol: str) -> Iterable[MarketBar]:
        csv_path = self.csv_by_symbol.get(symbol)
        if csv_path is None:
            return []

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = DictReader(handle)
            return [self._row_to_bar(symbol, row) for row in reader]

    def _row_to_bar(self, symbol: str, row: dict[str, str]) -> MarketBar:
        return MarketBar(
            symbol=symbol,
            timestamp=datetime.fromisoformat(row["timestamp"]),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=Decimal(row["volume"]),
        )
