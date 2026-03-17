from datetime import datetime, timedelta
from decimal import Decimal

from trading_system.core.types import MarketBar
from trading_system.patterns.alerts import PatternAlertService
from trading_system.patterns.trainer import PatternTrainer
from trading_system.patterns.types import PatternExample


def run_example() -> None:
    trainer = PatternTrainer(default_threshold=0.8)
    learned_patterns = trainer.train(
        [
            PatternExample(label="bullish_reversal", bars=_bars([100, 98, 101, 104])),
            PatternExample(label="bullish_reversal", bars=_bars([200, 197, 202, 207])),
            PatternExample(label="bearish_reversal", bars=_bars([100, 103, 99, 96])),
        ]
    )

    current_window = _bars([300, 294, 303, 312])
    alert = PatternAlertService().evaluate("BTCUSDT", current_window, learned_patterns)

    if alert is None:
        print("No pattern match.")
        return

    print(alert.message)


def _bars(closes: list[int]) -> list[MarketBar]:
    start = datetime(2024, 1, 1, 9, 0)
    bars: list[MarketBar] = []
    for index, close in enumerate(closes):
        open_price = closes[index - 1] if index > 0 else close
        high = max(open_price, close) + 1
        low = min(open_price, close) - 1
        bars.append(
            MarketBar(
                symbol="BTCUSDT",
                timestamp=start + timedelta(minutes=index),
                open=Decimal(str(open_price)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=Decimal("1"),
            )
        )
    return bars


if __name__ == "__main__":
    run_example()
