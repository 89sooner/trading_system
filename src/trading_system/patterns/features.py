from collections.abc import Sequence

from trading_system.core.types import MarketBar


def extract_pattern_vector(bars: Sequence[MarketBar]) -> tuple[float, ...]:
    if len(bars) < 2:
        raise ValueError("pattern extraction requires at least two bars")

    vector: list[float] = []
    previous_close = float(bars[0].close)

    for bar in bars:
        open_price = float(bar.open)
        high_price = float(bar.high)
        low_price = float(bar.low)
        close_price = float(bar.close)
        range_value = max(high_price - low_price, 1e-9)

        vector.extend(
            [
                _safe_ratio(close_price - open_price, open_price),
                _safe_ratio(high_price - low_price, open_price),
                (close_price - low_price) / range_value,
                _safe_ratio(close_price - previous_close, previous_close),
            ]
        )
        previous_close = close_price

    return tuple(vector)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) < 1e-9:
        return 0.0
    return numerator / denominator
