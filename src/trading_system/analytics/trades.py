from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class CompletedTrade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal

    @property
    def holding_seconds(self) -> float:
        return (self.exit_time - self.entry_time).total_seconds()


@dataclass(slots=True)
class _OpenLot:
    quantity: Decimal
    price: Decimal
    timestamp: datetime


def extract_trades(order_events: Sequence[Mapping[str, object]]) -> list[CompletedTrade]:
    open_lots: dict[str, deque[_OpenLot]] = {}
    completed: list[CompletedTrade] = []

    for event in order_events:
        if is_dataclass(event):
            event = asdict(event)
        if str(event.get("event")) != "order.filled":
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, Mapping):
            continue

        symbol = str(payload.get("symbol", ""))
        side = str(payload.get("side", ""))
        quantity = _to_decimal(payload.get("filled_quantity"))
        price = _to_decimal(payload.get("fill_price"))
        timestamp = _to_datetime(payload.get("timestamp"))

        if not symbol or quantity <= ZERO:
            continue

        lots = open_lots.setdefault(symbol, deque())
        if side == "buy":
            lots.append(_OpenLot(quantity=quantity, price=price, timestamp=timestamp))
            continue

        remaining = quantity
        while remaining > ZERO and lots:
            lot = lots[0]
            matched = min(remaining, lot.quantity)
            completed.append(
                CompletedTrade(
                    symbol=symbol,
                    entry_time=lot.timestamp,
                    exit_time=timestamp,
                    entry_price=lot.price,
                    exit_price=price,
                    quantity=matched,
                    pnl=(price - lot.price) * matched,
                )
            )
            remaining -= matched
            lot.quantity -= matched
            if lot.quantity == ZERO:
                lots.popleft()

    return completed


def _to_decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _to_datetime(value: object) -> datetime:
    return datetime.fromisoformat(str(value))
