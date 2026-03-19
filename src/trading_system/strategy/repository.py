from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from trading_system.strategy.base import SignalSide


@dataclass(slots=True, frozen=True)
class StrategyProfile:
    strategy_id: str
    name: str
    strategy_type: str
    pattern_set_id: str
    label_to_side: dict[str, SignalSide]
    trade_quantity: Decimal | None
    threshold_overrides: dict[str, float]


class StrategyProfileRepository:
    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def save(self, profile: StrategyProfile) -> StrategyProfile:
        path = self._root_dir / f"{profile.strategy_id}.json"
        path.write_text(json.dumps(_profile_to_payload(profile), indent=2, sort_keys=True), "utf-8")
        return profile

    def list(self) -> list[StrategyProfile]:
        profiles: list[StrategyProfile] = []
        for path in sorted(self._root_dir.glob("*.json")):
            profiles.append(_payload_to_profile(json.loads(path.read_text("utf-8"))))
        return profiles

    def get(self, strategy_id: str) -> StrategyProfile:
        path = self._root_dir / f"{strategy_id}.json"
        if not path.exists():
            raise RuntimeError(f"Strategy profile not found: {strategy_id}")
        return _payload_to_profile(json.loads(path.read_text("utf-8")))


def _profile_to_payload(profile: StrategyProfile) -> dict[str, object]:
    return {
        "strategy_id": profile.strategy_id,
        "name": profile.name,
        "strategy_type": profile.strategy_type,
        "pattern_set_id": profile.pattern_set_id,
        "label_to_side": {label: side.value for label, side in profile.label_to_side.items()},
        "trade_quantity": format(profile.trade_quantity, "f") if profile.trade_quantity else None,
        "threshold_overrides": profile.threshold_overrides,
    }


def _payload_to_profile(payload: dict[str, object]) -> StrategyProfile:
    raw_label_map = payload.get("label_to_side", {})
    if not isinstance(raw_label_map, dict):
        raise RuntimeError("Strategy profile label_to_side must be a mapping.")

    raw_thresholds = payload.get("threshold_overrides", {})
    if not isinstance(raw_thresholds, dict):
        raise RuntimeError("Strategy profile threshold_overrides must be a mapping.")

    raw_trade_quantity = payload.get("trade_quantity")
    trade_quantity = Decimal(str(raw_trade_quantity)) if raw_trade_quantity is not None else None

    return StrategyProfile(
        strategy_id=str(payload["strategy_id"]),
        name=str(payload["name"]),
        strategy_type=str(payload["strategy_type"]),
        pattern_set_id=str(payload["pattern_set_id"]),
        label_to_side={
            str(label): SignalSide(str(side)) for label, side in sorted(raw_label_map.items())
        },
        trade_quantity=trade_quantity,
        threshold_overrides={
            str(label): float(value) for label, value in sorted(raw_thresholds.items())
        },
    )
