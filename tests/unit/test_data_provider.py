from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from trading_system.core.types import MarketBar
from trading_system.data.provider import (
    CsvMarketDataProvider,
    InMemoryMarketDataProvider,
    KisQuoteMarketDataProvider,
)
from trading_system.integrations.kis import KisQuote


def test_in_memory_provider_loads_symbol_bars() -> None:
    bars = [_bar(Decimal("100")), _bar(Decimal("101"))]
    provider = InMemoryMarketDataProvider(bars_by_symbol={"BTCUSDT": bars})

    loaded = list(provider.load_bars("BTCUSDT"))

    assert loaded == bars


def test_csv_provider_loads_bars(tmp_path: Path) -> None:
    csv_path = tmp_path / "btc.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01T00:00:00+00:00,100,101,99,100,1\n"
        "2024-01-01T00:01:00+00:00,100,102,100,101,2\n",
        encoding="utf-8",
    )
    provider = CsvMarketDataProvider(csv_by_symbol={"BTCUSDT": csv_path})

    loaded = list(provider.load_bars("BTCUSDT"))

    assert [bar.close for bar in loaded] == [Decimal("100"), Decimal("101")]
    assert loaded[0].timestamp == datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_kis_quote_provider_maps_quote_to_single_live_like_bar() -> None:
    provider = KisQuoteMarketDataProvider(client=_FakeKisClient())

    loaded = list(provider.load_bars("005930"))

    assert len(loaded) == 1
    assert loaded[0].symbol == "005930"
    assert loaded[0].close == Decimal("70100")
    assert loaded[0].volume == Decimal("1500")


def test_kis_quote_provider_can_sample_multiple_live_bars() -> None:
    provider = KisQuoteMarketDataProvider(client=_FakeKisClient(), bars_per_load=2)

    loaded = list(provider.load_bars("005930"))

    assert len(loaded) == 2
    assert all(bar.symbol == "005930" for bar in loaded)


def _bar(close: Decimal) -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=Decimal("1"),
    )


class _FakeKisClient:
    def preflight_symbol(self, symbol: str) -> KisQuote:
        return KisQuote(
            symbol=symbol,
            price=Decimal("70100"),
            volume=Decimal("1500"),
            as_of=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
