from collections.abc import Iterable
from csv import DictReader
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from trading_system.core.ops import (
    CircuitBreakerPolicy,
    CircuitBreakerState,
    RetryPolicy,
    StructuredLogger,
    TimeoutPolicy,
    execute_with_resilience,
)
from trading_system.core.types import MarketBar
from trading_system.integrations.kis import KisApiClient


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
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    circuit_breaker_policy: CircuitBreakerPolicy = field(default_factory=CircuitBreakerPolicy)
    logger: StructuredLogger | None = None
    _circuit_state: CircuitBreakerState = field(default_factory=CircuitBreakerState, init=False)

    def load_bars(self, symbol: str) -> Iterable[MarketBar]:
        csv_path = self.csv_by_symbol.get(symbol)
        if csv_path is None:
            return []

        rows = execute_with_resilience(
            operation=f"csv_load:{symbol}",
            callback=lambda: self._load_rows(symbol, csv_path),
            retry=self.retry_policy,
            timeout=self.timeout_policy,
            circuit_breaker=self.circuit_breaker_policy,
            circuit_state=self._circuit_state,
        )
        if self.logger is not None:
            self.logger.emit(
                "data.load.success",
                severity=20,
                payload={"symbol": symbol, "rows": len(rows), "path": str(csv_path)},
            )
        return rows

    def _load_rows(self, symbol: str, csv_path: Path) -> list[MarketBar]:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = DictReader(handle)
            return [self._row_to_bar(symbol=symbol, row=row) for row in reader]

    def _row_to_bar(self, symbol: str, row: dict[str, str]) -> MarketBar:
        resolved_symbol = symbol or row.get("symbol", "UNKNOWN")
        return MarketBar(
            symbol=resolved_symbol,
            timestamp=datetime.fromisoformat(row["timestamp"]),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=Decimal(row["volume"]),
        )


@dataclass(slots=True)
class KisQuoteMarketDataProvider:
    client: KisApiClient
    bars_per_load: int = 1

    def load_bars(self, symbol: str) -> Iterable[MarketBar]:
        sample_size = max(self.bars_per_load, 1)
        bars: list[MarketBar] = []
        for _ in range(sample_size):
            quote = self.client.preflight_symbol(symbol)
            bars.append(
                MarketBar(
                    symbol=symbol,
                    timestamp=quote.as_of,
                    open=quote.price,
                    high=quote.price,
                    low=quote.price,
                    close=quote.price,
                    volume=quote.volume,
                )
            )
        return bars
