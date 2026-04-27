from decimal import Decimal
from unittest.mock import MagicMock

from trading_system.app.loop import LiveTradingLoop
from trading_system.app.state import AppRunnerState
from trading_system.execution.broker import AccountBalanceSnapshot, OpenOrder, OpenOrderSnapshot
from trading_system.execution.orders import OrderSide
from trading_system.execution.step import TradingContext
from trading_system.portfolio.book import PortfolioBook


class MockExceptionLoop(LiveTradingLoop):
    def _run_tick(self, context: TradingContext) -> None:
        # Simulate network or API error
        raise ConnectionError("API disconnected")


def test_live_loop_catches_exceptions_and_pauses(monkeypatch):
    # Setup mock services
    mock_services = MagicMock()
    mock_services.logger = MagicMock()
    mock_services.portfolio = MagicMock()
    mock_services.risk_limits = MagicMock()
    mock_services.broker_simulator = MagicMock()

    loop = MockExceptionLoop(services=mock_services, poll_interval=1, heartbeat_interval=1)
    
    import time
    def mock_sleep(_):
        assert loop.state == AppRunnerState.PAUSED
        loop.state = AppRunnerState.STOPPED
    monkeypatch.setattr(time, "sleep", mock_sleep)
    
    assert loop.state == AppRunnerState.INIT
    
    # Run loop
    loop.run()
    
    # Assert state transitioned to PAUSED instead of crashing
    # Already checked in mock_sleep, but we can verify the mock was called by checking STOPPED
    assert loop.state == AppRunnerState.STOPPED
    
    # Assert logger emitted the error
    from unittest.mock import ANY
    mock_services.logger.emit.assert_any_call(
        "system.error",
        severity=40,
        payload={
            "reason": "unhandled_exception",
            "error": "API disconnected",
            "traceback": ANY
        }
    )

def test_live_loop_keyboard_interrupt():
    class MockInterruptLoop(LiveTradingLoop):
        def _check_heartbeat(self) -> None:
            raise KeyboardInterrupt()

    mock_services = MagicMock()
    mock_services.logger = MagicMock()

    loop = MockInterruptLoop(services=mock_services, poll_interval=1, heartbeat_interval=1)
    loop.run()
    
    assert loop.state == AppRunnerState.STOPPED
    mock_services.logger.emit.assert_any_call(
        "system.shutdown",
        severity=20,
        payload={"reason": "keyboard_interrupt"}
    )


def test_live_loop_reconciliation_uses_open_orders_as_pending_source():
    services = MagicMock()
    services.logger = MagicMock()
    services.portfolio = PortfolioBook(
        cash=Decimal("100"),
        positions={"005930": Decimal("1")},
        average_costs={"005930": Decimal("70000")},
    )
    services.broker_simulator.get_open_orders.return_value = OpenOrderSnapshot(
        orders=(
            OpenOrder(
                broker_order_id="90001",
                symbol="005930",
                side=OrderSide.BUY,
                requested_quantity=Decimal("3"),
                remaining_quantity=Decimal("1"),
                status="open",
            ),
        )
    )
    services.broker_simulator.get_account_balance.return_value = AccountBalanceSnapshot(
        cash=Decimal("120"),
        positions={"005930": Decimal("2")},
        average_costs={"005930": Decimal("71000")},
        pending_symbols=(),
    )

    loop = LiveTradingLoop(services=services, poll_interval=1, heartbeat_interval=1)

    loop._maybe_reconcile()

    assert services.portfolio.cash == Decimal("100")
    assert services.portfolio.positions["005930"] == Decimal("1")
    services.logger.emit.assert_any_call(
        "portfolio.reconciliation.pending_source",
        severity=20,
        payload={"pending_source": "open_orders", "pending_symbol_count": 1},
    )


def test_live_loop_reconciliation_skips_when_open_order_query_fails():
    services = MagicMock()
    services.logger = MagicMock()
    services.portfolio = PortfolioBook(cash=Decimal("100"), positions={"005930": Decimal("1")})
    services.broker_simulator.get_open_orders.side_effect = RuntimeError("open orders failed")

    loop = LiveTradingLoop(services=services, poll_interval=1, heartbeat_interval=1)

    loop._maybe_reconcile()

    services.broker_simulator.get_account_balance.assert_not_called()
    assert services.portfolio.cash == Decimal("100")
    services.logger.emit.assert_any_call(
        "portfolio.reconciliation.skipped",
        severity=40,
        payload={
            "reason": "open_orders_unavailable",
            "error": "open orders failed",
            "pending_source": "open_orders",
        },
    )
