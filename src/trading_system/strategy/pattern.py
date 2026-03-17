from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from trading_system.core.types import MarketBar
from trading_system.patterns.alerts import PatternAlertService
from trading_system.patterns.types import LearnedPattern
from trading_system.strategy.base import SignalSide, StrategySignal


@dataclass(slots=True)
class PatternSignalStrategy:
    patterns: list[LearnedPattern]
    label_to_side: Mapping[str, SignalSide]
    trade_quantity: Decimal = Decimal("1")
    alert_service: PatternAlertService = field(default_factory=PatternAlertService)
    name: str = "pattern_signal"
    _history: dict[str, deque[MarketBar]] = field(default_factory=dict, init=False, repr=False)

    def evaluate(self, bar: MarketBar) -> StrategySignal:
        history = self._history.setdefault(bar.symbol, deque(maxlen=self._lookback))
        history.append(bar)

        if len(history) < self._lookback:
            return StrategySignal(
                side=SignalSide.HOLD,
                quantity=Decimal("0"),
                reason="waiting_for_pattern_window",
            )

        alert = self.alert_service.evaluate(bar.symbol, list(history), self.patterns)
        if alert is None:
            return StrategySignal(
                side=SignalSide.HOLD,
                quantity=Decimal("0"),
                reason="no_pattern_match",
            )

        side = self.label_to_side.get(alert.label, SignalSide.HOLD)
        quantity = self.trade_quantity if side != SignalSide.HOLD else Decimal("0")
        return StrategySignal(
            side=side,
            quantity=quantity,
            reason=f"{alert.label}:{alert.similarity:.3f}",
        )

    @property
    def _lookback(self) -> int:
        return max(pattern.lookback for pattern in self.patterns)
