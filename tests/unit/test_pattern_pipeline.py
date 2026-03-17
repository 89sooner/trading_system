from datetime import datetime, timedelta
from decimal import Decimal

from trading_system.core.types import MarketBar
from trading_system.patterns.alerts import PatternAlertService
from trading_system.patterns.matcher import PatternMatcher
from trading_system.patterns.trainer import PatternTrainer
from trading_system.patterns.types import PatternExample
from trading_system.strategy.base import SignalSide
from trading_system.strategy.pattern import PatternSignalStrategy


def test_pattern_trainer_and_matcher_rank_similar_pattern_first() -> None:
    trainer = PatternTrainer(default_threshold=0.8)
    patterns = trainer.train(
        [
            PatternExample(label="bullish_reversal", bars=_bars([100, 98, 101, 104])),
            PatternExample(label="bullish_reversal", bars=_bars([200, 197, 202, 207])),
            PatternExample(label="bearish_reversal", bars=_bars([100, 103, 99, 96])),
            PatternExample(label="bearish_reversal", bars=_bars([200, 205, 198, 193])),
        ]
    )

    matches = PatternMatcher().match(patterns, _bars([300, 294, 303, 312]))

    assert matches[0].label == "bullish_reversal"
    assert matches[0].is_match is True
    assert matches[0].similarity > matches[1].similarity


def test_pattern_alert_service_returns_alert_for_matching_window() -> None:
    trainer = PatternTrainer(default_threshold=0.8)
    patterns = trainer.train(
        [PatternExample(label="bullish_reversal", bars=_bars([100, 98, 101, 104]))]
    )

    alert = PatternAlertService().evaluate("ETHUSDT", _bars([250, 245, 253, 260]), patterns)

    assert alert is not None
    assert alert.symbol == "ETHUSDT"
    assert alert.label == "bullish_reversal"
    assert "matched bullish_reversal" in alert.message


def test_pattern_signal_strategy_emits_buy_after_window_is_full() -> None:
    trainer = PatternTrainer(default_threshold=0.8)
    patterns = trainer.train(
        [PatternExample(label="bullish_reversal", bars=_bars([100, 98, 101, 104]))]
    )
    strategy = PatternSignalStrategy(
        patterns=patterns,
        label_to_side={"bullish_reversal": SignalSide.BUY},
        trade_quantity=Decimal("2"),
    )

    signals = [strategy.evaluate(bar) for bar in _bars([250, 245, 253, 260])]

    assert [signal.side for signal in signals[:-1]] == [SignalSide.HOLD] * 3
    assert signals[-1].side == SignalSide.BUY
    assert signals[-1].quantity == Decimal("2")
    assert signals[-1].reason.startswith("bullish_reversal:")


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
