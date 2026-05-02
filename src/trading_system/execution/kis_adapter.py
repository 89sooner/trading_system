from dataclasses import dataclass
from decimal import Decimal

from trading_system.core.types import MarketBar
from trading_system.execution.broker import (
    AccountBalanceSnapshot,
    FillEvent,
    FillStatus,
    OpenOrderSnapshot,
    OrderCancelRequest,
    OrderCancelResult,
)
from trading_system.execution.orders import OrderRequest
from trading_system.integrations.kis import KisApiClient, KisApiError, KisOrderResult


@dataclass(slots=True)
class KisBrokerAdapter:
    client: KisApiClient

    def submit_order(self, order: OrderRequest, bar: MarketBar) -> FillEvent:
        result = self.client.submit_order(order)
        return _to_fill_event(result=result, order=order, fallback_price=bar.close)

    def get_account_balance(self) -> AccountBalanceSnapshot | None:
        """Build a safe snapshot from KIS balance query.

        Returns ``None`` if any part of the query fails, ensuring
        reconciliation is skipped rather than applied with partial data.
        """
        try:
            access_token = self.client.issue_access_token()
            balance = self.client.inquire_balance(access_token=access_token)
            return AccountBalanceSnapshot(
                cash=balance["cash"],
                positions=balance["positions"],
                average_costs=balance["average_costs"],
                pending_symbols=balance["pending_symbols"],
            )
        except (KisApiError, KeyError, Exception):
            return None

    def get_open_orders(self) -> OpenOrderSnapshot:
        access_token = self.client.issue_access_token()
        return self.client.inquire_open_orders(access_token=access_token)

    def cancel_order(self, request: OrderCancelRequest) -> OrderCancelResult:
        result = self.client.cancel_order(
            broker_order_id=request.broker_order_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
        )
        return OrderCancelResult(
            broker_order_id=result.order_id,
            accepted=True,
            message=result.message,
            result_code=result.result_code,
        )


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
        broker_order_id=result.order_id,
    )


def _resolve_status(*, requested: Decimal, filled: Decimal) -> FillStatus:
    if filled <= 0:
        return FillStatus.UNFILLED
    if filled >= requested:
        return FillStatus.FILLED
    return FillStatus.PARTIALLY_FILLED
