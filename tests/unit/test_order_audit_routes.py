from __future__ import annotations

from types import SimpleNamespace

from trading_system.api.routes.order_audit import (
    export_order_audit_records,
    list_order_audit_records,
)
from trading_system.execution.order_audit import OrderAuditRecord


class FakeOrderAuditRepository:
    def list(self, **kwargs):
        assert kwargs["scope"] == "backtest"
        assert kwargs["owner_id"] == "run-1"
        return [
            OrderAuditRecord(
                record_id="oa_1",
                scope="backtest",
                owner_id="run-1",
                event="order.filled",
                symbol="BTCUSDT",
                side="buy",
                requested_quantity="1",
                filled_quantity="1",
                price="100",
                status="filled",
                reason=None,
                timestamp="2024-01-01T00:00:00Z",
                payload={"symbol": "BTCUSDT"},
            )
        ]


def test_list_order_audit_records_maps_repository_records():
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(order_audit_repository=FakeOrderAuditRepository()))
    )

    response = list_order_audit_records(request, scope="backtest", owner_id="run-1")

    assert response.total == 1
    assert response.records[0].record_id == "oa_1"
    assert response.records[0].owner_id == "run-1"


def test_export_order_audit_records_returns_csv():
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(order_audit_repository=FakeOrderAuditRepository()))
    )

    response = export_order_audit_records(
        request,
        scope="backtest",
        owner_id="run-1",
        format="csv",
    )

    assert response.status_code == 200
    assert response.headers["x-order-audit-record-count"] == "1"
    assert "record_id,scope,owner_id" in response.body.decode()
    assert "oa_1" in response.body.decode()


def test_export_order_audit_records_returns_jsonl():
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(order_audit_repository=FakeOrderAuditRepository()))
    )

    response = export_order_audit_records(
        request,
        scope="backtest",
        owner_id="run-1",
        format="jsonl",
    )

    assert response.status_code == 200
    assert '"record_id":"oa_1"' in response.body.decode().replace(" ", "")
