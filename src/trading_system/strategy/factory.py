from dataclasses import replace

from trading_system.app.settings import AppSettings, PatternSignalStrategySettings
from trading_system.patterns.repository import PatternSetRepository
from trading_system.strategy.base import SignalSide, Strategy
from trading_system.strategy.config import PatternSignalStrategyConfig
from trading_system.strategy.example import MomentumStrategy
from trading_system.strategy.pattern import PatternSignalStrategy
from trading_system.strategy.repository import StrategyProfileRepository


def build_strategy(
    settings: AppSettings,
    *,
    pattern_repository: PatternSetRepository,
    strategy_repository: StrategyProfileRepository,
) -> Strategy:
    if settings.strategy is None:
        return MomentumStrategy(trade_quantity=settings.backtest.trade_quantity)

    config = _resolve_pattern_strategy_config(
        settings.strategy,
        strategy_repository=strategy_repository,
    )
    pattern_set = pattern_repository.get(config.pattern_set_id)
    patterns = [
        replace(pattern, threshold=config.threshold_overrides.get(pattern.label, pattern.threshold))
        for pattern in pattern_set.patterns
    ]
    trade_quantity = config.trade_quantity or settings.backtest.trade_quantity
    return PatternSignalStrategy(
        patterns=patterns,
        label_to_side=config.label_to_side,
        trade_quantity=trade_quantity,
    )


def _resolve_pattern_strategy_config(
    settings: PatternSignalStrategySettings,
    *,
    strategy_repository: StrategyProfileRepository,
) -> PatternSignalStrategyConfig:
    if settings.profile_id is not None:
        profile = strategy_repository.get(settings.profile_id)
        return PatternSignalStrategyConfig(
            pattern_set_id=profile.pattern_set_id,
            label_to_side=_copy_label_map(profile.label_to_side),
            trade_quantity=profile.trade_quantity,
            threshold_overrides=dict(profile.threshold_overrides),
        )

    assert settings.pattern_set_id is not None
    return PatternSignalStrategyConfig(
        pattern_set_id=settings.pattern_set_id,
        label_to_side=_copy_label_map(settings.label_to_side),
        trade_quantity=settings.trade_quantity,
        threshold_overrides=dict(settings.threshold_overrides),
    )


def _copy_label_map(label_to_side: dict[str, SignalSide]) -> dict[str, SignalSide]:
    return {label: SignalSide(side) for label, side in label_to_side.items()}
