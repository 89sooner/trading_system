"""Strategy contracts and signals."""

from trading_system.strategy.base import SignalSide, Strategy, StrategySignal
from trading_system.strategy.pattern import PatternSignalStrategy

__all__ = ["PatternSignalStrategy", "SignalSide", "Strategy", "StrategySignal"]
