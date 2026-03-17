from collections import defaultdict
from collections.abc import Iterable

from trading_system.patterns.features import extract_pattern_vector
from trading_system.patterns.types import LearnedPattern, PatternExample


class PatternTrainer:
    def __init__(self, default_threshold: float = 0.8) -> None:
        self._default_threshold = default_threshold

    def train(self, examples: Iterable[PatternExample]) -> list[LearnedPattern]:
        grouped_examples: dict[str, list[PatternExample]] = defaultdict(list)
        for example in examples:
            grouped_examples[example.label].append(example)

        learned_patterns: list[LearnedPattern] = []
        for label, label_examples in grouped_examples.items():
            lookback = _validate_lookback(label_examples)
            vectors = [extract_pattern_vector(example.bars) for example in label_examples]
            prototype = _average_vectors(vectors)
            learned_patterns.append(
                LearnedPattern(
                    label=label,
                    lookback=lookback,
                    prototype=prototype,
                    sample_size=len(label_examples),
                    threshold=self._default_threshold,
                )
            )

        return sorted(learned_patterns, key=lambda pattern: pattern.label)


def _validate_lookback(examples: list[PatternExample]) -> int:
    lookback = examples[0].lookback
    if lookback < 2:
        raise ValueError("pattern examples require at least two bars")

    for example in examples[1:]:
        if example.lookback != lookback:
            raise ValueError("all examples for a label must use the same lookback")

    return lookback


def _average_vectors(vectors: list[tuple[float, ...]]) -> tuple[float, ...]:
    feature_count = len(vectors[0])
    totals = [0.0] * feature_count
    for vector in vectors:
        if len(vector) != feature_count:
            raise ValueError("all pattern vectors must share the same size")
        for index, value in enumerate(vector):
            totals[index] += value
    return tuple(total / len(vectors) for total in totals)
