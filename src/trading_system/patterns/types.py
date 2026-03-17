from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from trading_system.core.types import MarketBar


@dataclass(slots=True, frozen=True)
class PatternExample:
    label: str
    bars: Sequence[MarketBar]

    @property
    def lookback(self) -> int:
        return len(self.bars)


@dataclass(slots=True, frozen=True)
class LearnedPattern:
    label: str
    lookback: int
    prototype: tuple[float, ...]
    sample_size: int
    threshold: float


@dataclass(slots=True, frozen=True)
class PatternMatch:
    label: str
    similarity: float
    threshold: float

    @property
    def is_match(self) -> bool:
        return self.similarity >= self.threshold


@dataclass(slots=True, frozen=True)
class PatternAlert:
    symbol: str
    label: str
    similarity: float
    timestamp: datetime
    message: str
