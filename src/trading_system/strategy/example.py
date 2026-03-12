from dataclasses import dataclass, field
from decimal import Decimal

from trading_system.core.types import MarketBar
from trading_system.strategy.base import SignalSide, StrategySignal


@dataclass(slots=True)
class MomentumStrategy:
    name: str = "momentum"
    trade_quantity: Decimal = Decimal("0.1")
    _previous_close: Decimal | None = field(default=None, init=False, repr=False)

    def evaluate(self, bar: MarketBar) -> StrategySignal:
        if self._previous_close is None:
            self._previous_close = bar.close
            return StrategySignal(
                side=SignalSide.HOLD,
                quantity=Decimal("0"),
                reason="waiting_for_previous_close",
            )

        previous_close = self._previous_close
        self._previous_close = bar.close

        if bar.close > previous_close:
            return StrategySignal(
                side=SignalSide.BUY,
                quantity=self.trade_quantity,
                reason="close_above_previous_close",
            )

        if bar.close < previous_close:
            return StrategySignal(
                side=SignalSide.SELL,
                quantity=self.trade_quantity,
                reason="close_below_previous_close",
            )

        return StrategySignal(
            side=SignalSide.HOLD,
            quantity=Decimal("0"),
            reason="close_unchanged",
        )
