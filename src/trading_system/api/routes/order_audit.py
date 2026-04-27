from __future__ import annotations

from fastapi import APIRouter, Request

from trading_system.api.schemas import OrderAuditListDTO, OrderAuditRecordDTO

router = APIRouter(prefix="/api/v1/order-audit", tags=["order-audit"])


@router.get("", response_model=OrderAuditListDTO)
def list_order_audit_records(
    request: Request,
    scope: str | None = None,
    owner_id: str | None = None,
    symbol: str | None = None,
    event: str | None = None,
    limit: int = 100,
) -> OrderAuditListDTO:
    repo = getattr(request.app.state, "order_audit_repository", None)
    if repo is None:
        return OrderAuditListDTO(records=[], total=0)
    records = repo.list(
        scope=scope,
        owner_id=owner_id,
        symbol=symbol,
        event=event,
        limit=max(1, min(limit, 500)),
    )
    return OrderAuditListDTO(
        records=[
            OrderAuditRecordDTO(
                record_id=record.record_id,
                scope=record.scope,
                owner_id=record.owner_id,
                event=record.event,
                symbol=record.symbol,
                side=record.side,
                requested_quantity=record.requested_quantity,
                filled_quantity=record.filled_quantity,
                price=record.price,
                status=record.status,
                reason=record.reason,
                timestamp=record.timestamp,
                payload=record.payload,
                broker_order_id=record.broker_order_id,
            )
            for record in records
        ],
        total=len(records),
    )
