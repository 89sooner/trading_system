from collections.abc import Sequence

from trading_system.core.types import MarketBar
from trading_system.patterns.matcher import PatternMatcher
from trading_system.patterns.types import LearnedPattern, PatternAlert


class PatternAlertService:
    def __init__(self, matcher: PatternMatcher | None = None) -> None:
        self._matcher = matcher or PatternMatcher()

    def evaluate(
        self,
        symbol: str,
        bars: Sequence[MarketBar],
        patterns: Sequence[LearnedPattern],
    ) -> PatternAlert | None:
        if not patterns:
            return None

        best_match = self._matcher.match(patterns, bars)[0]
        if not best_match.is_match:
            return None

        latest_bar = bars[-1]
        return PatternAlert(
            symbol=symbol,
            label=best_match.label,
            similarity=best_match.similarity,
            timestamp=latest_bar.timestamp,
            message=f"{symbol} matched {best_match.label} with score {best_match.similarity:.3f}",
        )
