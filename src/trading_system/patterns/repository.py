from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from trading_system.patterns.types import LearnedPattern


@dataclass(slots=True, frozen=True)
class PatternSet:
    pattern_set_id: str
    name: str
    symbol: str
    default_threshold: float
    examples_count: int
    patterns: list[LearnedPattern]


class PatternSetRepository:
    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def save(self, pattern_set: PatternSet) -> PatternSet:
        path = self._root_dir / f"{pattern_set.pattern_set_id}.json"
        path.write_text(
            json.dumps(_pattern_set_to_payload(pattern_set), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return pattern_set

    def list(self) -> list[PatternSet]:
        pattern_sets: list[PatternSet] = []
        for path in sorted(self._root_dir.glob("*.json")):
            pattern_sets.append(_payload_to_pattern_set(json.loads(path.read_text("utf-8"))))
        return pattern_sets

    def get(self, pattern_set_id: str) -> PatternSet:
        path = self._root_dir / f"{pattern_set_id}.json"
        if not path.exists():
            raise RuntimeError(f"Pattern set not found: {pattern_set_id}")
        return _payload_to_pattern_set(json.loads(path.read_text("utf-8")))


def _pattern_set_to_payload(pattern_set: PatternSet) -> dict[str, object]:
    return {
        "pattern_set_id": pattern_set.pattern_set_id,
        "name": pattern_set.name,
        "symbol": pattern_set.symbol,
        "default_threshold": pattern_set.default_threshold,
        "examples_count": pattern_set.examples_count,
        "patterns": [
            {
                "label": pattern.label,
                "lookback": pattern.lookback,
                "prototype": list(pattern.prototype),
                "sample_size": pattern.sample_size,
                "threshold": pattern.threshold,
            }
            for pattern in pattern_set.patterns
        ],
    }


def _payload_to_pattern_set(payload: dict[str, object]) -> PatternSet:
    raw_patterns = payload.get("patterns", [])
    if not isinstance(raw_patterns, list):
        raise RuntimeError("Pattern set patterns must be a list.")

    return PatternSet(
        pattern_set_id=str(payload["pattern_set_id"]),
        name=str(payload["name"]),
        symbol=str(payload["symbol"]),
        default_threshold=float(payload["default_threshold"]),
        examples_count=int(payload["examples_count"]),
        patterns=[
            LearnedPattern(
                label=str(pattern["label"]),
                lookback=int(pattern["lookback"]),
                prototype=tuple(float(value) for value in pattern["prototype"]),
                sample_size=int(pattern["sample_size"]),
                threshold=float(pattern["threshold"]),
            )
            for pattern in raw_patterns
        ],
    )
