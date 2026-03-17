from collections.abc import Sequence
from math import sqrt

from trading_system.core.types import MarketBar
from trading_system.patterns.features import extract_pattern_vector
from trading_system.patterns.types import LearnedPattern, PatternMatch


class PatternMatcher:
    def match(
        self,
        patterns: Sequence[LearnedPattern],
        bars: Sequence[MarketBar],
    ) -> list[PatternMatch]:
        matches: list[PatternMatch] = []
        for pattern in patterns:
            if len(bars) != pattern.lookback:
                raise ValueError("bar window length must match the learned pattern lookback")
            similarity = _similarity(pattern.prototype, extract_pattern_vector(bars))
            matches.append(
                PatternMatch(
                    label=pattern.label,
                    similarity=similarity,
                    threshold=pattern.threshold,
                )
            )

        return sorted(matches, key=lambda match: match.similarity, reverse=True)


def _similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    cosine = _cosine_similarity(left, right)
    mean_absolute_diff = sum(abs(a - b) for a, b in zip(left, right, strict=True)) / len(left)
    diff_score = 1.0 / (1.0 + (mean_absolute_diff * 25.0))
    return max(0.0, min(1.0, (cosine + diff_score) / 2.0))


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot_product / (left_norm * right_norm)))
