from dataclasses import dataclass
from decimal import Decimal

from trading_system.core.types import MarketBar
from trading_system.execution.broker import FillEvent, FillStatus
from trading_system.execution.orders import OrderRequest
from trading_system.integrations.kis import KisApiClient, KisOrderResult


@dataclass(slots=True)
class KisBrokerAdapter:
    client: KisApiClient

    def submit_order(self, order: OrderRequest, bar: MarketBar) -> FillEvent:
        result = self.client.submit_order(order)
        return _to_fill_event(result=result, order=order, fallback_price=bar.close)


def _to_fill_event(
    *,
    result: KisOrderResult,
    order: OrderRequest,
    fallback_price: Decimal,
) -> FillEvent:
    filled_quantity = max(result.filled_quantity, Decimal("0"))
    fill_price = result.fill_price if result.fill_price > 0 else fallback_price
    status = _resolve_status(requested=order.quantity, filled=filled_quantity)
    return FillEvent(
        symbol=order.symbol,
        side=order.side,
        requested_quantity=order.quantity,
        filled_quantity=filled_quantity,
        fill_price=fill_price,
        fee=result.fee,
        status=status,
    )


def _resolve_status(*, requested: Decimal, filled: Decimal) -> FillStatus:
    if filled <= 0:
        return FillStatus.UNFILLED
    if filled >= requested:
        return FillStatus.FILLED
    return FillStatus.PARTIALLY_FILLED
