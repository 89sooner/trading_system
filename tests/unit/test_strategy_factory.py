from decimal import Decimal
from pathlib import Path

from trading_system.app.settings import (
    AppMode,
    AppSettings,
    BacktestSettings,
    LiveExecutionMode,
    PatternSignalStrategySettings,
    RiskSettings,
)
from trading_system.patterns.repository import PatternSet, PatternSetRepository
from trading_system.patterns.types import LearnedPattern
from trading_system.strategy.base import SignalSide
from trading_system.strategy.factory import build_strategy
from trading_system.strategy.pattern import PatternSignalStrategy
from trading_system.strategy.repository import StrategyProfile, StrategyProfileRepository


def test_build_strategy_returns_pattern_signal_strategy_from_inline_settings(
    tmp_path: Path,
) -> None:
    pattern_repository = PatternSetRepository(tmp_path / "patterns")
    strategy_repository = StrategyProfileRepository(tmp_path / "strategies")
    pattern_repository.save(
        PatternSet(
            pattern_set_id="bullish",
            name="Bullish",
            symbol="BTCUSDT",
            default_threshold=0.8,
            examples_count=2,
            patterns=[
                LearnedPattern(
                    label="bullish_reversal",
                    lookback=4,
                    prototype=(1.0, 2.0),
                    sample_size=2,
                    threshold=0.8,
                )
            ],
        )
    )
    settings = _build_settings(
        PatternSignalStrategySettings(
            pattern_set_id="bullish",
            label_to_side={"bullish_reversal": SignalSide.BUY},
            trade_quantity=Decimal("2"),
            threshold_overrides={"bullish_reversal": 0.9},
        )
    )

    strategy = build_strategy(
        settings,
        pattern_repository=pattern_repository,
        strategy_repository=strategy_repository,
    )

    assert isinstance(strategy, PatternSignalStrategy)
    assert strategy.trade_quantity == Decimal("2")
    assert strategy.patterns[0].threshold == 0.9


def test_build_strategy_uses_saved_profile_when_profile_id_is_provided(tmp_path: Path) -> None:
    pattern_repository = PatternSetRepository(tmp_path / "patterns")
    strategy_repository = StrategyProfileRepository(tmp_path / "strategies")
    pattern_repository.save(
        PatternSet(
            pattern_set_id="bullish",
            name="Bullish",
            symbol="BTCUSDT",
            default_threshold=0.8,
            examples_count=2,
            patterns=[
                LearnedPattern(
                    label="bullish_reversal",
                    lookback=4,
                    prototype=(1.0, 2.0),
                    sample_size=2,
                    threshold=0.8,
                )
            ],
        )
    )
    strategy_repository.save(
        StrategyProfile(
            strategy_id="profile-1",
            name="Profile 1",
            strategy_type="pattern_signal",
            pattern_set_id="bullish",
            label_to_side={"bullish_reversal": SignalSide.HOLD},
            trade_quantity=Decimal("3"),
            threshold_overrides={"bullish_reversal": 0.95},
        )
    )
    settings = _build_settings(PatternSignalStrategySettings(profile_id="profile-1"))

    strategy = build_strategy(
        settings,
        pattern_repository=pattern_repository,
        strategy_repository=strategy_repository,
    )

    assert isinstance(strategy, PatternSignalStrategy)
    assert strategy.trade_quantity == Decimal("3")
    assert strategy.label_to_side["bullish_reversal"] == SignalSide.HOLD
    assert strategy.patterns[0].threshold == 0.95


def _build_settings(strategy: PatternSignalStrategySettings | None) -> AppSettings:
    return AppSettings(
        mode=AppMode.BACKTEST,
        symbols=("BTCUSDT",),
        provider="mock",
        broker="paper",
        live_execution=LiveExecutionMode.PREFLIGHT,
        risk=RiskSettings(
            max_position=Decimal("1"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("0.25"),
        ),
        backtest=BacktestSettings(
            starting_cash=Decimal("10000"),
            fee_bps=Decimal("5"),
            trade_quantity=Decimal("0.1"),
        ),
        strategy=strategy,
    )
