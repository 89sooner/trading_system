from decimal import Decimal
from types import SimpleNamespace

from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.routes.order_audit import list_order_audit_records
from trading_system.api.schemas import BacktestRunRequestDTO
from trading_system.app.loop import LiveTradingLoop
from trading_system.app.sample_data import build_sample_bars
from trading_system.app.services import AppServices
from trading_system.app.settings import AppMode, LiveExecutionMode
from trading_system.backtest.file_repository import FileBacktestRunRepository
from trading_system.core.ops import StructuredLogFormat, StructuredLogger
from trading_system.data.provider import InMemoryMarketDataProvider
from trading_system.execution.broker import (
    BpsCommissionPolicy,
    BpsSlippagePolicy,
    FixedRatioFillPolicy,
    PolicyBrokerSimulator,
    ResilientBroker,
)
from trading_system.execution.order_audit import FileOrderAuditRepository
from trading_system.execution.step import TradingContext
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.example import MomentumStrategy


class _FailingOrderAuditRepository:
    def append(self, record):
        del record
        raise RuntimeError("audit unavailable")

    def list(self, **kwargs):
        del kwargs
        return []


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


def test_live_session_order_audit_records_are_queryable_without_testclient(tmp_path):
    audit_repo = FileOrderAuditRepository(tmp_path / "order_audit")
    services = AppServices(
        mode=AppMode.LIVE,
        provider="mock",
        broker="paper",
        live_execution=LiveExecutionMode.PAPER,
        strategy=MomentumStrategy(trade_quantity=Decimal("0.1")),
        strategies=None,
        data_provider=InMemoryMarketDataProvider({"BTCUSDT": build_sample_bars("BTCUSDT")[:2]}),
        risk_limits=RiskLimits(
            max_position=Decimal("1"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("0.25"),
        ),
        broker_simulator=ResilientBroker(
            delegate=PolicyBrokerSimulator(
                fill_quantity_policy=FixedRatioFillPolicy(),
                slippage_policy=BpsSlippagePolicy(),
                commission_policy=BpsCommissionPolicy(),
            )
        ),
        portfolio=PortfolioBook(cash=Decimal("10000")),
        symbols=("BTCUSDT",),
        logger=StructuredLogger("test.live.audit", log_format=StructuredLogFormat.JSON),
        order_audit_repository=audit_repo,
    )
    loop = LiveTradingLoop(services=services, audit_owner_id="session-1")
    context = TradingContext(
        portfolio=services.portfolio,
        risk_limits=services.risk_limits,
        broker=services.broker_simulator,
        logger=services.logger,
        runtime_state=loop.runtime,
        marks=loop.runtime.last_marks,
        order_audit_repository=audit_repo,
        order_audit_scope="live_session",
        order_audit_owner_id="session-1",
    )

    loop._run_tick(context)
    response = list_order_audit_records(
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(order_audit_repository=audit_repo))),
        scope="live_session",
        owner_id="session-1",
    )

    assert response.total >= 1
    assert {record.owner_id for record in response.records} == {"session-1"}
    assert "order.created" in {record.event for record in response.records}


def test_live_session_audit_append_failure_does_not_fail_tick():
    services = AppServices(
        mode=AppMode.LIVE,
        provider="mock",
        broker="paper",
        live_execution=LiveExecutionMode.PAPER,
        strategy=MomentumStrategy(trade_quantity=Decimal("0.1")),
        strategies=None,
        data_provider=InMemoryMarketDataProvider({"BTCUSDT": build_sample_bars("BTCUSDT")[:2]}),
        risk_limits=RiskLimits(
            max_position=Decimal("1"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("0.25"),
        ),
        broker_simulator=ResilientBroker(
            delegate=PolicyBrokerSimulator(
                fill_quantity_policy=FixedRatioFillPolicy(),
                slippage_policy=BpsSlippagePolicy(),
                commission_policy=BpsCommissionPolicy(),
            )
        ),
        portfolio=PortfolioBook(cash=Decimal("10000")),
        symbols=("BTCUSDT",),
        logger=StructuredLogger("test.live.audit.failure", log_format=StructuredLogFormat.JSON),
        order_audit_repository=_FailingOrderAuditRepository(),
    )
    loop = LiveTradingLoop(services=services, audit_owner_id="session-failure")
    context = TradingContext(
        portfolio=services.portfolio,
        risk_limits=services.risk_limits,
        broker=services.broker_simulator,
        logger=services.logger,
        runtime_state=loop.runtime,
        marks=loop.runtime.last_marks,
        order_audit_repository=services.order_audit_repository,
        order_audit_scope="live_session",
        order_audit_owner_id="session-failure",
    )

    loop._run_tick(context)

    assert services.portfolio.positions["BTCUSDT"] == Decimal("0.1")
