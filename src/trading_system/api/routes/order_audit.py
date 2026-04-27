from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Request
from fastapi.responses import Response

from trading_system.api.schemas import OrderAuditListDTO, OrderAuditRecordDTO
from trading_system.execution.order_audit import OrderAuditRecord

router = APIRouter(prefix="/api/v1/order-audit", tags=["order-audit"])


@router.get("", response_model=OrderAuditListDTO)
def list_order_audit_records(
    request: Request,
    scope: str | None = None,
    owner_id: str | None = None,
    symbol: str | None = None,
    event: str | None = None,
    status: str | None = None,
    side: str | None = None,
    broker_order_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    sort: str = "desc",
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
        status=status,
        side=side,
        broker_order_id=broker_order_id,
        start=start,
        end=end,
        sort=_normalize_sort(sort),
        limit=max(1, min(limit, 500)),
    )
    return OrderAuditListDTO(records=[_to_dto(record) for record in records], total=len(records))


@router.get("/export")
def export_order_audit_records(
    request: Request,
    scope: str | None = None,
    owner_id: str | None = None,
    symbol: str | None = None,
    event: str | None = None,
    status: str | None = None,
    side: str | None = None,
    broker_order_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    sort: str = "desc",
    format: str = "csv",
    limit: int = 1000,
) -> Response:
    repo = getattr(request.app.state, "order_audit_repository", None)
    export_format = format.strip().lower()
    if export_format not in {"csv", "jsonl"}:
        return Response("format must be one of: csv, jsonl", status_code=400)
    if repo is None:
        records: list[OrderAuditRecord] = []
    else:
        records = repo.list(
            scope=scope,
            owner_id=owner_id,
            symbol=symbol,
            event=event,
            status=status,
            side=side,
            broker_order_id=broker_order_id,
            start=start,
            end=end,
            sort=_normalize_sort(sort),
            limit=max(1, min(limit, 5000)),
        )
    headers = {
        "X-Order-Audit-Record-Count": str(len(records)),
        "X-Order-Audit-Applied-Filters": json.dumps(
            {
                "scope": scope,
                "owner_id": owner_id,
                "symbol": symbol,
                "event": event,
                "status": status,
                "side": side,
                "broker_order_id": broker_order_id,
                "start": start,
                "end": end,
                "sort": _normalize_sort(sort),
                "limit": max(1, min(limit, 5000)),
            },
            default=str,
        ),
    }
    if export_format == "jsonl":
        body = "\n".join(
            json.dumps(_to_dto(record).model_dump(), default=str)
            for record in records
        )
        if body:
            body += "\n"
        return Response(body, media_type="application/x-ndjson", headers=headers)

    return Response(_to_csv(records), media_type="text/csv", headers=headers)


def _to_dto(record: OrderAuditRecord) -> OrderAuditRecordDTO:
    return OrderAuditRecordDTO(
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


def _to_csv(records: list[OrderAuditRecord]) -> str:
    output = io.StringIO()
    fieldnames = [
        "record_id",
        "scope",
        "owner_id",
        "event",
        "symbol",
        "side",
        "requested_quantity",
        "filled_quantity",
        "price",
        "status",
        "reason",
        "timestamp",
        "broker_order_id",
        "payload",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                "record_id": record.record_id,
                "scope": record.scope,
                "owner_id": record.owner_id,
                "event": record.event,
                "symbol": record.symbol,
                "side": record.side,
                "requested_quantity": record.requested_quantity,
                "filled_quantity": record.filled_quantity,
                "price": record.price,
                "status": record.status,
                "reason": record.reason,
                "timestamp": record.timestamp,
                "broker_order_id": record.broker_order_id,
                "payload": json.dumps(record.payload, default=str),
            }
        )
    return output.getvalue()


def _normalize_sort(sort: str) -> str:
    return "asc" if sort == "asc" else "desc"
