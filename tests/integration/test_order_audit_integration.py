from types import SimpleNamespace

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.routes.order_audit import list_order_audit_records
from trading_system.api.schemas import BacktestRunRequestDTO
from trading_system.backtest.file_repository import FileBacktestRunRepository
from trading_system.execution.order_audit import FileOrderAuditRepository


def _base_payload() -> dict:
    return {
        "mode": "backtest",
        "symbols": ["BTCUSDT"],
        "provider": "mock",
        "broker": "paper",
        "live_execution": "preflight",
        "risk": {
            "max_position": "1",
            "max_notional": "100000",
            "max_order_size": "0.25",
        },
        "backtest": {
            "starting_cash": "10000",
            "fee_bps": "5",
            "trade_quantity": "0.1",
        },
    }


def test_backtest_order_audit_records_are_queryable(tmp_path):
    run_repo = FileBacktestRunRepository(tmp_path / "runs")
    audit_repo = FileOrderAuditRepository(tmp_path / "order_audit")
    original_run_repo = backtest_routes._RUN_REPOSITORY
    original_audit_repo = backtest_routes._ORDER_AUDIT_REPOSITORY
    backtest_routes._RUN_REPOSITORY = run_repo
    backtest_routes._ORDER_AUDIT_REPOSITORY = audit_repo
    try:
        accepted = backtest_routes.create_backtest_run(
            BacktestRunRequestDTO.model_validate(_base_payload()),
            request=None,
        )
        response = list_order_audit_records(
            SimpleNamespace(
                app=SimpleNamespace(state=SimpleNamespace(order_audit_repository=audit_repo))
            ),
            scope="backtest",
            owner_id=accepted.run_id,
        )
    finally:
        backtest_routes._RUN_REPOSITORY = original_run_repo
        backtest_routes._ORDER_AUDIT_REPOSITORY = original_audit_repo

    assert response.total >= 1
    assert {record.owner_id for record in response.records} == {accepted.run_id}
    assert "order.created" in {record.event for record in response.records}
