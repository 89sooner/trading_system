from decimal import Decimal
from pathlib import Path

from trading_system.patterns.repository import PatternSet, PatternSetRepository
from trading_system.patterns.types import LearnedPattern
from trading_system.strategy.base import SignalSide
from trading_system.strategy.repository import StrategyProfile, StrategyProfileRepository


def test_pattern_set_repository_round_trip(tmp_path: Path) -> None:
    repository = PatternSetRepository(tmp_path / "patterns")
    pattern_set = PatternSet(
        pattern_set_id="bullish-patterns",
        name="Bullish Patterns",
        symbol="BTCUSDT",
        default_threshold=0.8,
        examples_count=2,
        patterns=[
            LearnedPattern(
                label="bullish_reversal",
                lookback=4,
                prototype=(0.1, 0.2, 0.3),
                sample_size=2,
                threshold=0.8,
            )
        ],
    )

    repository.save(pattern_set)
    loaded = repository.get("bullish-patterns")

    assert loaded == pattern_set
    assert repository.list() == [pattern_set]


def test_strategy_profile_repository_round_trip(tmp_path: Path) -> None:
    repository = StrategyProfileRepository(tmp_path / "strategies")
    profile = StrategyProfile(
        strategy_id="pattern-bullish",
        name="Pattern Bullish",
        strategy_type="pattern_signal",
        pattern_set_id="bullish-patterns",
        label_to_side={"bullish_reversal": SignalSide.BUY},
        trade_quantity=Decimal("0.3"),
        threshold_overrides={"bullish_reversal": 0.92},
    )

    repository.save(profile)
    loaded = repository.get("pattern-bullish")

    assert loaded == profile
    assert repository.list() == [profile]
