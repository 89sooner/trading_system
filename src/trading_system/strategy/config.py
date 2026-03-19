from dataclasses import dataclass, field
from decimal import Decimal

from trading_system.strategy.base import SignalSide


@dataclass(slots=True, frozen=True)
class PatternSignalStrategyConfig:
    pattern_set_id: str
    label_to_side: dict[str, SignalSide]
    trade_quantity: Decimal | None = None
    threshold_overrides: dict[str, float] = field(default_factory=dict)

