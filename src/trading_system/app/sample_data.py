from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_system.core.types import MarketBar


def build_sample_bars(symbol: str = "BTCUSDT") -> list[MarketBar]:
    closes = [
        Decimal("100"),
        Decimal("101"),
        Decimal("103"),
        Decimal("102"),
        Decimal("104"),
        Decimal("105"),
        Decimal("103"),
    ]
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)

    return [
        MarketBar(
            symbol=symbol,
            timestamp=start + timedelta(minutes=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=Decimal("1"),
        )
        for index, close in enumerate(closes)
    ]
